import httpx
import openai

from core.config import FAILOVER_STATUS_CODES


class TruncatedResponseError(Exception):
    """Raised when the response from OpenAI was truncated due to the
    `max_completion_tokens` limit (`finish_reason == 'length'`), rather than
    due to JSON structure validation errors."""


class ProviderResponseError(openai.OpenAIError):
    """The provider responded, but the response is unusable (empty `choices`/`content`).

    We inherit from `OpenAIError` so that the Celery task treats this as a
    provider failure—triggering a retry—rather than as a bug in our own code.
    """

def is_failover_error(exc: BaseException) -> bool:

    if isinstance(exc, (openai.APIConnectionError, ProviderResponseError)):
        return True  # APITimeoutError является подклассом APIConnectionError

    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in FAILOVER_STATUS_CODES or exc.status_code >= 500

    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code in FAILOVER_STATUS_CODES or code >= 500

    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True

    return False

