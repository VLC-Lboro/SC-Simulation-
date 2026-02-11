import random
import unittest

from supply_chain_simulation import (
    ForecastModule,
    ForecastSharingConfig,
    SimulationConfig,
    SupplyChainSimulation,
    compare_scenarios,
)


class ForecastModuleTests(unittest.TestCase):
    def test_perfect_forecast_generation_matches_future_demand_plan(self):
        config = ForecastSharingConfig(
            forecast_horizon=4,
            forecast_update_frequency=1,
            forecast_accuracy_model="perfect",
            forecast_error_std=10.0,
        )
        demand_plan = [95, 102, 99, 105, 98, 100]
        module = ForecastModule(config, demand_plan=demand_plan, rng=random.Random(7))

        forecast = module.maybe_update(day=1)

        self.assertEqual(forecast, [102.0, 99.0, 105.0, 98.0])

    def test_noisy_forecast_generation_has_error(self):
        config = ForecastSharingConfig(
            forecast_horizon=5,
            forecast_update_frequency=1,
            forecast_accuracy_model="noise",
            forecast_error_std=6.0,
        )
        demand_plan = [100, 100, 100, 100, 100, 100]
        module = ForecastModule(config, demand_plan=demand_plan, rng=random.Random(11))

        forecast = module.maybe_update(day=0)

        self.assertEqual(len(forecast), 5)
        self.assertNotEqual(forecast, [100.0] * 5)
        self.assertTrue(all(value >= 0 for value in forecast))


class T1OrderingLogicTests(unittest.TestCase):
    def test_forecast_changes_t1_replenishment_behavior(self):
        baseline_cfg = SimulationConfig(
            num_periods=70,
            seed=9,
            t1_initial_inventory=100,
            t1_rop_days=2.0,
            t1_order_up_to_days=5.0,
        )
        forecast_cfg = SimulationConfig(
            num_periods=70,
            seed=9,
            t1_initial_inventory=100,
            t1_rop_days=2.0,
            t1_order_up_to_days=5.0,
            forecast_sharing=ForecastSharingConfig(
                forecast_horizon=8,
                forecast_update_frequency=1,
                forecast_accuracy_model="noise",
                forecast_error_std=25.0,
                t1_forecast_weight=1.0,
            ),
        )

        baseline_sim = SupplyChainSimulation(baseline_cfg, scenario_name="baseline")
        baseline_sim.run_simulation()

        forecast_sim = SupplyChainSimulation(forecast_cfg, scenario_name="forecast_sharing")
        forecast_sim.run_simulation()

        self.assertNotEqual(sum(forecast_sim.t1_order_history), sum(baseline_sim.t1_order_history))


class ScenarioComparisonTests(unittest.TestCase):
    def test_compare_scenarios_returns_full_kpis(self):
        config = SimulationConfig(
            num_periods=60,
            seed=10,
            forecast_sharing=ForecastSharingConfig(
                forecast_horizon=7,
                forecast_update_frequency=1,
                forecast_accuracy_model="noise",
                forecast_error_std=18.0,
                t1_forecast_weight=0.8,
            ),
        )

        comparison = compare_scenarios(config)

        self.assertEqual(comparison.baseline.scenario_name, "baseline")
        self.assertEqual(comparison.forecast_sharing.scenario_name, "forecast_sharing")

        self.assertGreaterEqual(comparison.baseline.fill_rate, 0)
        self.assertGreaterEqual(comparison.forecast_sharing.fill_rate, 0)
        self.assertGreaterEqual(comparison.baseline.otif_percentage, 0)
        self.assertGreaterEqual(comparison.forecast_sharing.otif_percentage, 0)

        deltas = [
            abs(comparison.forecast_sharing.mean_wip - comparison.baseline.mean_wip),
            abs(comparison.forecast_sharing.mean_backlog - comparison.baseline.mean_backlog),
            abs(comparison.forecast_sharing.otif_percentage - comparison.baseline.otif_percentage),
            abs(comparison.forecast_sharing.fill_rate - comparison.baseline.fill_rate),
            abs(comparison.forecast_sharing.bullwhip_effect - comparison.baseline.bullwhip_effect),
        ]
        self.assertTrue(any(delta > 1e-9 for delta in deltas))


if __name__ == "__main__":
    unittest.main()
