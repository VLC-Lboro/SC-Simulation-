import unittest

from supply_chain_simulation import SimulationConfig, run_baseline


class BaselineSimulationTests(unittest.TestCase):
    def test_baseline_metrics_are_reasonable(self):
        params = SimulationConfig(simulation_horizon=30, random_seed=42)
        results = run_baseline(params)
        self.assertGreaterEqual(results.mean_lead_time, 0)
        self.assertGreaterEqual(results.max_backlog_t1, 0)
        self.assertEqual(len(results.t1_backlog_units), 30)


if __name__ == "__main__":
    unittest.main()
