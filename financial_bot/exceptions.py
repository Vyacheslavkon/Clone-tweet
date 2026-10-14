class AppError(Exception):

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UserNotFoundError(AppError):

    pass


class DataValidationError(AppError):
    """Called in the event of logical data errors e(e.g., budget < 0)."""
