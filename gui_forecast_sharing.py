"""Simple GUI for baseline vs forecast-sharing (Scenario 2)."""

import tkinter as tk
from tkinter import messagebox, ttk

from supply_chain_simulation import SimulationConfig, compare_scenarios


class ForecastSharingGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Baseline vs Forecast Sharing")
        self.root.geometry("760x420")
        self.days_var = tk.IntVar(value=180)
        self.seed_var = tk.IntVar(value=7)
        self.demand_var = tk.DoubleVar(value=100.0)
        self._build()

    def _build(self) -> None:
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Days").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(frm, textvariable=self.days_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(frm, text="Seed").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(frm, textvariable=self.seed_var, width=8).grid(row=0, column=3, padx=5)
        ttk.Label(frm, text="Poisson λ").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(frm, textvariable=self.demand_var, width=8).grid(row=0, column=5, padx=5)
        ttk.Button(frm, text="Run", command=self._run).grid(row=0, column=6, padx=8)

        self.tree = ttk.Treeview(frm, columns=("metric", "baseline", "forecast"), show="headings")
        for key, title, width in [("metric", "Metric", 220), ("baseline", "Baseline", 140), ("forecast", "Forecast", 140)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        self.tree.grid(row=1, column=0, columnspan=7, sticky="nsew", pady=10)
        frm.rowconfigure(1, weight=1)

    def _run(self) -> None:
        try:
            config = SimulationConfig(
                simulation_horizon=self.days_var.get(),
                random_seed=self.seed_var.get(),
                demand_distribution_type="poisson",
                demand_params={"lambda": self.demand_var.get()},
            )
            comparison = compare_scenarios(config)
            self._render(comparison)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _render(self, cmp) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = [
            ("Mean LT", cmp.baseline.mean_lead_time, cmp.forecast_sharing.mean_lead_time),
            ("P95 LT", cmp.baseline.worst_case_lead_time_p95, cmp.forecast_sharing.worst_case_lead_time_p95),
            ("Mean Backlog T1", cmp.baseline.mean_backlog_t1, cmp.forecast_sharing.mean_backlog_t1),
            ("Bullwhip", cmp.baseline.bullwhip_ratio, cmp.forecast_sharing.bullwhip_ratio),
        ]
        for metric, b, f in rows:
            self.tree.insert("", tk.END, values=(metric, f"{b:.2f}", f"{f:.2f}"))


if __name__ == "__main__":
    root = tk.Tk()
    ForecastSharingGUI(root)
    root.mainloop()
