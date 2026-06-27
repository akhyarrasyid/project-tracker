from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Raised when an entity is not found by ID."""

    def __init__(self, entity: str, entity_id: int) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} with ID {entity_id} not found",
        )


class ValidationException(HTTPException):
    """Raised when input validation fails at the service layer."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
