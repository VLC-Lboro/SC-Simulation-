"""3-stage supply-chain discrete-event simulation with 5 SCV scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from statistics import mean, pstdev
from typing import Dict, List, Literal, Optional

DemandType = Literal["poisson", "normal", "deterministic"]


@dataclass(frozen=True)
class SimulationConfig:
    simulation_horizon: int = 180
    random_seed: int = 7
    demand_distribution_type: DemandType = "poisson"
    demand_params: Dict[str, float] = field(default_factory=lambda: {"lambda": 100.0})
    transport_delay_t1_to_oem: int = 1
    transport_delay_t23_to_t1: int = 2
    t1_daily_capacity: int = 140
    t23_daily_capacity: int = 130
    initial_oem_inventory: int = 600
    initial_t1_inventory: int = 600
    oem_order_up_to_S: float = 700
    oem_forecast_horizon: int = 7
    t1_order_up_to_S: float = 720
    t1_reorder_point_R: float = 0.0
    beta_f: float = 0.10
    alpha_inv: float = 0.30
    oem_inventory_target: Optional[float] = None
    replications_per_scenario: int = 1

    def validate(self) -> None:
        if self.simulation_horizon < 1:
            raise ValueError("simulation_horizon must be >= 1")
        for value, name in [
            (self.t1_daily_capacity, "t1_daily_capacity"),
            (self.t23_daily_capacity, "t23_daily_capacity"),
            (self.initial_oem_inventory, "initial_oem_inventory"),
            (self.initial_t1_inventory, "initial_t1_inventory"),
            (self.transport_delay_t1_to_oem, "transport_delay_t1_to_oem"),
            (self.transport_delay_t23_to_t1, "transport_delay_t23_to_t1"),
            (self.replications_per_scenario, "replications_per_scenario"),
        ]:
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
        if self.replications_per_scenario < 1:
            raise ValueError("replications_per_scenario must be >= 1")
        if self.demand_distribution_type == "poisson":
            if self.demand_params.get("lambda", 0) <= 0:
                raise ValueError("poisson lambda must be > 0")
        elif self.demand_distribution_type == "normal":
            if self.demand_params.get("std_dev", -1) < 0:
                raise ValueError("normal std_dev must be >= 0")
        elif self.demand_distribution_type == "deterministic":
            if self.demand_params.get("value", -1) < 0:
                raise ValueError("deterministic value must be >= 0")
        else:
            raise ValueError("Unsupported demand_distribution_type")


@dataclass
class OrderLogEntry:
    order_id: int
    day_placed: int
    day_shipped: Optional[int]
    day_received: Optional[int]
    qty: int


@dataclass
class SimulationResults:
    scenario_id: int
    scenario_name: str
    mean_lead_time: float
    lead_time_std: float
    worst_case_lead_time_p95: float
    mean_backlog_t1: float
    max_backlog_t1: int
    bullwhip_ratio: float
    mean_wip: float
    daily_oem_demand: List[int]
    oem_to_t1_orders: List[int]
    t1_to_t23_orders: List[int]
    t1_backlog_units: List[int]
    t1_on_hand: List[int]
    t1_shipments_to_oem: List[int]
    t23_backlog_units: List[int]
    t23_production: List[int]
    oem_on_hand: List[int]
    lead_times: List[int]
    order_log: List[OrderLogEntry]


@dataclass
class ScenarioComparison:
    baseline: SimulationResults
    forecast_sharing: SimulationResults


def _round_nonnegative(value: float) -> int:
    return max(0, int(round(value)))


def _pop_variance(values: List[int]) -> float:
    if not values:
        return 0.0
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / len(values)


def _percentile_inclusive(values: List[int], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * percentile
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return float(sorted_values[low])
    frac = pos - low
    return sorted_values[low] + frac * (sorted_values[high] - sorted_values[low])


def _poisson(rng: random.Random, lam: float) -> int:
    threshold = math.exp(-lam)
    k = 0
    p = 1.0
    while p > threshold:
        k += 1
        p *= rng.random()
    return k - 1


def _scenario_name(scenario_id: int) -> str:
    return {
        1: "baseline",
        2: "forecast_sharing",
        3: "inventory_visibility",
        4: "capacity_visibility",
        5: "full_visibility",
    }[scenario_id]


class SupplyChainSimulation:
    def __init__(self, config: SimulationConfig, scenario_id: int = 1, seed_offset: int = 0):
        self.config = config
        self.config.validate()
        self.scenario_id = scenario_id
        self.rng = random.Random(config.random_seed + seed_offset)
        self._next_order_id = 1

    def _demand_sample(self) -> int:
        dist = self.config.demand_distribution_type
        p = self.config.demand_params
        if dist == "poisson":
            return _poisson(self.rng, p["lambda"])
        if dist == "normal":
            return max(0, int(round(self.rng.gauss(p["mean"], p["std_dev"]))))
        return max(0, int(round(p["value"])))

    def _expected_demand(self) -> float:
        if self.config.demand_distribution_type == "poisson":
            return self.config.demand_params["lambda"]
        if self.config.demand_distribution_type == "normal":
            return self.config.demand_params["mean"]
        return self.config.demand_params["value"]

    def _forecast_sum(self, day: int) -> float:
        horizon_remaining = max(0, self.config.simulation_horizon - (day + 1))
        horizon = min(self.config.oem_forecast_horizon, horizon_remaining)
        return self._expected_demand() * horizon

    def run_simulation(self) -> SimulationResults:
        c = self.config
        oem_on_hand = c.initial_oem_inventory
        t1_on_hand = c.initial_t1_inventory

        oem_order_pipeline: List[Dict[str, Optional[int]]] = []
        t1_backlog_queue: List[Dict[str, Optional[int]]] = []
        t1_inbound_shipments: List[Dict[str, int]] = []
        t1_outbound_shipments: List[Dict[str, int]] = []
        t23_order_backlog_queue: List[Dict[str, int]] = []

        daily_oem_demand: List[int] = []
        oem_to_t1_orders: List[int] = []
        t1_to_t23_orders: List[int] = []
        t1_backlog_units: List[int] = []
        t1_on_hand_ts: List[int] = []
        t1_shipments_to_oem: List[int] = []
        t23_backlog_units: List[int] = []
        t23_production: List[int] = []
        oem_on_hand_ts: List[int] = []
        lead_times: List[int] = []

        for day in range(c.simulation_horizon):
            # 1) T1 receives inbound shipments from T23
            arrivals_t1 = [s for s in t1_inbound_shipments if s["arrival_day"] == day]
            t1_on_hand += sum(s["qty"] for s in arrivals_t1)
            t1_inbound_shipments = [s for s in t1_inbound_shipments if s["arrival_day"] != day]

            # 2) OEM receives inbound shipments from T1
            arrivals_oem = [s for s in t1_outbound_shipments if s["arrival_day"] == day]
            for shipment in arrivals_oem:
                oem_on_hand += shipment["qty"]
                matching = next((o for o in oem_order_pipeline if o["order_id"] == shipment["order_id"] and o["day_received"] is None), None)
                if matching is not None:
                    matching["day_received"] = day
                    lead_times.append(day - int(matching["day_placed"]))
            t1_outbound_shipments = [s for s in t1_outbound_shipments if s["arrival_day"] != day]

            # 3) OEM demand realization
            demand = self._demand_sample()
            daily_oem_demand.append(demand)
            oem_on_hand = max(0, oem_on_hand - demand)

            # 4) OEM ordering decision
            pipeline_qty = sum(int(o["qty"]) for o in oem_order_pipeline if o["day_received"] is None)
            ip_oem = oem_on_hand + pipeline_qty
            oem_order_qty = _round_nonnegative(max(0.0, c.oem_order_up_to_S - ip_oem))
            oem_to_t1_orders.append(oem_order_qty)
            if oem_order_qty > 0:
                order = {
                    "order_id": self._next_order_id,
                    "qty": oem_order_qty,
                    "day_placed": day,
                    "day_shipped": None,
                    "day_received": None,
                }
                self._next_order_id += 1
                oem_order_pipeline.append(order)
                t1_backlog_queue.append(
                    {
                        "order_id": order["order_id"],
                        "qty": order["qty"],
                        "day_received_from_oem": day,
                        "day_shipped": None,
                    }
                )

            # 5) T1 shipping to OEM
            available_shipping_capacity = c.t1_daily_capacity
            shipped_today = 0
            while t1_backlog_queue:
                oldest = t1_backlog_queue[0]
                qty = int(oldest["qty"])
                if t1_on_hand >= qty and available_shipping_capacity >= qty:
                    t1_on_hand -= qty
                    available_shipping_capacity -= qty
                    shipped_today += qty
                    oldest["day_shipped"] = day
                    matching = next(o for o in oem_order_pipeline if o["order_id"] == oldest["order_id"])
                    matching["day_shipped"] = day
                    t1_outbound_shipments.append(
                        {
                            "order_id": int(oldest["order_id"]),
                            "qty": qty,
                            "dispatch_day": day,
                            "arrival_day": day + c.transport_delay_t1_to_oem,
                        }
                    )
                    t1_backlog_queue.pop(0)
                else:
                    break

            backlog_qty_after_shipping = sum(int(o["qty"]) for o in t1_backlog_queue)

            # 6) T1 upstream ordering
            inbound_pipeline_qty = sum(s["qty"] for s in t1_inbound_shipments if s["arrival_day"] > day)
            ip_t1 = t1_on_hand + inbound_pipeline_qty - backlog_qty_after_shipping
            s_t1_effective = c.t1_order_up_to_S

            if self.scenario_id in (2, 5):
                s_t1_effective += c.beta_f * self._forecast_sum(day)
            if self.scenario_id in (3, 5):
                target = c.oem_inventory_target if c.oem_inventory_target is not None else c.oem_order_up_to_S
                s_t1_effective = max(0.0, s_t1_effective - c.alpha_inv * (oem_on_hand - target))

            t1_order_raw = max(0.0, s_t1_effective - ip_t1)
            if self.scenario_id in (4, 5):
                t1_order_raw = min(t1_order_raw, float(c.t23_daily_capacity))

            t1_order_qty = _round_nonnegative(t1_order_raw)
            t1_to_t23_orders.append(t1_order_qty)
            if t1_order_qty > 0:
                t23_order_backlog_queue.append({"qty": t1_order_qty, "day_received_from_t1": day})

            # 7) T23 production (FIFO, partial allowed)
            available_capacity = c.t23_daily_capacity
            produced_today = 0
            while available_capacity > 0 and t23_order_backlog_queue:
                oldest = t23_order_backlog_queue[0]
                produce = min(available_capacity, oldest["qty"])
                oldest["qty"] -= produce
                available_capacity -= produce
                produced_today += produce
                if oldest["qty"] == 0:
                    t23_order_backlog_queue.pop(0)

            # 8) T23 dispatch to T1
            if produced_today > 0:
                t1_inbound_shipments.append(
                    {
                        "qty": produced_today,
                        "dispatch_day": day,
                        "arrival_day": day + c.transport_delay_t23_to_t1,
                    }
                )

            # 9) End-of-day metrics
            t1_shipments_to_oem.append(shipped_today)
            t1_backlog_units.append(backlog_qty_after_shipping)
            t1_on_hand_ts.append(t1_on_hand)
            t23_backlog_units.append(sum(o["qty"] for o in t23_order_backlog_queue))
            t23_production.append(produced_today)
            oem_on_hand_ts.append(oem_on_hand)

        mean_backlog = mean(t1_backlog_units) if t1_backlog_units else 0.0
        demand_variance = _pop_variance(daily_oem_demand)
        order_variance = _pop_variance(t1_to_t23_orders)
        bullwhip = order_variance / demand_variance if demand_variance > 0 else float("nan")
        mean_wip = mean([t1_on_hand_ts[i] + t23_backlog_units[i] for i in range(len(t1_on_hand_ts))]) if t1_on_hand_ts else 0.0

        order_log = [
            OrderLogEntry(
                order_id=int(o["order_id"]),
                day_placed=int(o["day_placed"]),
                day_shipped=None if o["day_shipped"] is None else int(o["day_shipped"]),
                day_received=None if o["day_received"] is None else int(o["day_received"]),
                qty=int(o["qty"]),
            )
            for o in oem_order_pipeline
        ]

        return SimulationResults(
            scenario_id=self.scenario_id,
            scenario_name=_scenario_name(self.scenario_id),
            mean_lead_time=mean(lead_times) if lead_times else 0.0,
            lead_time_std=pstdev(lead_times) if len(lead_times) > 1 else 0.0,
            worst_case_lead_time_p95=_percentile_inclusive(lead_times, 0.95),
            mean_backlog_t1=mean_backlog,
            max_backlog_t1=max(t1_backlog_units) if t1_backlog_units else 0,
            bullwhip_ratio=bullwhip,
            mean_wip=mean_wip,
            daily_oem_demand=daily_oem_demand,
            oem_to_t1_orders=oem_to_t1_orders,
            t1_to_t23_orders=t1_to_t23_orders,
            t1_backlog_units=t1_backlog_units,
            t1_on_hand=t1_on_hand_ts,
            t1_shipments_to_oem=t1_shipments_to_oem,
            t23_backlog_units=t23_backlog_units,
            t23_production=t23_production,
            oem_on_hand=oem_on_hand_ts,
            lead_times=lead_times,
            order_log=order_log,
        )


def run_scenario(config: SimulationConfig, scenario_id: int) -> SimulationResults:
    if scenario_id not in {1, 2, 3, 4, 5}:
        raise ValueError("scenario_id must be in {1,2,3,4,5}")

    all_results = [SupplyChainSimulation(config, scenario_id, seed_offset=i).run_simulation() for i in range(config.replications_per_scenario)]
    if len(all_results) == 1:
        return all_results[0]

    # Aggregate scalar KPIs across replications; keep timeseries from replication 0.
    base = all_results[0]
    return SimulationResults(
        scenario_id=scenario_id,
        scenario_name=base.scenario_name,
        mean_lead_time=mean(r.mean_lead_time for r in all_results),
        lead_time_std=mean(r.lead_time_std for r in all_results),
        worst_case_lead_time_p95=mean(r.worst_case_lead_time_p95 for r in all_results),
        mean_backlog_t1=mean(r.mean_backlog_t1 for r in all_results),
        max_backlog_t1=max(r.max_backlog_t1 for r in all_results),
        bullwhip_ratio=mean(r.bullwhip_ratio for r in all_results),
        mean_wip=mean(r.mean_wip for r in all_results),
        daily_oem_demand=base.daily_oem_demand,
        oem_to_t1_orders=base.oem_to_t1_orders,
        t1_to_t23_orders=base.t1_to_t23_orders,
        t1_backlog_units=base.t1_backlog_units,
        t1_on_hand=base.t1_on_hand,
        t1_shipments_to_oem=base.t1_shipments_to_oem,
        t23_backlog_units=base.t23_backlog_units,
        t23_production=base.t23_production,
        oem_on_hand=base.oem_on_hand,
        lead_times=base.lead_times,
        order_log=base.order_log,
    )


def run_baseline(config: SimulationConfig) -> SimulationResults:
    return run_scenario(config, 1)


def run_forecast_sharing(config: SimulationConfig) -> SimulationResults:
    return run_scenario(config, 2)


def compare_scenarios(config: SimulationConfig) -> ScenarioComparison:
    return ScenarioComparison(baseline=run_scenario(config, 1), forecast_sharing=run_scenario(config, 2))


def run_all_scenarios(config: SimulationConfig) -> Dict[int, SimulationResults]:
    return {scenario_id: run_scenario(config, scenario_id) for scenario_id in [1, 2, 3, 4, 5]}
