"""Forecast sharing GUI for side-by-side scenario comparison."""

import tkinter as tk
from tkinter import ttk, messagebox

from supply_chain_simulation import (
    ForecastSharingConfig,
    SimulationConfig,
    compare_scenarios,
)


class ForecastSharingGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Forecast Sharing Supply Chain Simulation")
        self.root.geometry("900x600")

        self.config = SimulationConfig()
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding="12")
        frame.pack(fill=tk.BOTH, expand=True)

        controls = ttk.LabelFrame(frame, text="Forecast Sharing Parameters", padding="10")
        controls.pack(fill=tk.X)

        self.days_var = tk.IntVar(value=self.config.num_periods)
        self.horizon_var = tk.IntVar(value=self.config.forecast_sharing.forecast_horizon)
        self.update_freq_var = tk.IntVar(value=self.config.forecast_sharing.forecast_update_frequency)
        self.error_std_var = tk.DoubleVar(value=self.config.forecast_sharing.forecast_error_std)
        self.weight_var = tk.DoubleVar(value=self.config.forecast_sharing.t1_forecast_weight)
        self.accuracy_var = tk.StringVar(value=self.config.forecast_sharing.forecast_accuracy_model)

        row = 0
        ttk.Label(controls, text="Simulation Days").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.days_var, width=8).grid(row=row, column=1, padx=(4, 16))
        ttk.Label(controls, text="Forecast Horizon").grid(row=row, column=2, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.horizon_var, width=8).grid(row=row, column=3, padx=(4, 16))
        ttk.Label(controls, text="Update Frequency").grid(row=row, column=4, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.update_freq_var, width=8).grid(row=row, column=5, padx=(4, 16))

        row += 1
        ttk.Label(controls, text="Accuracy Model").grid(row=row, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            controls,
            textvariable=self.accuracy_var,
            values=["perfect", "noise"],
            width=10,
            state="readonly",
        ).grid(row=row, column=1, pady=(8, 0), padx=(4, 16))
        ttk.Label(controls, text="Forecast Error Std").grid(row=row, column=2, sticky=tk.W, pady=(8, 0))
        ttk.Entry(controls, textvariable=self.error_std_var, width=8).grid(
            row=row,
            column=3,
            pady=(8, 0),
            padx=(4, 16),
        )
        ttk.Label(controls, text="T1 Forecast Weight").grid(row=row, column=4, sticky=tk.W, pady=(8, 0))
        ttk.Entry(controls, textvariable=self.weight_var, width=8).grid(
            row=row,
            column=5,
            pady=(8, 0),
            padx=(4, 16),
        )

        ttk.Button(controls, text="Run Comparison", command=self._run).grid(
            row=2,
            column=0,
            columnspan=2,
            pady=(12, 0),
            sticky=tk.W,
        )

        self.results = ttk.Treeview(frame, columns=("metric", "baseline", "forecast"), show="headings")
        self.results.heading("metric", text="Metric")
        self.results.heading("baseline", text="Baseline")
        self.results.heading("forecast", text="Forecast Sharing")
        self.results.column("metric", width=220)
        self.results.column("baseline", width=160)
        self.results.column("forecast", width=180)
        self.results.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def _run(self) -> None:
        try:
            config = SimulationConfig(
                num_periods=self.days_var.get(),
                forecast_sharing=ForecastSharingConfig(
                    forecast_horizon=self.horizon_var.get(),
                    forecast_update_frequency=self.update_freq_var.get(),
                    forecast_accuracy_model=self.accuracy_var.get(),
                    forecast_error_std=self.error_std_var.get(),
                    t1_forecast_weight=self.weight_var.get(),
                ),
            )
            comparison = compare_scenarios(config)
            self._render(comparison)
        except Exception as exc:
            messagebox.showerror("Simulation Error", str(exc))

    def _render(self, comparison) -> None:
        for row in self.results.get_children():
            self.results.delete(row)

        metric_rows = [
            ("Fill Rate", comparison.baseline.fill_rate, comparison.forecast_sharing.fill_rate),
            (
                "Mean Lead Time",
                comparison.baseline.mean_lead_time,
                comparison.forecast_sharing.mean_lead_time,
            ),
            (
                "Bullwhip Effect",
                comparison.baseline.bullwhip_effect,
                comparison.forecast_sharing.bullwhip_effect,
            ),
            (
                "Average Inventory",
                comparison.baseline.average_inventory_level,
                comparison.forecast_sharing.average_inventory_level,
            ),
        ]

        for metric, baseline_value, forecast_value in metric_rows:
            self.results.insert(
                "",
                tk.END,
                values=(metric, f"{baseline_value:.3f}", f"{forecast_value:.3f}"),
            )


def main() -> None:
    root = tk.Tk()
    ForecastSharingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
