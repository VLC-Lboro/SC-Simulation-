# SC-Simulation-

Supply chain simulation scaffolding for a three-stage automotive model.

## Run the baseline simulation

```bash
python -m sc_simulation.baseline
```

## Run forecast sharing scenario comparison GUI

```bash
python gui_forecast_sharing.py
```

## Programmatic usage

```python
from supply_chain_simulation import (
    SimulationConfig,
    ForecastSharingConfig,
    run_baseline,
    run_forecast_sharing,
    compare_scenarios,
)

config = SimulationConfig(
    num_periods=120,
    forecast_sharing=ForecastSharingConfig(
        forecast_horizon=7,
        forecast_update_frequency=2,
        forecast_accuracy_model="noise",
        forecast_error_std=8.0,
        t1_forecast_weight=0.4,
    ),
)

baseline_results = run_baseline(config)
forecast_results = run_forecast_sharing(config)
comparison = compare_scenarios(config)
print(comparison.baseline.fill_rate, comparison.forecast_sharing.fill_rate)
```

## Scenario config metadata

Default metadata for baseline and forecast-sharing parameters is stored in:

- `scenario_config.json`

## Tests

```bash
python -m unittest
```
