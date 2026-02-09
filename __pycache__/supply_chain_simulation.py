"""
Supply Chain Simulation Module
Three-tier automotive supply chain model with visibility scenarios
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict
from enum import Enum


class VisibilityScenario(Enum):
    """Supply chain visibility scenarios"""
    BASELINE = 1
    FORECAST_SHARING = 2
    INVENTORY_VISIBILITY = 3
    CAPACITY_VISIBILITY = 4
    FULL_VISIBILITY = 5


@dataclass
class SimulationConfig:
    """Configuration parameters for the simulation"""
    num_periods: int = 365  # Number of days to simulate
    base_demand_mean: float = 100.0  # Average daily demand from OEM
    base_demand_std: float = 20.0  # Demand variability
    
    # Lead times (in days)
    transport_t2_to_t1_base: float = 5.0
    transport_t1_to_oem_base: float = 3.0
    manufacturing_t2_base: float = 10.0
    manufacturing_t1_base: float = 7.0
    
    # Lead time variability
    transport_std: float = 1.5
    manufacturing_std: float = 2.0
    
    # Inventory parameters
    t2_initial_inventory: float = 1000.0
    t1_initial_inventory: float = 500.0
    t2_safety_stock: float = 500.0
    t1_safety_stock: float = 300.0
    
    # Capacity constraints
    t2_capacity: float = 200.0  # Max daily production
    t1_capacity: float = 150.0
    
    # Forecast parameters
    forecast_horizon: int = 14  # Days ahead
    forecast_accuracy: float = 0.85  # 85% accuracy
    
    # Order policy
    reorder_point_multiplier: float = 1.5  # Safety stock multiplier
    order_up_to_level: float = 2000.0


@dataclass
class SimulationResults:
    """Results from a simulation run"""
    scenario: VisibilityScenario
    mean_lead_time: float
    lead_time_std: float
    worst_case_lead_time: float  # 95th percentile
    mean_wip: float
    mean_backlog: float
    otif_percentage: float
    
    # Detailed time series data
    lead_times: List[float]
    wip_levels: List[float]
    backlog_levels: List[float]
    fill_rates: List[float]


class SupplyChainSimulation:
    """
    Three-tier supply chain simulation
    Tier 2/3 Aggregate -> Transport -> Tier 1 -> Transport -> OEM
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.reset()
    
    def reset(self):
        """Reset simulation state"""
        self.current_period = 0
        
        # Inventory levels
        self.t2_inventory = self.config.t2_initial_inventory
        self.t1_inventory = self.config.t1_initial_inventory
        
        # Work in progress
        self.t2_manufacturing_queue = []  # (completion_period, quantity)
        self.t1_manufacturing_queue = []
        self.t2_to_t1_transport_queue = []
        self.t1_to_oem_transport_queue = []
        
        # Orders and forecasts
        self.pending_t2_orders = []
        self.pending_t1_orders = []
        
        # Metrics tracking
        self.lead_times = []
        self.wip_levels = []
        self.backlog_levels = []
        self.order_timestamps = {}  # order_id -> placement_time
        self.deliveries = []  # (order_id, delivery_time, quantity, on_time)
        
        # Demand tracking
        self.oem_demands = []
        self.forecasts = []
    
    def run_simulation(self, scenario: VisibilityScenario) -> SimulationResults:
        """Run simulation for a specific visibility scenario"""
        self.reset()
        self.scenario = scenario
        
        # Generate demand series
        np.random.seed(42)  # For reproducibility
        demands = self._generate_demand_series()
        
        # Main simulation loop
        for period in range(self.config.num_periods):
            self.current_period = period
            current_demand = demands[period]
            
            # Generate forecast if applicable
            forecast = self._generate_forecast(demands, period) if self._has_forecast_sharing() else None
            
            # Process the supply chain from downstream to upstream
            self._process_oem_demand(current_demand, forecast)
            self._process_t1_to_oem_transport()
            self._process_t1_manufacturing()
            self._process_t2_to_t1_transport()
            self._process_t2_manufacturing()
            
            # Place orders based on scenario
            self._place_t1_order(forecast)
            self._place_t2_order(forecast)
            
            # Track metrics
            self._track_metrics()
        
        return self._calculate_results()
    
    def _generate_demand_series(self) -> np.ndarray:
        """Generate OEM demand time series with autocorrelation"""
        # Use AR(1) process for more realistic demand
        demands = np.zeros(self.config.num_periods)
        demands[0] = self.config.base_demand_mean
        
        rho = 0.7  # Autocorrelation coefficient
        for t in range(1, self.config.num_periods):
            innovation = np.random.normal(0, self.config.base_demand_std)
            demands[t] = (1 - rho) * self.config.base_demand_mean + rho * demands[t-1] + innovation
            demands[t] = max(0, demands[t])  # No negative demand
        
        return demands
    
    def _generate_forecast(self, demands: np.ndarray, current_period: int) -> float:
        """Generate demand forecast"""
        if current_period + self.config.forecast_horizon >= len(demands):
            return self.config.base_demand_mean
        
        # True future demand
        future_demand = np.mean(demands[current_period:current_period + self.config.forecast_horizon])
        
        # Add forecast error
        error = np.random.normal(0, (1 - self.config.forecast_accuracy) * future_demand)
        forecast = future_demand + error
        
        return max(0, forecast)
    
    def _has_forecast_sharing(self) -> bool:
        """Check if current scenario includes forecast sharing"""
        return self.scenario in [
            VisibilityScenario.FORECAST_SHARING,
            VisibilityScenario.FULL_VISIBILITY
        ]
    
    def _has_inventory_visibility(self) -> bool:
        """Check if current scenario includes inventory visibility"""
        return self.scenario in [
            VisibilityScenario.INVENTORY_VISIBILITY,
            VisibilityScenario.FULL_VISIBILITY
        ]
    
    def _has_capacity_visibility(self) -> bool:
        """Check if current scenario includes capacity visibility"""
        return self.scenario in [
            VisibilityScenario.CAPACITY_VISIBILITY,
            VisibilityScenario.FULL_VISIBILITY
        ]
    
    def _process_oem_demand(self, demand: float, forecast: float = None):
        """Process demand from OEM"""
        self.oem_demands.append(demand)
        if forecast is not None:
            self.forecasts.append(forecast)
        
        # Try to fulfill from T1 inventory
        fulfilled = min(demand, self.t1_inventory)
        self.t1_inventory -= fulfilled
        backlog = demand - fulfilled
        
        if backlog > 0:
            # Create backlog order
            order_id = f"OEM_{self.current_period}"
            self.order_timestamps[order_id] = self.current_period
            self.pending_t1_orders.append({
                'id': order_id,
                'quantity': backlog,
                'due_date': self.current_period,
                'original_period': self.current_period
            })
    
    def _process_t1_to_oem_transport(self):
        """Process shipments from T1 to OEM"""
        completed = [item for item in self.t1_to_oem_transport_queue 
                    if item['arrival_period'] <= self.current_period]
        
        for shipment in completed:
            # Deliver to OEM (adds to T1 effective inventory for fulfillment)
            # Track delivery metrics
            order_id = shipment.get('order_id')
            if order_id and order_id in self.order_timestamps:
                lead_time = self.current_period - self.order_timestamps[order_id]
                self.lead_times.append(lead_time)
                
                # Check on-time delivery
                on_time = self.current_period <= shipment.get('due_date', float('inf'))
                self.deliveries.append({
                    'order_id': order_id,
                    'delivery_time': self.current_period,
                    'quantity': shipment['quantity'],
                    'on_time': on_time
                })
        
        # Remove completed shipments
        self.t1_to_oem_transport_queue = [
            item for item in self.t1_to_oem_transport_queue 
            if item['arrival_period'] > self.current_period
        ]
    
    def _process_t1_manufacturing(self):
        """Process T1 manufacturing"""
        completed = [item for item in self.t1_manufacturing_queue 
                    if item['completion_period'] <= self.current_period]
        
        for job in completed:
            # Add to T1 inventory
            self.t1_inventory += job['quantity']
            
            # Ship to OEM if there are pending orders
            if self.pending_t1_orders:
                order = self.pending_t1_orders.pop(0)
                ship_quantity = min(job['quantity'], order['quantity'])
                
                # Create transport task
                transport_time = max(1, np.random.normal(
                    self.config.transport_t1_to_oem_base,
                    self.config.transport_std
                ))
                
                self.t1_to_oem_transport_queue.append({
                    'arrival_period': self.current_period + transport_time,
                    'quantity': ship_quantity,
                    'order_id': order['id'],
                    'due_date': order['due_date']
                })
                
                # If order partially fulfilled, keep remainder
                if order['quantity'] > ship_quantity:
                    order['quantity'] -= ship_quantity
                    self.pending_t1_orders.insert(0, order)
        
        # Remove completed jobs
        self.t1_manufacturing_queue = [
            item for item in self.t1_manufacturing_queue 
            if item['completion_period'] > self.current_period
        ]
    
    def _process_t2_to_t1_transport(self):
        """Process shipments from T2 to T1"""
        completed = [item for item in self.t2_to_t1_transport_queue 
                    if item['arrival_period'] <= self.current_period]
        
        for shipment in completed:
            # Add to T1 inventory (raw materials)
            # For simplicity, assume direct addition
            # In reality, this would trigger T1 manufacturing
            pass  # Handled implicitly in T1 ordering
        
        # Remove completed shipments
        self.t2_to_t1_transport_queue = [
            item for item in self.t2_to_t1_transport_queue 
            if item['arrival_period'] > self.current_period
        ]
    
    def _process_t2_manufacturing(self):
        """Process T2/T3 aggregate manufacturing"""
        completed = [item for item in self.t2_manufacturing_queue 
                    if item['completion_period'] <= self.current_period]
        
        for job in completed:
            # Add to T2 inventory
            self.t2_inventory += job['quantity']
        
        # Remove completed jobs
        self.t2_manufacturing_queue = [
            item for item in self.t2_manufacturing_queue 
            if item['completion_period'] > self.current_period
        ]
    
    def _place_t1_order(self, forecast: float = None):
        """T1 places order to T2"""
        # Calculate order quantity based on scenario
        
        # Baseline: Simple reorder point
        reorder_point = self.config.t1_safety_stock * self.config.reorder_point_multiplier
        
        if self._has_inventory_visibility():
            # Adjust based on system-wide inventory
            system_inventory = self.t1_inventory + self._calculate_pipeline_inventory_t1()
            net_inventory = system_inventory
        else:
            net_inventory = self.t1_inventory
        
        if net_inventory < reorder_point:
            # Calculate order quantity
            if forecast is not None and self._has_forecast_sharing():
                # Order based on forecast
                order_quantity = forecast * self.config.forecast_horizon - net_inventory
            else:
                # Order based on historical average
                order_quantity = self.config.base_demand_mean * 7 - net_inventory
            
            order_quantity = max(0, order_quantity)
            
            # Apply capacity constraints if visible
            if self._has_capacity_visibility():
                # Check T2 capacity and adjust
                current_t2_load = self._calculate_t2_load()
                available_capacity = self.config.t2_capacity * 10 - current_t2_load  # 10 days window
                order_quantity = min(order_quantity, available_capacity)
            
            if order_quantity > 0:
                # T2 ships from inventory or manufactures
                ship_quantity = min(order_quantity, self.t2_inventory)
                
                if ship_quantity > 0:
                    self.t2_inventory -= ship_quantity
                    
                    # Create transport task
                    transport_time = max(1, np.random.normal(
                        self.config.transport_t2_to_t1_base,
                        self.config.transport_std
                    ))
                    
                    self.t2_to_t1_transport_queue.append({
                        'arrival_period': self.current_period + transport_time,
                        'quantity': ship_quantity
                    })
                
                # Manufacture remainder
                manufacture_quantity = order_quantity - ship_quantity
                if manufacture_quantity > 0:
                    self._start_t1_manufacturing(manufacture_quantity)
    
    def _place_t2_order(self, forecast: float = None):
        """T2 produces based on demand/forecast"""
        # Check if T2 needs to manufacture
        reorder_point = self.config.t2_safety_stock * self.config.reorder_point_multiplier
        
        if self.t2_inventory < reorder_point:
            # Calculate production quantity
            if forecast is not None and self._has_forecast_sharing():
                production_quantity = forecast * self.config.forecast_horizon
            else:
                production_quantity = self.config.base_demand_mean * 14
            
            production_quantity = min(production_quantity, self.config.t2_capacity * 10)
            
            # Start manufacturing
            if production_quantity > 0:
                self._start_t2_manufacturing(production_quantity)
    
    def _start_t1_manufacturing(self, quantity: float):
        """Start manufacturing at T1"""
        # Apply capacity constraints
        actual_quantity = min(quantity, self.config.t1_capacity * 2)
        
        manufacturing_time = max(1, np.random.normal(
            self.config.manufacturing_t1_base,
            self.config.manufacturing_std
        ))
        
        self.t1_manufacturing_queue.append({
            'completion_period': self.current_period + manufacturing_time,
            'quantity': actual_quantity
        })
    
    def _start_t2_manufacturing(self, quantity: float):
        """Start manufacturing at T2"""
        # Apply capacity constraints
        actual_quantity = min(quantity, self.config.t2_capacity * 2)
        
        manufacturing_time = max(1, np.random.normal(
            self.config.manufacturing_t2_base,
            self.config.manufacturing_std
        ))
        
        self.t2_manufacturing_queue.append({
            'completion_period': self.current_period + manufacturing_time,
            'quantity': actual_quantity
        })
    
    def _calculate_pipeline_inventory_t1(self) -> float:
        """Calculate inventory in transit/production for T1"""
        pipeline = 0.0
        
        # Manufacturing WIP
        for job in self.t1_manufacturing_queue:
            pipeline += job['quantity']
        
        # In transit from T2
        for shipment in self.t2_to_t1_transport_queue:
            pipeline += shipment['quantity']
        
        return pipeline
    
    def _calculate_t2_load(self) -> float:
        """Calculate current production load at T2"""
        load = 0.0
        for job in self.t2_manufacturing_queue:
            load += job['quantity']
        return load
    
    def _track_metrics(self):
        """Track WIP and backlog at current period"""
        # Calculate total WIP
        wip = 0.0
        for job in self.t1_manufacturing_queue:
            wip += job['quantity']
        for job in self.t2_manufacturing_queue:
            wip += job['quantity']
        for shipment in self.t1_to_oem_transport_queue:
            wip += shipment['quantity']
        for shipment in self.t2_to_t1_transport_queue:
            wip += shipment['quantity']
        
        self.wip_levels.append(wip)
        
        # Calculate backlog
        backlog = sum(order['quantity'] for order in self.pending_t1_orders)
        self.backlog_levels.append(backlog)
    
    def _calculate_results(self) -> SimulationResults:
        """Calculate final simulation results"""
        # Lead time statistics
        if self.lead_times:
            mean_lead_time = np.mean(self.lead_times)
            lead_time_std = np.std(self.lead_times)
            worst_case = np.percentile(self.lead_times, 95)
        else:
            mean_lead_time = 0.0
            lead_time_std = 0.0
            worst_case = 0.0
        
        # WIP statistics
        mean_wip = np.mean(self.wip_levels) if self.wip_levels else 0.0
        
        # Backlog statistics
        mean_backlog = np.mean(self.backlog_levels) if self.backlog_levels else 0.0
        
        # OTIF calculation
        if self.deliveries:
            on_time_count = sum(1 for d in self.deliveries if d['on_time'])
            otif = (on_time_count / len(self.deliveries)) * 100
        else:
            otif = 0.0
        
        return SimulationResults(
            scenario=self.scenario,
            mean_lead_time=mean_lead_time,
            lead_time_std=lead_time_std,
            worst_case_lead_time=worst_case,
            mean_wip=mean_wip,
            mean_backlog=mean_backlog,
            otif_percentage=otif,
            lead_times=self.lead_times,
            wip_levels=self.wip_levels,
            backlog_levels=self.backlog_levels,
            fill_rates=[]  # Placeholder
        )


def run_all_scenarios(config: SimulationConfig = None) -> Dict[VisibilityScenario, SimulationResults]:
    """Run simulation for all scenarios and return results"""
    if config is None:
        config = SimulationConfig()
    
    results = {}
    
    for scenario in VisibilityScenario:
        sim = SupplyChainSimulation(config)
        result = sim.run_simulation(scenario)
        results[scenario] = result
    
    return results
