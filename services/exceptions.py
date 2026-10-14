class TruncatedResponseError(Exception):
    """Raised when the response from OpenAI was truncated due to the
    `max_completion_tokens` limit (`finish_reason == 'length'`), rather than
    due to JSON structure validation errors."""
