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
                """Sanitise log messages while preserving correct formatting semantics.

                ``record.getMessage()`` lazily formats ``record.msg`` with ``record.args``
                using the ``%`` operator.  We first format the message, apply the
                ``sanitize_output`` function to hide any secrets, then replace the
                raw ``msg`` with the sanitized result *and clear the ``args``*.

                The original implementation only overwrote ``record.msg`` which
                left ``record.args`` untouched.  Subsequent formatting attempts
                (for example when the ``Handler`` formats the record) tried to
                apply the original arguments to the already‑formatted message,
                causing a ``TypeError: not all arguments converted during string
                formatting``.  By clearing ``record.args`` we ensure the sanitized
                message is emitted unchanged.
                """
                # Format the original message with its arguments first.
                formatted = record.getMessage()
                # Apply secret redaction.
                sanitized = sanitize_output(formatted)
                # Replace the message and clear any arguments to avoid re‑formatting.
                record.msg = sanitized
                record.args = None
                return True

        handler.addFilter(SecretMaskFilter())

    return logger


# Default logger for the application
logger = setup_logger("cloudmesh")
