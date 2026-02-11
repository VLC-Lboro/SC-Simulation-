"""Forecast sharing GUI for side-by-side scenario comparison."""

import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from supply_chain_simulation import ForecastSharingConfig, SimulationConfig, compare_scenarios


class ForecastSharingGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Forecast Sharing Supply Chain Simulation")
        self.root.geometry("1300x850")

        self.config = SimulationConfig()
        self.comparison = None

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        self._build_controls(main)
        self._build_results(main)

    def _build_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Forecast Sharing Parameters", padding="10")
        controls.grid(row=0, column=0, rowspan=2, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))

        self.days_var = tk.IntVar(value=self.config.num_periods)
        self.horizon_var = tk.IntVar(value=self.config.forecast_sharing.forecast_horizon)
        self.update_freq_var = tk.IntVar(value=self.config.forecast_sharing.forecast_update_frequency)
        self.error_std_var = tk.DoubleVar(value=self.config.forecast_sharing.forecast_error_std)
        self.weight_var = tk.DoubleVar(value=self.config.forecast_sharing.t1_forecast_weight)
        self.accuracy_var = tk.StringVar(value=self.config.forecast_sharing.forecast_accuracy_model)

        row = 0
        ttk.Label(controls, text="Simulation Days").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.days_var, width=10).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Label(controls, text="Forecast Horizon").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.horizon_var, width=10).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Label(controls, text="Update Frequency").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.update_freq_var, width=10).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Label(controls, text="Accuracy Model").grid(row=row, column=0, sticky=tk.W)
        ttk.Combobox(
            controls,
            textvariable=self.accuracy_var,
            values=["perfect", "noise"],
            state="readonly",
            width=8,
        ).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Label(controls, text="Forecast Error Std").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.error_std_var, width=10).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Label(controls, text="T1 Forecast Weight").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.weight_var, width=10).grid(row=row, column=1, pady=2)
        row += 1

        ttk.Button(controls, text="Run Comparison", command=self._run).grid(
            row=row,
            column=0,
            columnspan=2,
            pady=(10, 4),
            sticky=(tk.W, tk.E),
        )

        self.status = ttk.Label(controls, text="", foreground="blue")
        self.status.grid(row=row + 1, column=0, columnspan=2, sticky=tk.W)

    def _build_results(self, parent: ttk.Frame) -> None:
        table_frame = ttk.LabelFrame(parent, text="Scenario KPI Comparison", padding="10")
        table_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)

        self.results = ttk.Treeview(
            table_frame,
            columns=("metric", "baseline", "forecast", "delta"),
            show="headings",
            height=10,
        )
        self.results.heading("metric", text="Metric")
        self.results.heading("baseline", text="Baseline")
        self.results.heading("forecast", text="Forecast Sharing")
        self.results.heading("delta", text="Delta (FS - BL)")
        self.results.column("metric", width=240)
        self.results.column("baseline", width=140)
        self.results.column("forecast", width=160)
        self.results.column("delta", width=140)
        self.results.grid(row=0, column=0, sticky=(tk.W, tk.E))

        viz_frame = ttk.LabelFrame(parent, text="Visualizations", padding="10")
        viz_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(1, weight=1)
        viz_frame.rowconfigure(0, weight=1)
        viz_frame.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(viz_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.lead_time_tab = ttk.Frame(self.notebook)
        self.wip_backlog_tab = ttk.Frame(self.notebook)
        self.kpi_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.lead_time_tab, text="Lead Time")
        self.notebook.add(self.wip_backlog_tab, text="WIP & Backlog")
        self.notebook.add(self.kpi_tab, text="OTIF / Fill / Bullwhip")

    def _run(self) -> None:
        self.status.config(text="Running baseline + forecast-sharing scenarios...")
        self.root.update()
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
            self.comparison = compare_scenarios(config)
            self._render_table()
            self._render_plots()
            self.status.config(text="Comparison complete")
        except Exception as exc:
            messagebox.showerror("Simulation Error", str(exc))
            self.status.config(text="Simulation failed")

    def _render_table(self) -> None:
        for row in self.results.get_children():
            self.results.delete(row)

        baseline = self.comparison.baseline
        forecast = self.comparison.forecast_sharing

        rows = [
            ("Mean Lead Time (days)", baseline.mean_lead_time, forecast.mean_lead_time),
            ("Lead Time Std Dev", baseline.lead_time_std, forecast.lead_time_std),
            ("Worst Case Lead Time", baseline.worst_case_lead_time, forecast.worst_case_lead_time),
            ("Mean WIP", baseline.mean_wip, forecast.mean_wip),
            ("Mean Backlog", baseline.mean_backlog, forecast.mean_backlog),
            ("OTIF %", baseline.otif_percentage, forecast.otif_percentage),
            ("Fill Rate", baseline.fill_rate * 100, forecast.fill_rate * 100),
            ("Bullwhip Effect", baseline.bullwhip_effect, forecast.bullwhip_effect),
            (
                "Average Inventory Level",
                baseline.average_inventory_level,
                forecast.average_inventory_level,
            ),
        ]

        for metric, bl, fs in rows:
            delta = fs - bl
            self.results.insert(
                "",
                tk.END,
                values=(metric, f"{bl:.3f}", f"{fs:.3f}", f"{delta:+.3f}"),
            )

    def _render_plots(self) -> None:
        for tab in [self.lead_time_tab, self.wip_backlog_tab, self.kpi_tab]:
            for widget in tab.winfo_children():
                widget.destroy()

        baseline = self.comparison.baseline
        forecast = self.comparison.forecast_sharing

        fig1 = Figure(figsize=(10, 4))
        ax1 = fig1.add_subplot(111)
        if baseline.lead_times:
            ax1.hist(baseline.lead_times, bins=20, alpha=0.5, label="Baseline")
        if forecast.lead_times:
            ax1.hist(forecast.lead_times, bins=20, alpha=0.5, label="Forecast Sharing")
        ax1.set_title("Lead Time Distribution")
        ax1.set_xlabel("Days")
        ax1.set_ylabel("Frequency")
        ax1.legend()
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=self.lead_time_tab)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        fig2 = Figure(figsize=(10, 4))
        ax2 = fig2.add_subplot(121)
        ax2.plot(baseline.wip_levels, label="Baseline WIP", color="#1f77b4")
        ax2.plot(forecast.wip_levels, label="Forecast WIP", color="#ff7f0e")
        ax2.set_title("WIP")
        ax2.set_xlabel("Day")
        ax2.set_ylabel("Units")
        ax2.legend()

        ax3 = fig2.add_subplot(122)
        ax3.plot(baseline.backlog_levels, label="Baseline Backlog", color="#2ca02c")
        ax3.plot(forecast.backlog_levels, label="Forecast Backlog", color="#d62728")
        ax3.set_title("Backlog")
        ax3.set_xlabel("Day")
        ax3.set_ylabel("Units")
        ax3.legend()

        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=self.wip_backlog_tab)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        fig3 = Figure(figsize=(10, 4))
        ax4 = fig3.add_subplot(111)
        names = ["OTIF %", "Fill Rate %", "Bullwhip"]
        bl_vals = [baseline.otif_percentage, baseline.fill_rate * 100, baseline.bullwhip_effect]
        fs_vals = [forecast.otif_percentage, forecast.fill_rate * 100, forecast.bullwhip_effect]
        x = range(len(names))
        width = 0.35
        ax4.bar([i - width / 2 for i in x], bl_vals, width=width, label="Baseline")
        ax4.bar([i + width / 2 for i in x], fs_vals, width=width, label="Forecast Sharing")
        ax4.set_xticks(list(x))
        ax4.set_xticklabels(names)
        ax4.set_title("Service and Variability KPIs")
        ax4.legend()
        fig3.tight_layout()
        canvas3 = FigureCanvasTkAgg(fig3, master=self.kpi_tab)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def main() -> None:
    root = tk.Tk()
    ForecastSharingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
