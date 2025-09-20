from agents.models import Allocation
from langchain_core.tools import tool


@tool
def verifier_weight_sum(allocations: list[Allocation]) -> str:
    """
    Verify that the sum of weight_pct in allocations is approximately 100 (±1e-6).
    Args:
        allocations (list[Allocation]): List of Allocation objects.
    """
    total_weight = sum(a.weight_pct for a in allocations)
    if abs(total_weight - 100) < 1e-6:
        return "Weight percentages are valid."
    return "Weight percentages are invalid. The sum is: {:.6f}; not approximately 100.".format(
        total_weight
    )
