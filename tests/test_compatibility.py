import unittest

from supply_chain_simulation import SimulationConfig, SupplyChainSimulation, run_baseline


class CompatibilityTests(unittest.TestCase):
    def test_legacy_entrypoints_still_work(self):
        config = SimulationConfig(num_periods=15, seed=1)
        results_direct = run_baseline(config)
        sim = SupplyChainSimulation(config)
        results_class = sim.run_simulation()

        self.assertGreaterEqual(results_direct.mean_lead_time, 0)
        self.assertEqual(results_direct.mean_lead_time, results_class.mean_lead_time)


if __name__ == "__main__":
    unittest.main()
