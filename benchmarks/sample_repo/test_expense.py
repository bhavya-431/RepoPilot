import pytest
from expense import calculate_expense_share, ExpenseTracker


def test_calculate_share_valid():
    assert calculate_expense_share(100.0, 4) == 25.0
    assert calculate_expense_share(50.0, 2) == 25.0


def test_calculate_share_negative():
    with pytest.raises(ValueError):
        calculate_expense_share(-10.0, 2)


def test_calculate_share_zero_participants():
    """
    This test exposes the bug! Currently raises ZeroDivisionError instead of handling safely.
    """
    with pytest.raises(ValueError):
        calculate_expense_share(100.0, 0)


def test_expense_tracker_normal():
    tracker = ExpenseTracker()
    rec = tracker.add_expense("Dinner", 60.0, ["Alice", "Bob", "Charlie"])
    assert rec["share_per_person"] == 20.0
