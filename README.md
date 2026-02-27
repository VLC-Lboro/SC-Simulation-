# SC-Simulation-

3-stage automotive supply-chain discrete-event simulator with a GUI and 5 supply-chain-visibility (SCV) scenarios.

## Scenarios

1. Baseline
2. Forecast sharing
3. Inventory visibility
4. Capacity visibility
5. Full visibility (2 + 3 + 4)

## Run GUI

```bash
python gui_application.py
```

## Run baseline-vs-forecast mini GUI

```bash
python gui_forecast_sharing.py
```

## Programmatic run

```python
from supply_chain_simulation import SimulationConfig, run_all_scenarios

config = SimulationConfig(
    simulation_horizon=180,
    random_seed=7,
    demand_distribution_type="poisson",
    demand_params={"lambda": 100.0},
)

results = run_all_scenarios(config)
print(results[1].mean_lead_time, results[5].mean_lead_time)
```

## Tests

```bash
python -m unittest discover -s tests
pytest -q
```
