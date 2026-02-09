"""
Test script to verify baseline supply chain simulation functionality.
"""

from supply_chain_simulation import SimulationConfig, run_baseline


def test_baseline_run() -> None:
    """Test running the baseline scenario."""
    print("Testing baseline simulation...")

    config = SimulationConfig(num_periods=60, seed=42)
    result = run_baseline(config)

    print("✓ Baseline scenario completed")
    print(f"  - Mean Lead Time: {result.mean_lead_time:.2f} days")
    print(f"  - Lead Time Std: {result.lead_time_std:.2f} days")
    print(f"  - Mean WIP: {result.mean_wip:.2f} units")
    print(f"  - Mean Backlog: {result.mean_backlog:.2f} units")
    print(f"  - OTIF: {result.otif_percentage:.2f}%")

    assert result.mean_lead_time >= 0
    assert result.mean_wip >= 0
    assert 0 <= result.otif_percentage <= 100


def main() -> None:
    print("=" * 80)
    print("Baseline Supply Chain Simulation Test Suite")
    print("=" * 80)
    print()

    try:
        test_baseline_run()
        print()
        print("=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)
        print("\nYou can run the GUI application with: python gui_application.py")
    except Exception as exc:
        print(f"\n✗ Test failed with error: {exc}")
        raise


if __name__ == "__main__":
    main()
