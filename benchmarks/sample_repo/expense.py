"""
Sample buggy Python repository for verification, benchmarks, and integration tests.
Bug: Expense API crashes (ZeroDivisionError) or returns 500 when amount or count is zero.
"""

def calculate_expense_share(total_amount: float, participant_count: int) -> float:
    """
    Calculate the share of expense per participant.
    Known bug: Does not validate participant_count == 0 before division.
    """
    if total_amount < 0:
        raise ValueError("Total amount cannot be negative")
    # Missing zero check!
    return total_amount / participant_count


class ExpenseTracker:
    def __init__(self):
        self.expenses = []

    def add_expense(self, description: str, amount: float, participants: list[str]) -> dict:
        if not description:
            raise ValueError("Description is required")
        share = calculate_expense_share(amount, len(participants))
        record = {
            "description": description,
            "amount": amount,
            "participants": participants,
            "share_per_person": share,
        }
        self.expenses.append(record)
        return record
