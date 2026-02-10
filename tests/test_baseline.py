import unittest

from sc_simulation.baseline import BaselineParams, simulate_baseline


class BaselineSimulationTests(unittest.TestCase):
    def test_baseline_metrics_are_reasonable(self):
        params = BaselineParams(days=30, seed=42)
        results = simulate_baseline(params)
        self.assertGreater(results.mean_lead_time, 0)
        self.assertGreaterEqual(results.max_lead_time, results.mean_lead_time)
        self.assertGreater(results.avg_wip, 0)
        self.assertGreaterEqual(results.otif, 0)
        self.assertLessEqual(results.otif, 1)


if __name__ == "__main__":
    unittest.main()
