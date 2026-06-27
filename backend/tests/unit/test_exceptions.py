from app.core.exceptions import NotFoundException, ValidationException


def test_not_found_exception():
    exc = NotFoundException("Task", 123)
    assert exc.status_code == 404
    assert exc.detail == "Task with ID 123 not found"


def test_validation_exception():
    exc = ValidationException("Invalid status")
    assert exc.status_code == 422
    assert exc.detail == "Invalid status"
