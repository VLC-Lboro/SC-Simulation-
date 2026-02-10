# Repository Architecture Plan

This project is being built scenario-by-scenario.

## Current implementation
- Scenario 1 (Baseline): implemented in `sc_simulation/baseline.py`.
- Legacy compatibility imports: `supply_chain_simulation.py` delegates to `sc_simulation.baseline`.
- GUI: `gui_application.py` currently runs baseline only.

## Planned structure for scenarios
Create one module per scenario with a consistent API:

- `sc_simulation/scenario_1_baseline.py`
- `sc_simulation/scenario_2_forecast_sharing.py`
- `sc_simulation/scenario_3_inventory_visibility.py`
- `sc_simulation/scenario_4_capacity_visibility.py`
- `sc_simulation/scenario_5_full_visibility.py`

Each module should expose:
- `Params` dataclass
- `Results` dataclass
- `simulate_<scenario>(params)` function

## Testing strategy
- Add one test file per scenario under `tests/`.
- Keep deterministic seeds for reproducible comparisons.
- Add regression tests before merging each scenario into a combined GUI.

## Merge strategy
1. Build and validate each scenario independently.
2. Add a scenario selector in one unified GUI at the end.
3. Keep per-scenario modules intact for reproducibility and debugging.
