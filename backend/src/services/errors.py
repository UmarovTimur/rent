class BaseError(Exception):
    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class UserNotFoundError(BaseError):
    def __init__(self, message: str = "User not found error"):
        super().__init__(message)


class CategoryNotFoundError(BaseError):
    def __init__(self, message: str = "Category not found error"):
        super().__init__(message)


class ProductNotFoundError(BaseError):
    def __init__(self, message: str = "Product not found error"):
        super().__init__(message)


class OrderNotFoundError(BaseError):
    def __init__(self, message: str = "Order not found error"):
        super().__init__(message)


class BasketNotFoundError(BaseError):
    def __init__(self, message: str = "Basket not found error"):
        super().__init__(message)


class BasketItemNotFoundError(BaseError):
    def __init__(self, message: str = "Basket item not found error"):
        super().__init__(message)


class KeyAlreadyExistsError(BaseError):
    def __init__(self, name: str, message: str = "Name '{}' already exists"):
        formatted_message = message.format(name)
        super().__init__(formatted_message)
        self.name = name


class RentalConfigNotFoundError(BaseError):
    def __init__(self, message: str = "Rental config not found for product"):
        super().__init__(message)


class RentalUnavailableError(BaseError):
    def __init__(self, message: str = "Requested rental period is unavailable"):
        super().__init__(message)


class InvalidRentalPeriodError(BaseError):
    def __init__(self, message: str = "Invalid rental period"):
        super().__init__(message)
