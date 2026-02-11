"""Supply chain simulation scenarios and comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from statistics import pstdev
from typing import List, Literal


ForecastAccuracyModel = Literal["perfect", "noise"]


@dataclass(frozen=True)
class ForecastSharingConfig:
    """Parameters for forecast generation and usage by T1."""

    forecast_horizon: int = 7
    forecast_update_frequency: int = 2
    forecast_accuracy_model: ForecastAccuracyModel = "perfect"
    forecast_error_std: float = 8.0
    t1_forecast_weight: float = 0.4


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration parameters for baseline and forecast-sharing simulations."""

    num_periods: int = 120
    seed: int = 7
    avg_daily_demand: int = 100
    oem_order_cycle_days: int = 2
    t1_initial_inventory: int = 500
    oem_initial_inventory: int = 500
    t1_rop_days: float = 1.8
    t1_order_up_to_days: float = 5.4
    t1_review_period_days: int = 1
    t2_daily_mean_capacity: int = 105
    t2_daily_capacity_sd: int = 11
    t2_downtime_probability: float = 0.05
    t2_to_t1_lead_time_base: float = 2.0
    t2_to_t1_lead_time_exp_mean: float = 0.5
    t1_to_oem_lead_time_base: float = 1.0
    t1_to_oem_lead_time_uniform_max: float = 0.5
    otif_target_days: float = 2.0
    forecast_sharing: ForecastSharingConfig = ForecastSharingConfig()


@dataclass
class SimulationResults:
    """Results from a simulation run."""

    scenario_name: str
    mean_lead_time: float
    lead_time_std: float
    worst_case_lead_time: float
    mean_wip: float
    mean_backlog: float
    otif_percentage: float
    fill_rate: float
    bullwhip_effect: float
    average_inventory_level: float
    lead_times: List[float]
    wip_levels: List[float]
    backlog_levels: List[float]


@dataclass
class ScenarioComparison:
    baseline: SimulationResults
    forecast_sharing: SimulationResults


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


class ForecastModule:
    """Generates OEM demand forecasts with optional noise."""

    def __init__(
        self,
        config: ForecastSharingConfig,
        avg_daily_demand: int,
        rng: random.Random,
    ) -> None:
        self.config = config
        self.avg_daily_demand = avg_daily_demand
        self.rng = rng
        self.current_forecast: List[float] = [float(avg_daily_demand)] * config.forecast_horizon

    def maybe_update(self, day: int) -> List[float]:
        if day % self.config.forecast_update_frequency == 0:
            self.current_forecast = self._generate_forecast()
        return self.current_forecast

    def _generate_forecast(self) -> List[float]:
        forecast: List[float] = []
        for _ in range(self.config.forecast_horizon):
            base_value = float(self.avg_daily_demand)
            if self.config.forecast_accuracy_model == "perfect":
                forecast.append(base_value)
                continue
            noisy = base_value + self.rng.gauss(0.0, self.config.forecast_error_std)
            forecast.append(max(0.0, noisy))
        return forecast


