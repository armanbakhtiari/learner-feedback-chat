import time
from typing import Any, Callable

MAX_RETRY = 5
BASE_DELAY = 1.0  # seconds; delays between attempts: 1, 2, 4, 8


def invoke_with_retry(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """Call an LLM invocable (e.g. llm.invoke, structured_llm.invoke) with
    up to MAX_RETRY attempts and exponential backoff between retries.
    Re-raises the last exception if all attempts fail.
    """
    last_exc: BaseException | None = None
    for attempt in range(MAX_RETRY):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRY - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(
                    f"⚠️  LLM call failed (attempt {attempt + 1}/{MAX_RETRY}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc
