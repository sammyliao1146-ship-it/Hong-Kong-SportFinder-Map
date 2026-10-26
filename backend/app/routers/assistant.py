import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from agent.data_access import SportsDataAccess
from agent.service import run_sports_assistant
from agent.tools.sports_data import make_sports_queries
from backend.app.config.container import Container
from backend.app.config.dependencies import get_container
from backend.app.models.assistant import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["assistant"])


def _access(container: Container) -> SportsDataAccess:
    return SportsDataAccess(container.venues, container.bookings, container.programmes)


@router.get("/assistant/capabilities")
async def capabilities(container: Container = Depends(get_container)) -> dict:
    from agents import function_tool

    tools = [function_tool(query) for query in make_sports_queries(_access(container))]
    return {
        "read_only": True,
        "transports": ["function", "mcp_stdio"],
        "tools": [{"name": t.name, "description": t.description, "input_schema": t.params_json_schema} for t in tools],
        "unsupported": ["booking", "payment", "login", "route and travel-time estimates", "arbitrary web access"],
    }


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, container: Container = Depends(get_container)) -> ChatResponse:
    settings = container.settings
    if not settings.api_key or not settings.model:
        raise HTTPException(status_code=503, detail="选场小帮手尚未配置模型密钥。")
    try:
        async with asyncio.timeout(120):
            answer = await run_sports_assistant(
                payload.message, api_key=settings.api_key, base_url=settings.base_url,
                model=settings.model, access=_access(container),
                tool_transport=settings.agent_tool_transport,
                history=[item.model_dump() for item in payload.history])
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="选场小帮手响应超时，请稍后重试。") from exc
    except Exception as exc:
        logger.exception("Assistant request failed")
        raise HTTPException(status_code=502, detail="选场小帮手暂时无法回答，请稍后重试。") from exc
    return ChatResponse(answer=answer, model=settings.model)
