"""Compatibility API for legacy imports.

This module keeps the old import path working while delegating to the
package implementation in ``sc_simulation.baseline``.
"""

from sc_simulation.baseline import BaselineParams, BaselineResults, simulate_baseline


# Backward-compatible aliases
SimulationConfig = BaselineParams
SimulationResults = BaselineResults


class SupplyChainSimulation:
    """Simple adapter that mirrors the old class-based entrypoint."""

    def __init__(self, config: SimulationConfig):
        self.config = config

    def run_simulation(self) -> SimulationResults:
        return simulate_baseline(self.config)


def run_baseline(config: SimulationConfig | None = None) -> SimulationResults:
    """Run the baseline simulation using the compatibility API."""
    if config is None:
        config = SimulationConfig()
    return simulate_baseline(config)
