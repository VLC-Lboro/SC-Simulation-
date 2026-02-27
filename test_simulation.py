from supply_chain_simulation import SimulationConfig, run_all_scenarios


def test_all_scenarios_smoke() -> None:
    config = SimulationConfig(simulation_horizon=20, random_seed=42)
    results = run_all_scenarios(config)
    assert len(results) == 5
    assert results[1].mean_lead_time >= 0
