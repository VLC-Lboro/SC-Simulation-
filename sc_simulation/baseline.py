from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import List


@dataclass(frozen=True)
class BaselineParams:
    days: int = 120
    seed: int = 7
    avg_daily_demand: int = 100
    oem_order_cycle_days: int = 2
    t1_initial_inventory: int = 500
    oem_initial_inventory: int = 500
    t1_rop_days: float = 1.8
    t1_order_up_to_days: float = 5.4
    t2_daily_mean_capacity: int = 105
    t2_daily_capacity_sd: int = 11
    t2_downtime_probability: float = 0.05
    t2_to_t1_lead_time_base: float = 2.0
    t2_to_t1_lead_time_exp_mean: float = 0.5
    t1_to_oem_lead_time_base: float = 1.0
    t1_to_oem_lead_time_uniform_max: float = 0.5
    otif_target_days: float = 2.0


@dataclass
class BaselineResults:
    mean_lead_time: float
    lead_time_std: float
    max_lead_time: float
    avg_wip: float
    avg_backlog: float
    otif: float
    lead_times: List[float]


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= rng.random()
    return k - 1


def simulate_baseline(params: BaselineParams = BaselineParams()) -> BaselineResults:
    rng = random.Random(params.seed)

    t1_inventory = params.t1_initial_inventory
    oem_inventory = params.oem_initial_inventory

    t1_shipments = []
    t2_shipments = []

    oem_orders = []
    t2_backlog = 0

    lead_times: List[float] = []
    on_time_shipments = 0
    total_shipments = 0

    daily_wip = []
    daily_backlog = []

    t1_rop = int(params.t1_rop_days * params.avg_daily_demand)
    t1_order_up_to = int(params.t1_order_up_to_days * params.avg_daily_demand)

    for day in range(params.days):
        # Process arrivals to OEM
        arrived_shipments = [s for s in t1_shipments if s["arrival_day"] <= day]
        t1_shipments = [s for s in t1_shipments if s["arrival_day"] > day]
        for shipment in arrived_shipments:
            oem_inventory += shipment["qty"]

        # Process arrivals to T1
        arrived_t2 = [s for s in t2_shipments if s["arrival_day"] <= day]
        t2_shipments = [s for s in t2_shipments if s["arrival_day"] > day]
        for shipment in arrived_t2:
            t1_inventory += shipment["qty"]

        # OEM demand from customer
        demand = _poisson(rng, params.avg_daily_demand)
        if demand <= oem_inventory:
            oem_inventory -= demand
        else:
            oem_inventory = 0

        # OEM places order to T1
        if day % params.oem_order_cycle_days == 0:
            order_size = _poisson(rng, params.avg_daily_demand * params.oem_order_cycle_days)
            if order_size > 0:
                oem_orders.append({"order_day": day, "remaining": order_size})

        # T1 fulfills OEM orders
        for order in oem_orders:
            if order["remaining"] == 0 or t1_inventory == 0:
                continue
            qty = min(order["remaining"], t1_inventory)
            t1_inventory -= qty
            order["remaining"] -= qty
            lead_time = (
                params.t1_to_oem_lead_time_base
                + rng.uniform(0, params.t1_to_oem_lead_time_uniform_max)
            )
            arrival_day = day + math.ceil(lead_time)
            t1_shipments.append(
                {"arrival_day": arrival_day, "qty": qty, "order_day": order["order_day"]}
            )
            lt = arrival_day - order["order_day"]
            lead_times.append(lt)
            total_shipments += 1
            if lt <= params.otif_target_days:
                on_time_shipments += 1

        oem_orders = [order for order in oem_orders if order["remaining"] > 0]

        # T1 inventory policy toward T2
        t1_backlog_qty = sum(order["remaining"] for order in oem_orders)
        t2_pipeline = sum(s["qty"] for s in t2_shipments)
        inventory_position = t1_inventory + t2_pipeline - t1_backlog_qty
        if inventory_position <= t1_rop:
            order_qty = max(0, t1_order_up_to - inventory_position)
            t2_backlog += order_qty

        # T2 production and shipment
        if rng.random() < params.t2_downtime_probability:
            daily_capacity = 0
        else:
            daily_capacity = max(
                0, int(round(rng.gauss(params.t2_daily_mean_capacity, params.t2_daily_capacity_sd)))
            )
        produced = min(t2_backlog, daily_capacity)
        if produced > 0:
            t2_backlog -= produced
            t2_lead_time = params.t2_to_t1_lead_time_base + rng.expovariate(
                1 / params.t2_to_t1_lead_time_exp_mean
            )
            arrival_day = day + math.ceil(t2_lead_time)
            t2_shipments.append({"arrival_day": arrival_day, "qty": produced})

        daily_wip.append(t1_inventory + t2_pipeline)
        daily_backlog.append(t1_backlog_qty)

    mean_lt = sum(lead_times) / len(lead_times) if lead_times else 0.0
    variance = (
        sum((lt - mean_lt) ** 2 for lt in lead_times) / len(lead_times)
        if lead_times
        else 0.0
    )
    std_lt = math.sqrt(variance)
    max_lt = max(lead_times) if lead_times else 0.0
    avg_wip = sum(daily_wip) / len(daily_wip) if daily_wip else 0.0
    avg_backlog = sum(daily_backlog) / len(daily_backlog) if daily_backlog else 0.0
    otif = on_time_shipments / total_shipments if total_shipments else 0.0

    return BaselineResults(
        mean_lead_time=mean_lt,
        lead_time_std=std_lt,
        max_lead_time=max_lt,
        avg_wip=avg_wip,
        avg_backlog=avg_backlog,
        otif=otif,
        lead_times=lead_times,
    )


if __name__ == "__main__":
    results = simulate_baseline()
    print("Baseline Results")
    print(f"Mean lead time: {results.mean_lead_time:.2f} days")
    print(f"Lead time std: {results.lead_time_std:.2f} days")
    print(f"Worst lead time: {results.max_lead_time:.2f} days")
    print(f"Avg WIP: {results.avg_wip:.2f}")
    print(f"Avg backlog: {results.avg_backlog:.2f}")
    print(f"OTIF: {results.otif:.2%}")
