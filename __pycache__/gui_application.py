"""
Supply Chain Simulation GUI Application
Interactive interface for running and comparing visibility scenarios
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from supply_chain_simulation import (
    SupplyChainSimulation,
    VisibilityScenario,
    SimulationConfig,
    SimulationResults,
    run_all_scenarios
)
from typing import Dict, Optional


class SupplyChainGUI:
    """Main GUI application for supply chain simulation"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Automotive Supply Chain Visibility Impact Analysis")
        self.root.geometry("1400x900")
        
        # Simulation state
        self.config = SimulationConfig()
        self.results: Dict[VisibilityScenario, SimulationResults] = {}
        self.selected_scenarios = set()
        
        # Create UI
        self._create_widgets()
        
    def _create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Left panel - Controls
        self._create_control_panel(main_container)
        
        # Right panel - Results
        self._create_results_panel(main_container)
        
    def _create_control_panel(self, parent):
        """Create the control panel for scenario selection"""
        control_frame = ttk.LabelFrame(parent, text="Scenario Selection", padding="10")
        control_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Title
        title = ttk.Label(control_frame, text="Supply Chain Visibility Scenarios", 
                         font=('Helvetica', 14, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Scenario descriptions
        scenarios_info = [
            ("Baseline", "Orders only, no forecasts, no upstream visibility"),
            ("Forecast Sharing", "Forecasts shared between OEM → Tier 1 → Tier 2/3"),
            ("Inventory Visibility", "Order quantity adjusts to net system inventory"),
            ("Capacity Visibility", "Tier 2/3 shares capacity constraints"),
            ("Full Visibility", "Combines Forecast + Inventory + Capacity (upper bound)")
        ]
        
        self.scenario_vars = {}
        row = 1
        
        for i, (name, desc) in enumerate(scenarios_info):
            scenario = VisibilityScenario(i + 1)
            
            # Checkbutton
            var = tk.BooleanVar()
            self.scenario_vars[scenario] = var
            
            cb = ttk.Checkbutton(control_frame, text=name, variable=var,
                                command=self._on_scenario_toggle)
            cb.grid(row=row, column=0, sticky=tk.W, pady=5)
            
            # Description
            desc_label = ttk.Label(control_frame, text=desc, 
                                  font=('Helvetica', 9), foreground='gray')
            desc_label.grid(row=row+1, column=0, sticky=tk.W, padx=(20, 0))
            
            row += 2
        
        # Separator
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Configuration section
        config_label = ttk.Label(control_frame, text="Simulation Parameters", 
                                font=('Helvetica', 12, 'bold'))
        config_label.grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1
        
        # Simulation duration
        ttk.Label(control_frame, text="Simulation Days:").grid(row=row, column=0, sticky=tk.W)
        self.days_var = tk.IntVar(value=365)
        days_entry = ttk.Entry(control_frame, textvariable=self.days_var, width=10)
        days_entry.grid(row=row, column=1, sticky=tk.W, padx=(10, 0))
        row += 1
        
        # Base demand
        ttk.Label(control_frame, text="Base Demand (mean):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.demand_var = tk.DoubleVar(value=100.0)
        demand_entry = ttk.Entry(control_frame, textvariable=self.demand_var, width=10)
        demand_entry.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        row += 1
        
        # Demand variability
        ttk.Label(control_frame, text="Demand Std Dev:").grid(row=row, column=0, sticky=tk.W)
        self.demand_std_var = tk.DoubleVar(value=20.0)
        demand_std_entry = ttk.Entry(control_frame, textvariable=self.demand_std_var, width=10)
        demand_std_entry.grid(row=row, column=1, sticky=tk.W, padx=(10, 0))
        row += 1
        
        # Separator
        ttk.Separator(control_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="Run Simulation", 
                                     command=self._run_simulation)
        self.run_button.grid(row=0, column=0, padx=5)
        
        self.compare_button = ttk.Button(button_frame, text="Compare All Scenarios", 
                                        command=self._run_all_scenarios)
        self.compare_button.grid(row=0, column=1, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear Results", 
                                 command=self._clear_results)
        clear_button.grid(row=0, column=2, padx=5)
        row += 1
        
        # Progress indicator
        self.progress_label = ttk.Label(control_frame, text="", foreground='blue')
        self.progress_label.grid(row=row, column=0, columnspan=2, pady=5)
        
    def _create_results_panel(self, parent):
        """Create the results display panel"""
        results_frame = ttk.Frame(parent)
        results_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        # Results table
        table_frame = ttk.LabelFrame(results_frame, text="Simulation Results", padding="10")
        table_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Create treeview for results
        columns = ('Scenario', 'Mean Lead Time', 'Lead Time Std', 'Worst Case (95%)', 
                  'Mean WIP', 'Mean Backlog', 'OTIF %')
        
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        
        # Define headings
        for col in columns:
            self.results_tree.heading(col, text=col)
            if col == 'Scenario':
                self.results_tree.column(col, width=150)
            else:
                self.results_tree.column(col, width=110)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Visualization area
        viz_frame = ttk.LabelFrame(results_frame, text="Visualizations", padding="10")
        viz_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        viz_frame.columnconfigure(0, weight=1)
        viz_frame.rowconfigure(0, weight=1)
        
        # Create notebook for different visualizations
        self.viz_notebook = ttk.Notebook(viz_frame)
        self.viz_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create placeholder tabs
        self._create_visualization_tabs()
        
    def _create_visualization_tabs(self):
        """Create tabs for different visualizations"""
        # Tab 1: Lead Time Comparison
        self.lead_time_frame = ttk.Frame(self.viz_notebook)
        self.viz_notebook.add(self.lead_time_frame, text="Lead Time Analysis")
        
        # Tab 2: WIP & Backlog
        self.wip_frame = ttk.Frame(self.viz_notebook)
        self.viz_notebook.add(self.wip_frame, text="WIP & Backlog")
        
        # Tab 3: Summary Comparison
        self.summary_frame = ttk.Frame(self.viz_notebook)
        self.viz_notebook.add(self.summary_frame, text="Summary Metrics")
        
    def _on_scenario_toggle(self):
        """Handle scenario checkbox toggle"""
        self.selected_scenarios = {
            scenario for scenario, var in self.scenario_vars.items() 
            if var.get()
        }
        
    def _run_simulation(self):
        """Run simulation for selected scenarios"""
        if not self.selected_scenarios:
            messagebox.showwarning("No Selection", "Please select at least one scenario to run.")
            return
        
        self.progress_label.config(text="Running simulation...")
        self.root.update()
        
        try:
            # Update configuration
            self.config.num_periods = self.days_var.get()
            self.config.base_demand_mean = self.demand_var.get()
            self.config.base_demand_std = self.demand_std_var.get()
            
            # Run simulations
            for scenario in self.selected_scenarios:
                sim = SupplyChainSimulation(self.config)
                result = sim.run_simulation(scenario)
                self.results[scenario] = result
            
            # Update display
            self._update_results_display()
            self._update_visualizations()
            
            self.progress_label.config(text="Simulation complete!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed: {str(e)}")
            self.progress_label.config(text="Simulation failed!")
        
    def _run_all_scenarios(self):
        """Run simulation for all scenarios"""
        self.progress_label.config(text="Running all scenarios...")
        self.root.update()
        
        try:
            # Update configuration
            self.config.num_periods = self.days_var.get()
            self.config.base_demand_mean = self.demand_var.get()
            self.config.base_demand_std = self.demand_std_var.get()
            
            # Run all scenarios
            self.results = run_all_scenarios(self.config)
            
            # Check all scenario checkboxes
            for var in self.scenario_vars.values():
                var.set(True)
            self._on_scenario_toggle()
            
            # Update display
            self._update_results_display()
            self._update_visualizations()
            
            self.progress_label.config(text="All scenarios complete!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed: {str(e)}")
            self.progress_label.config(text="Simulation failed!")
    
    def _clear_results(self):
        """Clear all results"""
        self.results.clear()
        self.selected_scenarios.clear()
        
        # Uncheck all scenarios
        for var in self.scenario_vars.values():
            var.set(False)
        
        # Clear table
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Clear visualizations
        self._clear_visualizations()
        
        self.progress_label.config(text="Results cleared")
    
    def _update_results_display(self):
        """Update the results table"""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Scenario name mapping
        scenario_names = {
            VisibilityScenario.BASELINE: "Baseline",
            VisibilityScenario.FORECAST_SHARING: "Forecast Sharing",
            VisibilityScenario.INVENTORY_VISIBILITY: "Inventory Visibility",
            VisibilityScenario.CAPACITY_VISIBILITY: "Capacity Visibility",
            VisibilityScenario.FULL_VISIBILITY: "Full Visibility"
        }
        
        # Add results
        for scenario, result in sorted(self.results.items(), key=lambda x: x[0].value):
            values = (
                scenario_names[scenario],
                f"{result.mean_lead_time:.2f}",
                f"{result.lead_time_std:.2f}",
                f"{result.worst_case_lead_time:.2f}",
                f"{result.mean_wip:.2f}",
                f"{result.mean_backlog:.2f}",
                f"{result.otif_percentage:.2f}%"
            )
            self.results_tree.insert('', tk.END, values=values)
    
    def _update_visualizations(self):
        """Update all visualization tabs"""
        if not self.results:
            return
        
        self._clear_visualizations()
        self._plot_lead_time_analysis()
        self._plot_wip_backlog()
        self._plot_summary_metrics()
    
    def _clear_visualizations(self):
        """Clear all visualization canvases"""
        for frame in [self.lead_time_frame, self.wip_frame, self.summary_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
    
    def _plot_lead_time_analysis(self):
        """Plot lead time distribution and comparison"""
        fig = Figure(figsize=(12, 5))
        
        # Scenario colors
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        scenario_names = {
            VisibilityScenario.BASELINE: "Baseline",
            VisibilityScenario.FORECAST_SHARING: "Forecast Sharing",
            VisibilityScenario.INVENTORY_VISIBILITY: "Inventory Visibility",
            VisibilityScenario.CAPACITY_VISIBILITY: "Capacity Visibility",
            VisibilityScenario.FULL_VISIBILITY: "Full Visibility"
        }
        
        # Plot 1: Lead time distributions
        ax1 = fig.add_subplot(121)
        for i, (scenario, result) in enumerate(sorted(self.results.items(), key=lambda x: x[0].value)):
            if result.lead_times:
                ax1.hist(result.lead_times, bins=30, alpha=0.5, 
                        label=scenario_names[scenario], color=colors[i])
        
        ax1.set_xlabel('Lead Time (days)', fontsize=10)
        ax1.set_ylabel('Frequency', fontsize=10)
        ax1.set_title('Lead Time Distributions', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Box plot comparison
        ax2 = fig.add_subplot(122)
        data_to_plot = []
        labels = []
        
        for scenario, result in sorted(self.results.items(), key=lambda x: x[0].value):
            if result.lead_times:
                data_to_plot.append(result.lead_times)
                labels.append(scenario_names[scenario])
        
        if data_to_plot:
            bp = ax2.boxplot(data_to_plot, labels=labels, patch_artist=True)
            
            # Color the boxes
            for patch, color in zip(bp['boxes'], colors[:len(data_to_plot)]):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
        
        ax2.set_ylabel('Lead Time (days)', fontsize=10)
        ax2.set_title('Lead Time Variability', fontsize=12, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3, axis='y')
        
        fig.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.lead_time_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _plot_wip_backlog(self):
        """Plot WIP and backlog time series"""
        fig = Figure(figsize=(12, 5))
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        scenario_names = {
            VisibilityScenario.BASELINE: "Baseline",
            VisibilityScenario.FORECAST_SHARING: "Forecast Sharing",
            VisibilityScenario.INVENTORY_VISIBILITY: "Inventory Visibility",
            VisibilityScenario.CAPACITY_VISIBILITY: "Capacity Visibility",
            VisibilityScenario.FULL_VISIBILITY: "Full Visibility"
        }
        
        # Plot 1: WIP over time
        ax1 = fig.add_subplot(121)
        for i, (scenario, result) in enumerate(sorted(self.results.items(), key=lambda x: x[0].value)):
            if result.wip_levels:
                # Plot moving average for clarity
                window = 7
                wip_ma = np.convolve(result.wip_levels, np.ones(window)/window, mode='valid')
                ax1.plot(wip_ma, label=scenario_names[scenario], 
                        color=colors[i], linewidth=1.5, alpha=0.8)
        
        ax1.set_xlabel('Time (days)', fontsize=10)
        ax1.set_ylabel('Work in Progress (units)', fontsize=10)
        ax1.set_title('WIP Over Time (7-day MA)', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Backlog over time
        ax2 = fig.add_subplot(122)
        for i, (scenario, result) in enumerate(sorted(self.results.items(), key=lambda x: x[0].value)):
            if result.backlog_levels:
                # Plot moving average
                window = 7
                backlog_ma = np.convolve(result.backlog_levels, np.ones(window)/window, mode='valid')
                ax2.plot(backlog_ma, label=scenario_names[scenario], 
                        color=colors[i], linewidth=1.5, alpha=0.8)
        
        ax2.set_xlabel('Time (days)', fontsize=10)
        ax2.set_ylabel('Backlog (units)', fontsize=10)
        ax2.set_title('Backlog Over Time (7-day MA)', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        fig.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.wip_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _plot_summary_metrics(self):
        """Plot summary comparison of all metrics"""
        fig = Figure(figsize=(12, 6))
        
        scenario_names = {
            VisibilityScenario.BASELINE: "Baseline",
            VisibilityScenario.FORECAST_SHARING: "Forecast",
            VisibilityScenario.INVENTORY_VISIBILITY: "Inventory",
            VisibilityScenario.CAPACITY_VISIBILITY: "Capacity",
            VisibilityScenario.FULL_VISIBILITY: "Full"
        }
        
        # Prepare data
        scenarios = sorted(self.results.keys(), key=lambda x: x.value)
        labels = [scenario_names[s] for s in scenarios]
        
        mean_lt = [self.results[s].mean_lead_time for s in scenarios]
        std_lt = [self.results[s].lead_time_std for s in scenarios]
        mean_wip = [self.results[s].mean_wip for s in scenarios]
        mean_backlog = [self.results[s].mean_backlog for s in scenarios]
        otif = [self.results[s].otif_percentage for s in scenarios]
        
        # Plot 1: Lead time metrics
        ax1 = fig.add_subplot(231)
        x = np.arange(len(labels))
        ax1.bar(x, mean_lt, color='steelblue', alpha=0.7)
        ax1.set_ylabel('Days', fontsize=9)
        ax1.set_title('Mean Lead Time', fontsize=10, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Plot 2: Lead time variability
        ax2 = fig.add_subplot(232)
        ax2.bar(x, std_lt, color='coral', alpha=0.7)
        ax2.set_ylabel('Days', fontsize=9)
        ax2.set_title('Lead Time Std Dev', fontsize=10, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Plot 3: WIP
        ax3 = fig.add_subplot(233)
        ax3.bar(x, mean_wip, color='mediumseagreen', alpha=0.7)
        ax3.set_ylabel('Units', fontsize=9)
        ax3.set_title('Mean WIP', fontsize=10, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Plot 4: Backlog
        ax4 = fig.add_subplot(234)
        ax4.bar(x, mean_backlog, color='indianred', alpha=0.7)
        ax4.set_ylabel('Units', fontsize=9)
        ax4.set_title('Mean Backlog', fontsize=10, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax4.grid(True, alpha=0.3, axis='y')
        
        # Plot 5: OTIF
        ax5 = fig.add_subplot(235)
        ax5.bar(x, otif, color='mediumpurple', alpha=0.7)
        ax5.set_ylabel('Percentage', fontsize=9)
        ax5.set_title('OTIF %', fontsize=10, fontweight='bold')
        ax5.set_xticks(x)
        ax5.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax5.set_ylim([0, 100])
        ax5.grid(True, alpha=0.3, axis='y')
        
        # Plot 6: Improvement vs Baseline
        if VisibilityScenario.BASELINE in self.results:
            ax6 = fig.add_subplot(236)
            baseline_lt = self.results[VisibilityScenario.BASELINE].mean_lead_time
            improvements = [(baseline_lt - lt) / baseline_lt * 100 for lt in mean_lt]
            
            colors_imp = ['green' if imp > 0 else 'red' for imp in improvements]
            ax6.bar(x, improvements, color=colors_imp, alpha=0.7)
            ax6.set_ylabel('Improvement %', fontsize=9)
            ax6.set_title('Lead Time Improvement vs Baseline', fontsize=10, fontweight='bold')
            ax6.set_xticks(x)
            ax6.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
            ax6.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax6.grid(True, alpha=0.3, axis='y')
        
        fig.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.summary_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = SupplyChainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