class SupplyChainSimulation:
    """Three-tier supply chain simulation with optional forecast sharing."""

    def __init__(self, config: SimulationConfig, scenario_name: str = "baseline"):
        self.config = config
        self.scenario_name = scenario_name
        self.use_forecast = scenario_name == "forecast_sharing"
        self.reset()

    def reset(self) -> None:
        self.current_period = 0
        self.rng = random.Random(self.config.seed)

        self.t1_inventory = self.config.t1_initial_inventory
        self.oem_inventory = self.config.oem_initial_inventory

        self.t1_shipments: List[dict] = []
        self.t2_shipments: List[dict] = []
        self.oem_orders: List[dict] = []
        self.t2_backlog = 0

        self.lead_times: List[float] = []
        self.on_time_shipments = 0
        self.total_shipments = 0

        self.wip_levels: List[float] = []
        self.backlog_levels: List[float] = []
        self.inventory_levels: List[float] = []

        self.total_customer_demand = 0
        self.total_customer_fulfilled = 0
        self.oem_order_history: List[int] = []
        self.t1_order_history: List[int] = []

        self.t1_rop = int(self.config.t1_rop_days * self.config.avg_daily_demand)
        self.t1_order_up_to = int(self.config.t1_order_up_to_days * self.config.avg_daily_demand)

        self.forecast_module = ForecastModule(
            self.config.forecast_sharing,
            self.config.avg_daily_demand,
            self.rng,
        )
        self.active_forecast: List[float] = []

    def run_simulation(self) -> SimulationResults:
        for day in range(self.config.num_periods):
            self.current_period = day
            self._process_arrivals()
            self._process_oem_demand()
            self._update_forecast()
            self._place_oem_order()
            self._fulfill_oem_orders()
            self._place_t1_order()
            self._process_t2_production()
            self._track_metrics()

        return self._calculate_results()

    def _process_arrivals(self) -> None:
        arrived_to_oem = [s for s in self.t1_shipments if s["arrival_day"] <= self.current_period]
        self.t1_shipments = [s for s in self.t1_shipments if s["arrival_day"] > self.current_period]
        for shipment in arrived_to_oem:
            self.oem_inventory += shipment["qty"]

        arrived_to_t1 = [s for s in self.t2_shipments if s["arrival_day"] <= self.current_period]
        self.t2_shipments = [s for s in self.t2_shipments if s["arrival_day"] > self.current_period]
        for shipment in arrived_to_t1:
            self.t1_inventory += shipment["qty"]

    def _process_oem_demand(self) -> None:
        demand = _poisson(self.rng, self.config.avg_daily_demand)
        self.total_customer_demand += demand

        fulfilled = min(demand, self.oem_inventory)
        self.oem_inventory -= fulfilled
        self.total_customer_fulfilled += fulfilled

    def _update_forecast(self) -> None:
        if self.use_forecast:
            self.active_forecast = self.forecast_module.maybe_update(self.current_period)

    def _place_oem_order(self) -> None:
        if self.current_period % self.config.oem_order_cycle_days != 0:
            return

        order_size = _poisson(
            self.rng,
            self.config.avg_daily_demand * self.config.oem_order_cycle_days,
        )
        self.oem_order_history.append(order_size)
        if order_size > 0:
            self.oem_orders.append({"order_day": self.current_period, "remaining": order_size})

    def _fulfill_oem_orders(self) -> None:
        for order in self.oem_orders:
            if order["remaining"] == 0 or self.t1_inventory == 0:
                continue

            qty = min(order["remaining"], self.t1_inventory)
            self.t1_inventory -= qty
            order["remaining"] -= qty

            lead_time = self.config.t1_to_oem_lead_time_base + self.rng.uniform(
                0,
                self.config.t1_to_oem_lead_time_uniform_max,
            )
            arrival_day = self.current_period + math.ceil(lead_time)
            self.t1_shipments.append(
                {
                    "arrival_day": arrival_day,
                    "qty": qty,
                    "order_day": order["order_day"],
                }
            )

            lt = arrival_day - order["order_day"]
            self.lead_times.append(lt)
            self.total_shipments += 1
            if lt <= self.config.otif_target_days:
                self.on_time_shipments += 1

        self.oem_orders = [order for order in self.oem_orders if order["remaining"] > 0]

    def _place_t1_order(self) -> None:
        if self.current_period % self.config.t1_review_period_days != 0:
            return

        t1_backlog_qty = sum(order["remaining"] for order in self.oem_orders)
        t2_pipeline = sum(s["qty"] for s in self.t2_shipments)
        inventory_position = self.t1_inventory + t2_pipeline - t1_backlog_qty

        target_order_up_to = self.t1_order_up_to
        if self.use_forecast and self.active_forecast:
            cycle_days = max(1, self.config.oem_order_cycle_days)
            forecast_window = self.active_forecast[:cycle_days]
            expected_cycle_demand = sum(forecast_window)
            blended_cycle_demand = (
                (1 - self.config.forecast_sharing.t1_forecast_weight)
                * (self.config.avg_daily_demand * cycle_days)
                + self.config.forecast_sharing.t1_forecast_weight * expected_cycle_demand
            )
            target_order_up_to += int(round(max(0.0, blended_cycle_demand)))

        order_qty = 0
        if inventory_position <= self.t1_rop:
            order_qty = max(0, target_order_up_to - inventory_position)
            self.t2_backlog += order_qty

        self.t1_order_history.append(order_qty)

    def _process_t2_production(self) -> None:
        if self.rng.random() < self.config.t2_downtime_probability:
            daily_capacity = 0
        else:
            daily_capacity = max(
                0,
                int(
                    round(
                        self.rng.gauss(
                            self.config.t2_daily_mean_capacity,
                            self.config.t2_daily_capacity_sd,
                        )
                    )
                ),
            )

        produced = min(self.t2_backlog, daily_capacity)
        if produced > 0:
            self.t2_backlog -= produced
            t2_lead_time = self.config.t2_to_t1_lead_time_base + self.rng.expovariate(
                1 / self.config.t2_to_t1_lead_time_exp_mean
            )
            arrival_day = self.current_period + math.ceil(t2_lead_time)
            self.t2_shipments.append({"arrival_day": arrival_day, "qty": produced})

    def _track_metrics(self) -> None:
        t1_backlog_qty = sum(order["remaining"] for order in self.oem_orders)
        t2_pipeline = sum(s["qty"] for s in self.t2_shipments)
        self.wip_levels.append(self.t1_inventory + t2_pipeline)
        self.backlog_levels.append(t1_backlog_qty)
        self.inventory_levels.append(self.t1_inventory)

    def _calculate_results(self) -> SimulationResults:
        if self.lead_times:
            mean_lt = sum(self.lead_times) / len(self.lead_times)
            variance = sum((lt - mean_lt) ** 2 for lt in self.lead_times) / len(self.lead_times)
            lead_time_std = math.sqrt(variance)
            worst_case = max(self.lead_times)
        else:
            mean_lt = 0.0
            lead_time_std = 0.0
            worst_case = 0.0

        mean_wip = sum(self.wip_levels) / len(self.wip_levels) if self.wip_levels else 0.0
        mean_backlog = (
            sum(self.backlog_levels) / len(self.backlog_levels) if self.backlog_levels else 0.0
        )
        otif = (self.on_time_shipments / self.total_shipments * 100) if self.total_shipments else 0.0

        fill_rate = (
            self.total_customer_fulfilled / self.total_customer_demand
            if self.total_customer_demand
            else 0.0
        )

        oem_order_std = pstdev(self.oem_order_history) if len(self.oem_order_history) > 1 else 0.0
        t1_order_std = pstdev(self.t1_order_history) if len(self.t1_order_history) > 1 else 0.0
        bullwhip = (t1_order_std / oem_order_std) if oem_order_std > 0 else 0.0

        average_inventory = (
            sum(self.inventory_levels) / len(self.inventory_levels) if self.inventory_levels else 0.0
        )

        return SimulationResults(
            scenario_name=self.scenario_name,
            mean_lead_time=mean_lt,
            lead_time_std=lead_time_std,
            worst_case_lead_time=worst_case,
            mean_wip=mean_wip,
            mean_backlog=mean_backlog,
            otif_percentage=otif,
            fill_rate=fill_rate,
            bullwhip_effect=bullwhip,
            average_inventory_level=average_inventory,
            lead_times=self.lead_times,
            wip_levels=self.wip_levels,
            backlog_levels=self.backlog_levels,
        )


def run_baseline(config: SimulationConfig | None = None) -> SimulationResults:
    """Run the baseline scenario simulation."""
    if config is None:
        config = SimulationConfig()
    simulation = SupplyChainSimulation(config, scenario_name="baseline")
    return simulation.run_simulation()


def run_forecast_sharing(config: SimulationConfig | None = None) -> SimulationResults:
    """Run the forecast-sharing scenario simulation."""
    if config is None:
        config = SimulationConfig()
    simulation = SupplyChainSimulation(config, scenario_name="forecast_sharing")
    return simulation.run_simulation()


def compare_scenarios(config: SimulationConfig | None = None) -> ScenarioComparison:
    """Run baseline and forecast-sharing scenarios for side-by-side analysis."""
    if config is None:
        config = SimulationConfig()

    baseline_results = run_baseline(config)
    forecast_results = run_forecast_sharing(config)
    return ScenarioComparison(baseline=baseline_results, forecast_sharing=forecast_results)
