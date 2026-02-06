"""
Discrete-time simulation of a simplified automotive supply chain.

Actors:
- OEM (demand source)
- Tier 1 supplier (focal firm)
- Tier 2 supplier (upstream production)

This baseline version is decentralized and order-only:
- No forecast sharing
- No inventory visibility
- No capacity visibility
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import random
from typing import Deque, List, Tuple

@dataclass
class SupplyNode:
    """Represents a supply chain node with inventory and backlog."""

    name: str
    inventory: int
    backlog: int = 0
    capacity: int | None = None

    def receive(self, quantity: int) -> None:
        """Receive inventory into stock."""
        self.inventory += quantity

    def ship(self, demand: int) -> int:
        """Ship as much as possible, backlogging unmet demand."""
        shipped = min(self.inventory, demand)
        self.inventory -= shipped
        self.backlog += demand - shipped
        return shipped

    def clear_backlog(self) -> int:
        """Use available inventory to clear backlog."""
        cleared = min(self.inventory, self.backlog)
        self.inventory -= cleared
        self.backlog -= cleared
        return cleared

@dataclass
class Order:
    quantity: int
    placed_at: int

@dataclass
class Tier2Queue:
    """FIFO queue of Tier 1 orders processed by Tier 2 capacity."""

    orders: Deque[Order] = field(default_factory=deque)

    def enqueue(self, order: Order) -> None:
        self.orders.append(order)

    def total_on_order(self) -> int:
        return sum(order.quantity for order in self.orders)

    def process(self, capacity: int, current_time: int) -> Tuple[int, List[int]]:
        """
        Process orders up to capacity.

        Returns:
            total_shipped: total units shipped to Tier 1 this period
            lead_times: list of lead times (per order completed)
        """
        remaining_capacity = capacity
        total_shipped = 0
        lead_times: List[int] = []

        while self.orders and remaining_capacity > 0:
            order = self.orders[0]
            if order.quantity <= remaining_capacity:
                self.orders.popleft()
                remaining_capacity -= order.quantity
                total_shipped += order.quantity
                lead_times.append(current_time - order.placed_at)
            else:
                # Partial completion: reduce order quantity and exhaust capacity.
                order.quantity -= remaining_capacity
                total_shipped += remaining_capacity
                remaining_capacity = 0

        return total_shipped, lead_times


def oem_demand(rng: random.Random, sigma: float) -> int:
    """Generate stochastic weekly OEM demand."""
    # Simple integer demand with mean around 50.
    demand = int(round(rng.gauss(mu=50, sigma=sigma)))
    return max(demand, 0)


def simulate(
    weeks: int = 52,
    base_stock: int = 200,
    tier2_capacity: int = 60,
    demand_sigma: float = 10.0,
    seed: int = 7,
) -> Tuple[List[int], dict]:
    """Run the discrete-time simulation and return lead times plus KPIs."""
    rng = random.Random(seed)

    tier1 = SupplyNode(name="Tier 1", inventory=base_stock)
    tier2 = SupplyNode(name="Tier 2", inventory=0, capacity=tier2_capacity)
    queue = Tier2Queue()

    lead_times: List[int] = []
    kpis = {
        "tier1_inventory": [],
        "tier1_backlog": [],
        "queue_wip": [],
        "oem_demand": [],
        "tier2_shipped": [],
    }
    total_demand = 0
    total_shipped_to_oem = 0

    for week in range(weeks):
        # 1) OEM demand arrives at Tier 1.
        demand = oem_demand(rng, demand_sigma)
        shipped_to_oem = tier1.ship(demand)
        total_demand += demand
        total_shipped_to_oem += shipped_to_oem

        # 2) Tier 1 attempts to clear backlog if possible (same week).
        tier1.clear_backlog()

        # 3) Tier 2 processes the queue up to its capacity.
        #    This happens before new orders are placed, enforcing min 1-week lead time.
        shipped, completed_lead_times = queue.process(
            capacity=tier2.capacity or 0, current_time=week
        )
        tier1.receive(shipped)
        lead_times.extend(completed_lead_times)

        # 4) Tier 1 clears backlog after receiving shipments.
        tier1.clear_backlog()

        # 5) Tier 1 calculates inventory position and places order to Tier 2.
        inventory_position = (
            tier1.inventory - tier1.backlog + queue.total_on_order()
        )
        order_qty = max(base_stock - inventory_position, 0)
        if order_qty > 0:
            queue.enqueue(Order(quantity=order_qty, placed_at=week))

        # 6) Record KPIs for this week.
        kpis["tier1_inventory"].append(tier1.inventory)
        kpis["tier1_backlog"].append(tier1.backlog)
        kpis["queue_wip"].append(queue.total_on_order())
        kpis["oem_demand"].append(demand)
        kpis["tier2_shipped"].append(shipped)

    kpis["total_demand"] = total_demand
    kpis["total_shipped_to_oem"] = total_shipped_to_oem

    return lead_times, kpis


def percentile(values: List[int], pct: float) -> float:
    """Compute a simple percentile using nearest-rank (no interpolation)."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = math.ceil((pct / 100) * len(sorted_values))
    index = max(rank - 1, 0)
    return float(sorted_values[index])


