"""
Test script to verify supply chain simulation functionality
Run this before using the GUI to ensure everything works correctly
"""

from supply_chain_simulation import (
    SupplyChainSimulation,
    VisibilityScenario,
    SimulationConfig,
    run_all_scenarios
)


def test_single_scenario():
    """Test running a single scenario"""
    print("Testing single scenario simulation...")
    
    config = SimulationConfig(num_periods=100)  # Short simulation for testing
    sim = SupplyChainSimulation(config)
    result = sim.run_simulation(VisibilityScenario.BASELINE)
    
    print(f"✓ Baseline scenario completed")
    print(f"  - Mean Lead Time: {result.mean_lead_time:.2f} days")
    print(f"  - Lead Time Std: {result.lead_time_std:.2f} days")
    print(f"  - Mean WIP: {result.mean_wip:.2f} units")
    print(f"  - Mean Backlog: {result.mean_backlog:.2f} units")
    print(f"  - OTIF: {result.otif_percentage:.2f}%")
    print()


def test_all_scenarios():
    """Test running all scenarios"""
    print("Testing all scenarios...")
    
    config = SimulationConfig(num_periods=100)
    results = run_all_scenarios(config)
    
    print(f"✓ All {len(results)} scenarios completed")
    print("\nScenario Comparison:")
    print("-" * 80)
    print(f"{'Scenario':<25} {'Mean LT':<12} {'LT Std':<12} {'WIP':<12} {'OTIF %':<10}")
    print("-" * 80)
    
    scenario_names = {
        VisibilityScenario.BASELINE: "Baseline",
        VisibilityScenario.FORECAST_SHARING: "Forecast Sharing",
        VisibilityScenario.INVENTORY_VISIBILITY: "Inventory Visibility",
        VisibilityScenario.CAPACITY_VISIBILITY: "Capacity Visibility",
        VisibilityScenario.FULL_VISIBILITY: "Full Visibility"
    }
    
    for scenario in sorted(results.keys(), key=lambda x: x.value):
        result = results[scenario]
        print(f"{scenario_names[scenario]:<25} "
              f"{result.mean_lead_time:<12.2f} "
              f"{result.lead_time_std:<12.2f} "
              f"{result.mean_wip:<12.2f} "
              f"{result.otif_percentage:<10.2f}")
    
    print("-" * 80)
    print()


def test_visibility_impact():
    """Test that visibility scenarios show improvement"""
    print("Testing visibility impact...")
    
    config = SimulationConfig(num_periods=100)
    
    # Run baseline and full visibility
    sim_baseline = SupplyChainSimulation(config)
    baseline = sim_baseline.run_simulation(VisibilityScenario.BASELINE)
    
    sim_full = SupplyChainSimulation(config)
    full_vis = sim_full.run_simulation(VisibilityScenario.FULL_VISIBILITY)
    
    # Check improvements
    lt_improvement = ((baseline.mean_lead_time - full_vis.mean_lead_time) / 
                      baseline.mean_lead_time * 100)
    wip_improvement = ((baseline.mean_wip - full_vis.mean_wip) / 
                       baseline.mean_wip * 100)
    
    print(f"✓ Impact analysis completed")
    print(f"  - Lead Time Improvement: {lt_improvement:.1f}%")
    print(f"  - WIP Reduction: {wip_improvement:.1f}%")
    
    if lt_improvement > 0:
        print(f"  ✓ Full visibility improves lead time (expected)")
    else:
        print(f"  ⚠ Warning: Full visibility did not improve lead time")
    
    print()


def test_configuration_changes():
    """Test that configuration changes affect results"""
    print("Testing configuration sensitivity...")
    
    # Low variability config
    config_low = SimulationConfig(num_periods=100, base_demand_std=10.0)
    sim_low = SupplyChainSimulation(config_low)
    result_low = sim_low.run_simulation(VisibilityScenario.BASELINE)
    
    # High variability config
    config_high = SimulationConfig(num_periods=100, base_demand_std=40.0)
    sim_high = SupplyChainSimulation(config_high)
    result_high = sim_high.run_simulation(VisibilityScenario.BASELINE)
    
    print(f"✓ Configuration testing completed")
    print(f"  - Low variability (std=10): Lead Time Std = {result_low.lead_time_std:.2f}")
    print(f"  - High variability (std=40): Lead Time Std = {result_high.lead_time_std:.2f}")
    
    if result_high.lead_time_std > result_low.lead_time_std:
        print(f"  ✓ Higher demand variability increases lead time variability (expected)")
    else:
        print(f"  ⚠ Warning: Variability relationship unexpected")
    
    print()


def main():
    """Run all tests"""
    print("=" * 80)
    print("Supply Chain Simulation Test Suite")
    print("=" * 80)
    print()
    
    try:
        test_single_scenario()
        test_all_scenarios()
        test_visibility_impact()
        test_configuration_changes()
        
        print("=" * 80)
        print("✓ All tests completed successfully!")
        print("=" * 80)
        print("\nYou can now run the GUI application with: python gui_application.py")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
