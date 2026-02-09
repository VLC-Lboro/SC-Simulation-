# SC-Simulation-

Baseline supply chain simulation scaffolding for a three-stage automotive model.

## Run the baseline simulation

```bash
python -m sc_simulation.baseline
```

## Programmatic usage

```python
from sc_simulation.baseline import BaselineParams, simulate_baseline

params = BaselineParams(days=120, seed=7)
results = simulate_baseline(params)
print(results.mean_lead_time)
```

## Tests

```bash
python -m unittest
```
