import random
import unittest

from supply_chain_simulation import (
    ForecastModule,
    ForecastSharingConfig,
    SimulationConfig,
    SupplyChainSimulation,
    compare_scenarios,
    run_baseline,
    run_forecast_sharing,
)


class ForecastModuleTests(unittest.TestCase):
    def test_perfect_forecast_generation(self):
        config = ForecastSharingConfig(
            forecast_horizon=4,
            forecast_update_frequency=1,
            forecast_accuracy_model="perfect",
            forecast_error_std=10.0,
        )
        module = ForecastModule(config, avg_daily_demand=90, rng=random.Random(7))

        forecast = module.maybe_update(day=0)

        self.assertEqual(len(forecast), 4)
        self.assertEqual(forecast, [90.0, 90.0, 90.0, 90.0])

    def test_noisy_forecast_generation(self):
        config = ForecastSharingConfig(
            forecast_horizon=5,
            forecast_update_frequency=1,
            forecast_accuracy_model="noise",
            forecast_error_std=6.0,
        )
        module = ForecastModule(config, avg_daily_demand=100, rng=random.Random(11))

        forecast = module.maybe_update(day=0)

        self.assertEqual(len(forecast), 5)
        self.assertNotEqual(forecast, [100.0] * 5)
        self.assertTrue(all(value >= 0 for value in forecast))


class T1OrderingLogicTests(unittest.TestCase):
    def test_forecast_increases_t1_replenishment_when_weighted(self):
        baseline_cfg = SimulationConfig(
            num_periods=50,
            seed=9,
            t1_initial_inventory=0,
            t1_rop_days=100,
            t1_order_up_to_days=1.0,
        )
        forecast_cfg = SimulationConfig(
            num_periods=50,
            seed=9,
            t1_initial_inventory=0,
            t1_rop_days=100,
            t1_order_up_to_days=1.0,
            forecast_sharing=ForecastSharingConfig(
                forecast_horizon=6,
                forecast_update_frequency=1,
                forecast_accuracy_model="perfect",
                forecast_error_std=0.0,
                t1_forecast_weight=1.0,
            ),
        )

        baseline_sim = SupplyChainSimulation(baseline_cfg, scenario_name="baseline")
        baseline_sim.run_simulation()

        forecast_sim = SupplyChainSimulation(forecast_cfg, scenario_name="forecast_sharing")
        forecast_sim.run_simulation()

        self.assertGreater(sum(forecast_sim.t1_order_history), sum(baseline_sim.t1_order_history))


class ScenarioComparisonTests(unittest.TestCase):
    def test_compare_scenarios_returns_metrics(self):
        config = SimulationConfig(num_periods=30, seed=10)

        baseline = run_baseline(config)
        forecast = run_forecast_sharing(config)
        comparison = compare_scenarios(config)

        self.assertEqual(comparison.baseline.scenario_name, "baseline")
        self.assertEqual(comparison.forecast_sharing.scenario_name, "forecast_sharing")
        self.assertEqual(baseline.scenario_name, "baseline")
        self.assertEqual(forecast.scenario_name, "forecast_sharing")
        self.assertGreaterEqual(comparison.baseline.fill_rate, 0)
        self.assertGreaterEqual(comparison.forecast_sharing.fill_rate, 0)


if __name__ == "__main__":
    unittest.main()
