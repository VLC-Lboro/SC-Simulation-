import unittest

from supply_chain_simulation import SimulationConfig, SupplyChainSimulation, run_baseline


class CompatibilityTests(unittest.TestCase):
    def test_baseline_entrypoints(self):
        cfg = SimulationConfig(simulation_horizon=25, random_seed=1)
        direct = run_baseline(cfg)
        via_class = SupplyChainSimulation(cfg, scenario_id=1).run_simulation()
        self.assertAlmostEqual(direct.mean_lead_time, via_class.mean_lead_time)


if __name__ == "__main__":
    unittest.main()
