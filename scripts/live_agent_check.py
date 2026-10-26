"""Opt-in real provider/data test. Reads existing .env; never prints credentials."""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from agent import service
from agent.data_access import SportsDataAccess
from backend.app.config.container import build_container
from backend.app.config.settings import get_settings

ROOT = Path(__file__).resolve().parents[1]

async def main():
    logging.basicConfig(level=logging.ERROR)
    settings = get_settings()
    if not settings.api_key:
        print('BLOCKED: configured test API key is missing')
        return
    container = await build_container(settings)
    access = SportsDataAccess(container.venues, container.bookings, container.programmes)
    original_run = service.Runner.run
    calls = []
    async def observed_run(*args, **kwargs):
        result = await original_run(*args, **kwargs)
        for item in result.new_items:
            if item.type == 'tool_call_item':
                raw = item.raw_item
                calls.append({'kind':'call','name':getattr(raw,'name',''), 'arguments':getattr(raw,'arguments','')})
            elif item.type == 'tool_call_output_item':
                calls.append({'kind':'output','output':item.output})
        usage = result.context_wrapper.usage
        calls.append({'kind':'usage','requests':usage.requests,'total_tokens':usage.total_tokens})
        return result
    service.Runner = SimpleNamespace(run=observed_run)
    report = {'tested_at_hk':datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),
              'model':settings.model,'transport':settings.agent_tool_transport, 'turns':[]}
    async def turn(scenario, message, history, expected=None):
        calls.clear()
        started = time.monotonic()
        record = {'scenario':scenario,'message':message}
        try:
            async with asyncio.timeout(150):
                answer = await service.run_sports_assistant(message, api_key=settings.api_key,
                    base_url=settings.base_url,model=settings.model,access=access,
                    tool_transport=settings.agent_tool_transport,history=history[-8:])
            record.update(answer=answer,tools=list(calls),success=True)
            names = [x.get('name') for x in calls if x['kind']=='call']
            record['expected_tool_called'] = expected in names if expected else None
            history.extend([{'role':'user','content':message},{'role':'assistant','content':answer[:8000]}])
            print(f"{scenario}: OK {round(time.monotonic()-started,1)}s tools={names}",flush=True)
        except Exception as exc:
            # Avoid provider error bodies/headers, which may contain credentials.
            record.update(success=False,error_type=type(exc).__name__,status_code=getattr(exc,'status_code',None),tools=list(calls))
            print(f"{scenario}: FAILED {type(exc).__name__} status={getattr(exc,'status_code',None)}",flush=True)
        record['elapsed_seconds']=round(time.monotonic()-started,2)
        report['turns'].append(record)
        target=ROOT/'docs/reports/live-agent-check.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        serialized=json.dumps(report,ensure_ascii=False,indent=2,default=str).replace(settings.api_key,'[REDACTED]')
        target.write_text(serialized)
        return record
    try:
        courses=[]
        first=await turn('course-1','我想参加一个体育课程，先帮我了解需要提供哪些条件，不要编造课程。',courses)
        if not first['success']:
            return
        await turn('course-2','羽毛球，沙田，周六或周日上午9点至12点，整期费用最多100港币，有公开剩余名额的优先。请实际查询。',courses,'recommend_sports_programmes')
        await turn('course-3','保留这些条件，把地区放宽到全香港，预算提高到200港币。说明保留和修改了什么，并重新查询。',courses,'recommend_sports_programmes')
        booking=[]
        result=await turn('booking-1','查沙田未来时间最早有公开空位的羽毛球场次，按开始时间排序，不是距离最近。给我最多三个候选以及抓取时间。',booking,'find_next_sports_sessions')
        candidate=None
        for item in result.get('tools',[]):
            if item['kind']!='output':
                continue
            value=item['output']
            if isinstance(value,str):
                try: value=json.loads(value)
                except ValueError: continue
            if isinstance(value,dict) and value.get('candidates'):
                candidate=value['candidates'][0]
                break
        if candidate:
            v,s=candidate['venue'],candidate['slot']
            message=f"就选你刚才推荐的{v['name_zh']}，{s['date']} {s['start']}–{s['end']}的羽毛球场次。请重新核对该指定时段，并给我官方预订入口。"
        else:
            # Use an explicit date from the live catalogue clock; no invented availability.
            from datetime import timedelta
            day=(datetime.now(ZoneInfo('Asia/Hong_Kong')).date()+timedelta(days=1)).isoformat()
            message=f'请核对沙田体育馆{day} 10:00–11:00的羽毛球场次，并给我官方入口；没有数据就说未知。'
        await turn('booking-2',message,booking,'prepare_sports_booking')
        await turn('booking-3','那你现在能替我自动登录康体通、抢这个场次和付款吗？请按你真实拥有的能力回答，不要声称已预订。',booking)
    finally:
        await container.aclose()
        service.Runner = SimpleNamespace(run=original_run)
        print('Report: docs/reports/live-agent-check.json',flush=True)

if __name__=='__main__':
    asyncio.run(main())
