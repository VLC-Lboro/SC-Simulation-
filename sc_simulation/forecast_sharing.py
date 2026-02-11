"""Forecast-sharing scenario wrappers for package-level usage."""

from __future__ import annotations

from dataclasses import dataclass

from supply_chain_simulation import (
    ForecastModule,
    ForecastSharingConfig,
    SimulationConfig,
    SimulationResults,
    run_forecast_sharing,
)


@dataclass(frozen=True)
class ForecastSharingParams(SimulationConfig):
    """Package-compatible params alias for forecast-sharing scenario."""


ForecastSharingResults = SimulationResults


def simulate_forecast_sharing(
    params: ForecastSharingParams = ForecastSharingParams(),
) -> ForecastSharingResults:
    return run_forecast_sharing(params)


__all__ = [
    "ForecastModule",
    "ForecastSharingConfig",
    "ForecastSharingParams",
    "ForecastSharingResults",
    "simulate_forecast_sharing",
]
