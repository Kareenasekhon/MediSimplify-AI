import sys
import logging
from loguru import logger
from app.core.config import settings

class InterceptHandler(logging.Handler):
    """
    Default handler from loguru documentation to intercept standard library logging
    and route it through loguru.
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging() -> None:
    # Set default level for root logger
    logging.root.setLevel(settings.log_level)
    
    # Intercept all python logging logs
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Route uvicorn logs through standard logs (so they get intercepted)
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    # Configure loguru format and output stream
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "level": settings.log_level,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            }
        ]
    )
    
    logger.info("Logging successfully initialized via Loguru.")
