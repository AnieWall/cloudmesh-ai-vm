import logging
import sys

# Import the sanitiser that strips secrets from any log message. This function
# lives in the command utilities module and already knows the patterns that
# need to be redacted (API keys, passwords, tokens, etc.).
from cloudmesh.ai.command._shared.providers_utils import sanitize_output


def setup_logger(name: str, level=logging.INFO):
    """
    Configures and returns a logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # -----------------------------------------------------------------
        # Attach a filter that sanitises the log record before it is emitted.
        # The filter mutates ``record.msg`` in‑place, applying the same
        # redaction logic used for CLI output. This guarantees that any
        # secret that accidentally ends up in a log message (e.g. from an
        # exception's ``stderr``) is masked.
        # -----------------------------------------------------------------
        class SecretMaskFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                # ``record.getMessage()`` formats the message with any args.
                # We replace the raw message after formatting.
                record.msg = sanitize_output(record.getMessage())
                return True

        handler.addFilter(SecretMaskFilter())

    return logger


# Default logger for the application
logger = setup_logger("cloudmesh")
