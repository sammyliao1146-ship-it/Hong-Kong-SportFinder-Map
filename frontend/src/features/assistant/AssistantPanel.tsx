import { useEffect, useRef, useState, type FormEvent } from 'react';
import { chat, type ChatMessage } from '../../api/client';
import Icon from '../../components/Icon';
import AssistantAnswer from './AssistantAnswer';
import { useLanguage } from '../../language';

const suggestions = [
  { labelZh: '挑选课程', labelEn: 'Find a course', question: '帮我挑选沙田周末上午、费用100元以内且有公开剩余名额的羽毛球课程。', questionEn: 'Find badminton courses in Sha Tin on weekend mornings, costing up to HK$100 per course, with published places remaining.' },
  { labelZh: '最近场次', labelEn: 'Next available session', question: '找沙田未来最早有公开空位的羽毛球场次，按开始时间排序。', questionEn: 'Find the earliest future badminton sessions with published availability in Sha Tin, sorted by start time.' },
  { labelZh: '指定时间预订', labelEn: 'Choose a specific session', question: '我想预订一个指定时间的场次，请先问我运动、场馆、日期和起止时间，再核对余量并给我康体通入口。', questionEn: 'Help me prepare a booking for a specific session. Ask for the sport, venue, date, start and end time, then check public availability and provide the SmartPLAY search link.' },
];

export default function AssistantPanel({ open, onOpen, onClose }: { open: boolean; onOpen: () => void; onClose: () => void }) {
  const { language, tx } = useLanguage();
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bubbleRef = useRef<HTMLButtonElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  function close() {
    onClose();
    requestAnimationFrame(() => bubbleRef.current?.focus());
  }

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus({ preventScroll: true });
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') close(); };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [open]);

  useEffect(() => {
    if (open) resultRef.current?.scrollIntoView({ block: 'nearest' });
  }, [answer, pending, error, open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim() || pending) return;
    const text = message.trim();
    setQuestion(text); setMessage(''); setPending(true); setError(''); setAnswer('');
    try {
      const reply = (await chat(`${language === 'en' ? 'Please respond in English. ' : '請以繁體中文回答。'}${text}`, history)).answer;
      setAnswer(reply);
      setHistory(previous => [...previous, { role: 'user' as const, content: text }, { role: 'assistant' as const, content: reply.slice(0, 8000) }].slice(-8));
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : tx('暂时无法连接助手，请重试。')); }
    finally { setPending(false); }
  }

  return <div className="assistant-widget">
    <section id="assistant-window" className="assistant-window" role="dialog" aria-label={tx('选场小帮手')} aria-modal="false" hidden={!open}>
      <div className="assistant-header"><span className="assistant-avatar"><Icon name="chat" size={22} /></span><div><h2>{tx('选场小帮手')}</h2><p>{tx('一起安排下一场运动')}</p></div><button className="icon-button" onClick={close} aria-label={tx('关闭聊天窗口')}><Icon name="close" size={19} /></button></div>
      <div className="assistant-body">
        <div className="assistant-welcome"><span className="eyebrow">{tx('LET’S GET MOVING')}</span><h3>{tx('今天想怎样动？')}</h3><p>{tx('告诉我运动、地区和时间，帮你理清选场条件。')}</p></div>
        {!question && <div className="suggestion-list">{suggestions.map(item => <button key={item.labelZh} onClick={() => { setMessage(language === 'en' ? item.questionEn : item.question); inputRef.current?.focus(); }}>{language === 'en' ? item.labelEn : item.labelZh}<span>↗</span></button>)}</div>}
        {question && <div className="user-message">{question}</div>}
        {pending && <div className="assistant-message thinking" role="status"><span /><span /><span /><span className="sr-only">{tx('助手正在思考')}</span></div>}
        {answer && <div className="assistant-message" role="status"><AssistantAnswer text={answer} /></div>}
        {error && <p className="inline-error" role="alert">{error}</p>}
        <div ref={resultRef} />
      </div>
      <div className="assistant-composer"><form ref={formRef} onSubmit={submit}><label className="sr-only" htmlFor="question">{tx('你的运动计划')}</label><textarea ref={inputRef} id="question" value={message} onChange={event => setMessage(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); formRef.current?.requestSubmit(); } }} placeholder={tx('输入你的运动计划…')} maxLength={8000} rows={2} /><button type="submit" className="send-button" disabled={pending || !message.trim()} aria-label={tx('发送消息')}><Icon name="send" size={18} /></button></form><p>{language === 'en' ? 'Continue with more details · Check availability on SmartPLAY' : '可继续补充条件 · 实际余量以康体通为准'} <button type="button" disabled={pending} className="assistant-reset" onClick={() => { setHistory([]); setQuestion(''); setAnswer(''); setError(''); setMessage(''); }}>{language === 'en' ? 'New chat' : '新对话'}</button></p></div>
    </section>
    <button ref={bubbleRef} className={`assistant-bubble ${open ? 'is-open' : ''}`} aria-label={open ? tx('收起选场小帮手') : tx('打开 选场小帮手')} aria-controls="assistant-window" aria-expanded={open} onClick={() => { if (open) close(); else onOpen(); }}>{open ? <Icon name="close" size={23} /> : <><Icon name="chat" size={23} /><span>{tx('问问选场')}</span></>}</button>
  </div>;
}
