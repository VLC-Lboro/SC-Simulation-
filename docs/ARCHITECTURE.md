# Repository Architecture Plan

This project is built scenario-by-scenario.

## Current implementation
- Scenario 1 (Baseline): implemented and available via `run_baseline`.
- Scenario 2 (Forecast Sharing): implemented and available via `run_forecast_sharing`.
- Scenario comparison utility: `compare_scenarios` returns baseline vs forecast-sharing metrics.
- Baseline-only GUI: `gui_application.py`.
- Forecast-sharing comparison GUI: `gui_forecast_sharing.py`.

## Scenario modules
- `sc_simulation/baseline.py`
- `sc_simulation/forecast_sharing.py`

## Forecast-sharing metrics tracked
- Fill rate
- Lead time (mean/std/worst)
- Bullwhip effect (std of T1 orders / std of OEM orders)
- Inventory level and WIP/backlog trends

## Testing strategy
- Unit tests for baseline scenario under `tests/test_baseline.py`
- Compatibility tests for legacy entrypoints under `tests/test_compatibility.py`
- Forecast module, T1 ordering logic, and comparison tests under `tests/test_forecast_sharing.py`
