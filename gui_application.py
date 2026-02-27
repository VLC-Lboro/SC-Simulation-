"""Tkinter GUI for the 5-scenario supply-chain simulation."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from supply_chain_simulation import SimulationConfig, run_all_scenarios


class SupplyChainGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("3-Stage Supply Chain SCV Simulation")
        self.root.geometry("1200x760")
        self.results = None
        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        controls = ttk.LabelFrame(main, text="Parameters", padding=10)
        controls.pack(side=tk.LEFT, fill=tk.Y)

        self.horizon_var = tk.IntVar(value=180)
        self.seed_var = tk.IntVar(value=7)
        self.dist_var = tk.StringVar(value="poisson")
        self.demand_var = tk.DoubleVar(value=100.0)
        self.t1_cap_var = tk.IntVar(value=140)
        self.t23_cap_var = tk.IntVar(value=130)

        rows = [
            ("Horizon (days)", self.horizon_var),
            ("Random seed", self.seed_var),
            ("Expected daily demand", self.demand_var),
            ("T1 capacity/day", self.t1_cap_var),
            ("T23 capacity/day", self.t23_cap_var),
        ]
        for idx, (label, var) in enumerate(rows):
            ttk.Label(controls, text=label).grid(row=idx, column=0, sticky=tk.W, pady=4)
            ttk.Entry(controls, textvariable=var, width=12).grid(row=idx, column=1, sticky=tk.W, pady=4)

        ttk.Label(controls, text="Demand dist").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(controls, textvariable=self.dist_var, values=["poisson", "normal", "deterministic"], width=10, state="readonly").grid(row=5, column=1, sticky=tk.W, pady=4)

        ttk.Button(controls, text="Run all 5 scenarios", command=self._run).grid(row=6, column=0, columnspan=2, pady=10)
        self.status = ttk.Label(controls, text="")
        self.status.grid(row=7, column=0, columnspan=2, sticky=tk.W)

        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(right, columns=("scenario", "mean_lt", "p95_lt", "std_lt", "mean_backlog", "bullwhip"), show="headings", height=8)
        for key, title, width in [
            ("scenario", "Scenario", 200),
            ("mean_lt", "Mean LT", 80),
            ("p95_lt", "P95 LT", 80),
            ("std_lt", "LT Std", 80),
            ("mean_backlog", "Mean Backlog", 110),
            ("bullwhip", "Bullwhip", 90),
        ]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        self.tree.pack(fill=tk.X, pady=(0, 8))

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.fig_frame = ttk.Frame(self.notebook)
        self.flow_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fig_frame, text="Lead Time + Backlog")
        self.notebook.add(self.flow_frame, text="Orders + Demand")

    def _run(self) -> None:
        try:
            demand_type = self.dist_var.get()
            demand_params = {
                "poisson": {"lambda": self.demand_var.get()},
                "normal": {"mean": self.demand_var.get(), "std_dev": 20.0},
                "deterministic": {"value": self.demand_var.get()},
            }[demand_type]

            config = SimulationConfig(
                simulation_horizon=self.horizon_var.get(),
                random_seed=self.seed_var.get(),
                demand_distribution_type=demand_type,
                demand_params=demand_params,
                t1_daily_capacity=self.t1_cap_var.get(),
                t23_daily_capacity=self.t23_cap_var.get(),
            )

            self.status.config(text="Running...")
            self.root.update_idletasks()
            self.results = run_all_scenarios(config)
            self._populate_table()
            self._plot()
            self.status.config(text="Done")
        except Exception as exc:
            messagebox.showerror("Simulation error", str(exc))
            self.status.config(text="Failed")

    def _populate_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for scenario_id in [1, 2, 3, 4, 5]:
            r = self.results[scenario_id]
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r.scenario_name,
                    f"{r.mean_lead_time:.2f}",
                    f"{r.worst_case_lead_time_p95:.2f}",
                    f"{r.lead_time_std:.2f}",
                    f"{r.mean_backlog_t1:.2f}",
                    "NaN" if str(r.bullwhip_ratio) == "nan" else f"{r.bullwhip_ratio:.2f}",
                ),
            )

    def _plot(self) -> None:
        for frame in [self.fig_frame, self.flow_frame]:
            for child in frame.winfo_children():
                child.destroy()

        baseline = self.results[1]
        full = self.results[5]

        fig1 = Figure(figsize=(9, 4))
        ax1 = fig1.add_subplot(121)
        ax1.hist(baseline.lead_times, bins=20, alpha=0.6, label="Baseline")
        ax1.hist(full.lead_times, bins=20, alpha=0.6, label="Full vis")
        ax1.set_title("Lead-time distribution")
        ax1.legend()

        ax2 = fig1.add_subplot(122)
        ax2.plot(baseline.t1_backlog_units, label="Baseline")
        ax2.plot(full.t1_backlog_units, label="Full vis")
        ax2.set_title("T1 backlog trend")
        ax2.legend()
        fig1.tight_layout()
        c1 = FigureCanvasTkAgg(fig1, self.fig_frame)
        c1.draw()
        c1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        fig2 = Figure(figsize=(9, 4))
        ax3 = fig2.add_subplot(111)
        ax3.plot(baseline.daily_oem_demand, label="OEM demand", alpha=0.8)
        ax3.plot(baseline.t1_to_t23_orders, label="T1->T23 orders", alpha=0.8)
        ax3.set_title("Baseline demand vs upstream orders")
        ax3.legend()
        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, self.flow_frame)
        c2.draw()
        c2.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def main() -> None:
    root = tk.Tk()
    SupplyChainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
