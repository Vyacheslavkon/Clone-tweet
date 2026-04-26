class AppError(Exception):

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UserNotFoundError(AppError):

    pass


class DataValidationError(AppError):
    """Вызывается при логических ошибках данных (например, бюджет < 0)"""
