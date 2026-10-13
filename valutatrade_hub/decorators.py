"""@log_action (логирование операций)"""

import inspect
import logging
from datetime import UTC, datetime
from functools import wraps

logger = logging.getLogger("valutatrade_hub")


def log_action(action_name=None, *, verbose=False):
    """Логирует выполнение функции и результат операции"""

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                bound = signature.bind_partial(*args, **kwargs)
                arguments = bound.arguments
            except TypeError:
                arguments = kwargs

            user = arguments.get("user")
            username = arguments.get("username", arguments.get("user_id", "unknown"))

            if user is not None:
                username = getattr(user, "username", getattr(user, "user_id", username))

            currency_code = arguments.get(
                "currency_code", arguments.get("quote_currency", "unknown")
            )
            amount = arguments.get("amount", "unknown")
            rate = arguments.get("rate", "unknown")
            base = arguments.get("base_currency", arguments.get("base", "unknown"))

            action = (action_name or func.__name__).upper()
            timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")

            extra = ""
            if verbose:
                extra = f" function={func.__name__}"

            try:
                result = func(*args, **kwargs)

                if isinstance(result, dict):
                    rate = result.get("rate", rate)
                    base = result.get("base_currency", base)

                    if base == "unknown" and (
                        "cost_usd" in result or "received_usd" in result
                    ):
                        base = "USD"
                if verbose and isinstance(result, dict):
                    balance_before = result.get("balance_before")
                    balance_after = result.get("balance_after")

                    if balance_before is not None and balance_after is not None:
                        extra += (
                            f" balance_before={balance_before:.4f}"
                            f" balance_after={balance_after:.4f}"
                        )

                logger.info(
                    "timestamp=%s action=%s username=%s "
                    "currency_code=%s amount=%s rate=%s base=%s "
                    "result=OK%s",
                    timestamp,
                    action,
                    username,
                    currency_code,
                    amount,
                    rate,
                    base,
                    extra,
                )
                return result

            except Exception as exc:
                logger.info(
                    "timestamp=%s action=%s username=%s "
                    "currency_code=%s amount=%s rate=%s base=%s "
                    "result=ERROR error_type=%s error_message=%r%s",
                    timestamp,
                    action,
                    username,
                    currency_code,
                    amount,
                    rate,
                    base,
                    type(exc).__name__,
                    str(exc),
                    extra,
                )
                logger.debug("Exception traceback for action=%s", action, exc_info=True)
                raise

        return wrapper

    return decorator