def summarize(lead_times: List[int], kpis: dict) -> None:
    """Print summary statistics for lead times and key KPIs."""
    if lead_times:
        mean = sum(lead_times) / len(lead_times)
        variance = sum((lt - mean) ** 2 for lt in lead_times) / len(lead_times)
        std_dev = math.sqrt(variance)
        p90 = percentile(lead_times, 90)
        p95 = percentile(lead_times, 95)
        mean_display = f"{mean:.2f}"
        std_display = f"{std_dev:.2f}"
        p90_display = f"{p90:.0f}"
        p95_display = f"{p95:.0f}"
    else:
        mean_display = "n/a"
        std_display = "n/a"
        p90_display = "n/a"
        p95_display = "n/a"
    avg_backlog = sum(kpis["tier1_backlog"]) / len(kpis["tier1_backlog"])
    avg_queue_wip = sum(kpis["queue_wip"]) / len(kpis["queue_wip"])
    total_demand = kpis["total_demand"]
    total_shipped_to_oem = kpis["total_shipped_to_oem"]
    fill_rate = (
        total_shipped_to_oem / total_demand if total_demand > 0 else 0.0
    )

    print(f"Orders completed: {len(lead_times)}")
    print(f"Mean lead time (weeks): {mean_display}")
    print(f"Std dev lead time (weeks): {std_display}")
    print(f"P90 lead time (weeks): {p90_display}")
    print(f"P95 lead time (weeks): {p95_display}")
    print(f"Average Tier 1 backlog: {avg_backlog:.2f}")
    print(f"Average Tier 2 queue WIP: {avg_queue_wip:.2f}")
    print(f"Total demand: {total_demand}")
    print(f"Total shipped to OEM: {total_shipped_to_oem}")
    print(f"Fill rate: {fill_rate:.2%}")


def main() -> None:
    lead_times, kpis = simulate()
    summarize(lead_times, kpis)

    capacities = [60, 55, 50]
    print("\nCapacity sweep (weekly):")
    print("capacity | mean LT | std LT | p90 LT | fill rate")
    for capacity in capacities:
        lead_times, kpis = simulate(tier2_capacity=capacity)
        mean = sum(lead_times) / len(lead_times) if lead_times else 0.0
        variance = (
            sum((lt - mean) ** 2 for lt in lead_times) / len(lead_times)
            if lead_times
            else 0.0
        )
        std_dev = math.sqrt(variance)
        p90 = percentile(lead_times, 90)
        fill_rate = (
            kpis["total_shipped_to_oem"] / kpis["total_demand"]
            if kpis["total_demand"] > 0
            else 0.0
        )
        print(
            f"{capacity:8d} | {mean:7.2f} | {std_dev:6.2f} |"
            f" {p90:6.0f} | {fill_rate:9.2%}"
        )


if __name__ == "__main__":
    main()