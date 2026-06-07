import time
import logging

logger = logging.getLogger(__name__)

async def log_and_time_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # milliseconds
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        process_time
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response
