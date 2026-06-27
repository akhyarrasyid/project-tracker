"""Unit tests for all 5 enums and their values."""
import pytest
from app.schemas.task import (
    TaskStatus,
    TaskPriority,
    RiskLevel,
    CustomerImpact,
    Quarter,
)


class TestTaskStatus:
    def test_has_five_values(self):
        assert len(TaskStatus) == 5

    def test_todo_value(self):
        assert TaskStatus.TODO == "Todo"

    def test_in_progress_value(self):
        assert TaskStatus.IN_PROGRESS == "In Progress"

    def test_review_value(self):
        assert TaskStatus.REVIEW == "Review"

    def test_blocked_value(self):
        assert TaskStatus.BLOCKED == "Blocked"

    def test_done_value(self):
        assert TaskStatus.DONE == "Done"

    def test_all_values_are_strings(self):
        for s in TaskStatus:
            assert isinstance(s.value, str)

    def test_case_sensitive_todo(self):
        with pytest.raises(ValueError):
            TaskStatus("todo")

    def test_case_sensitive_done(self):
        with pytest.raises(ValueError):
            TaskStatus("done")


class TestTaskPriority:
    def test_has_four_values(self):
        assert len(TaskPriority) == 4

    def test_low(self):
        assert TaskPriority.LOW == "Low"

    def test_medium(self):
        assert TaskPriority.MEDIUM == "Medium"

    def test_high(self):
        assert TaskPriority.HIGH == "High"

    def test_critical(self):
        assert TaskPriority.CRITICAL == "Critical"

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            TaskPriority("Urgent")


class TestRiskLevel:
    def test_has_three_values(self):
        assert len(RiskLevel) == 3

    def test_low(self):
        assert RiskLevel.LOW == "Low"

    def test_medium(self):
        assert RiskLevel.MEDIUM == "Medium"

    def test_high(self):
        assert RiskLevel.HIGH == "High"


class TestCustomerImpact:
    def test_has_five_values(self):
        assert len(CustomerImpact) == 5

    def test_none(self):
        assert CustomerImpact.NONE == "None"

    def test_internal(self):
        assert CustomerImpact.INTERNAL == "Internal"

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            CustomerImpact("Extreme")


class TestQuarter:
    def test_has_four_values(self):
        assert len(Quarter) == 4

    def test_all_quarters_present(self):
        values = {q.value for q in Quarter}
        assert values == {"Q1", "Q2", "Q3", "Q4"}
