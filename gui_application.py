"""
Supply Chain Simulation GUI Application
Baseline-only interface for running and inspecting results.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from supply_chain_simulation import SimulationConfig, run_baseline


class SupplyChainGUI:
    """GUI application for the baseline supply chain simulation."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Baseline Supply Chain Simulation")
        self.root.geometry("1200x800")

        self.config = SimulationConfig()
        self.results = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)

        self._create_control_panel(main_container)
        self._create_results_panel(main_container)

    def _create_control_panel(self, parent: ttk.Frame) -> None:
        control_frame = ttk.LabelFrame(parent, text="Baseline Parameters", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        ttk.Label(
            control_frame,
            text="Baseline Scenario",
            font=("Helvetica", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(control_frame, text="Simulation Days:").grid(row=1, column=0, sticky=tk.W)
        self.days_var = tk.IntVar(value=self.config.num_periods)
        ttk.Entry(control_frame, textvariable=self.days_var, width=10).grid(
            row=1, column=1, sticky=tk.W
        )

        ttk.Label(control_frame, text="Avg Daily Demand:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.demand_var = tk.IntVar(value=self.config.avg_daily_demand)
        ttk.Entry(control_frame, textvariable=self.demand_var, width=10).grid(
            row=2, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(control_frame, text="T1 ROP (days):").grid(row=3, column=0, sticky=tk.W)
        self.rop_var = tk.DoubleVar(value=self.config.t1_rop_days)
        ttk.Entry(control_frame, textvariable=self.rop_var, width=10).grid(
            row=3, column=1, sticky=tk.W
        )

        ttk.Label(control_frame, text="T1 Order-up-to (days):").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        self.order_up_to_var = tk.DoubleVar(value=self.config.t1_order_up_to_days)
        ttk.Entry(control_frame, textvariable=self.order_up_to_var, width=10).grid(
            row=4, column=1, sticky=tk.W, pady=5
        )

        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Run Baseline", command=self._run_baseline).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(button_frame, text="Clear Results", command=self._clear_results).grid(
            row=0, column=1, padx=5
        )

        self.progress_label = ttk.Label(control_frame, text="", foreground="blue")
        self.progress_label.grid(row=6, column=0, columnspan=2, pady=5)

    def _create_results_panel(self, parent: ttk.Frame) -> None:
        results_frame = ttk.Frame(parent)
        results_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)

        table_frame = ttk.LabelFrame(results_frame, text="Baseline Results", padding="10")
        table_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)

        columns = ("Metric", "Value")
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        self.results_tree.heading("Metric", text="Metric")
        self.results_tree.heading("Value", text="Value")
        self.results_tree.column("Metric", width=200)
        self.results_tree.column("Value", width=150)
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        viz_frame = ttk.LabelFrame(results_frame, text="Visualizations", padding="10")
        viz_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        viz_frame.columnconfigure(0, weight=1)
        viz_frame.rowconfigure(0, weight=1)

        self.viz_notebook = ttk.Notebook(viz_frame)
        self.viz_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.lead_time_frame = ttk.Frame(self.viz_notebook)
        self.wip_frame = ttk.Frame(self.viz_notebook)
        self.viz_notebook.add(self.lead_time_frame, text="Lead Times")
        self.viz_notebook.add(self.wip_frame, text="WIP & Backlog")

    def _run_baseline(self) -> None:
        self.progress_label.config(text="Running baseline simulation...")
        self.root.update()

        try:
            self.config = SimulationConfig(
                num_periods=self.days_var.get(),
                avg_daily_demand=self.demand_var.get(),
                t1_rop_days=self.rop_var.get(),
                t1_order_up_to_days=self.order_up_to_var.get(),
            )
            self.results = run_baseline(self.config)
            self._update_results_display()
            self._update_visualizations()
            self.progress_label.config(text="Simulation complete!")
        except Exception as exc:
            messagebox.showerror("Error", f"Simulation failed: {exc}")
            self.progress_label.config(text="Simulation failed!")

    def _clear_results(self) -> None:
        self.results = None
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        for frame in [self.lead_time_frame, self.wip_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
        self.progress_label.config(text="Results cleared")

    def _update_results_display(self) -> None:
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        if not self.results:
            return

        metrics = [
            ("Mean Lead Time (days)", f"{self.results.mean_lead_time:.2f}"),
            ("Lead Time Std Dev", f"{self.results.lead_time_std:.2f}"),
            ("Worst Case Lead Time", f"{self.results.worst_case_lead_time:.2f}"),
            ("Mean WIP", f"{self.results.mean_wip:.2f}"),
            ("Mean Backlog", f"{self.results.mean_backlog:.2f}"),
            ("OTIF %", f"{self.results.otif_percentage:.2f}%"),
        ]
        for metric, value in metrics:
            self.results_tree.insert("", tk.END, values=(metric, value))

    def _update_visualizations(self) -> None:
        for frame in [self.lead_time_frame, self.wip_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        if not self.results:
            return

        fig = Figure(figsize=(10, 4))
        ax1 = fig.add_subplot(121)
        ax1.hist(self.results.lead_times, bins=25, color="#1f77b4", alpha=0.7)
        ax1.set_title("Lead Time Distribution")
        ax1.set_xlabel("Days")
        ax1.set_ylabel("Frequency")

        ax2 = fig.add_subplot(122)
        ax2.plot(self.results.wip_levels, label="WIP", color="#2ca02c")
        ax2.plot(self.results.backlog_levels, label="Backlog", color="#d62728")
        ax2.set_title("WIP and Backlog")
        ax2.set_xlabel("Day")
        ax2.set_ylabel("Units")
        ax2.legend()

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.lead_time_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        fig2 = Figure(figsize=(10, 4))
        ax3 = fig2.add_subplot(111)
        ax3.plot(self.results.wip_levels, label="WIP", color="#2ca02c")
        ax3.plot(self.results.backlog_levels, label="Backlog", color="#d62728")
        ax3.set_title("WIP and Backlog (Detailed)")
        ax3.set_xlabel("Day")
        ax3.set_ylabel("Units")
        ax3.legend()
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=self.wip_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def main() -> None:
    root = tk.Tk()
    app = SupplyChainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
