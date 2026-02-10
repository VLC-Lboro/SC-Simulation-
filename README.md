# SC-Simulation-

Baseline supply chain simulation scaffolding for a three-stage automotive model.

## Quick setup

```bash
python -m pip install -r requirements.txt
```

## Run the baseline simulation

```bash
python -m sc_simulation.baseline
```

## Run the baseline GUI

```bash
python gui_application.py
```

> If `matplotlib` is missing, the GUI still opens but chart tabs are disabled.

## Programmatic usage

```python
from sc_simulation.baseline import BaselineParams, simulate_baseline

params = BaselineParams(days=120, seed=7)
results = simulate_baseline(params)
print(results.mean_lead_time)
```

## Tests

```bash
python -m unittest discover -s tests
```

## Architecture roadmap

This repository is being prepared for scenario-by-scenario development and later merge into a single comparison GUI.
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the planned module layout.
