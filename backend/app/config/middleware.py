"""HTTP middleware: CORS, gzip, request id + access log, chat rate limit."""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.app.config.settings import Settings

logger = logging.getLogger("hksf.access")
RATE_LIMITED_PATHS = ("/assistant/chat",)


def register_middleware(app: FastAPI, settings: Settings, api_prefix: str) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        container = getattr(request.app.state, "container", None)
        path = request.url.path
        if container and request.method == "POST" and path.startswith(api_prefix) \
                and path[len(api_prefix):] in RATE_LIMITED_PATHS:
            client = request.client.host if request.client else "unknown"
            count = await container.cache.hit(f"rate:{client}:{path}", settings.chat_rate_window_seconds)
            if count > settings.chat_rate_limit:
                return JSONResponse({"detail": "请求过于频繁，请稍后再试。"}, status_code=429,
                                    headers={"Retry-After": str(settings.chat_rate_window_seconds),
                                             "X-Request-ID": request_id})
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("%s %s -> %s [%s]", request.method, path, response.status_code, request_id)
        return response

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
                       expose_headers=["X-Request-ID"])
