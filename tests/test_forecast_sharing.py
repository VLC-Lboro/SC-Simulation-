import unittest

from supply_chain_simulation import SimulationConfig, compare_scenarios, run_scenario


class ScenarioPolicyTests(unittest.TestCase):
    def test_all_scenarios_run(self):
        config = SimulationConfig(simulation_horizon=40, random_seed=11)
        for scenario in [1, 2, 3, 4, 5]:
            result = run_scenario(config, scenario)
            self.assertEqual(result.scenario_id, scenario)
            self.assertEqual(len(result.daily_oem_demand), 40)

    def test_compare_has_baseline_and_forecast(self):
        config = SimulationConfig(simulation_horizon=30, random_seed=5)
        cmp = compare_scenarios(config)
        self.assertEqual(cmp.baseline.scenario_name, "baseline")
        self.assertEqual(cmp.forecast_sharing.scenario_name, "forecast_sharing")


if __name__ == "__main__":
    unittest.main()
