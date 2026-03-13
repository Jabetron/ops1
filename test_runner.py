import subprocess
import json
import os
import csv
from datetime import datetime

# Configuration
UE_EDITOR_PATH = r"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe"
PROJECT_PATH = r"C:\Users\rodri\Documents\Unreal Projects\ops1\ops1.uproject"
SCENARIOS_PATH = r"C:\Users\rodri\Documents\Unreal Projects\ops1\Scenarios"
RESULTS_PATH = r"C:\Users\rodri\Documents\Unreal Projects\ops1\Results"

def get_all_scenarios():
    """Load all scenario JSON files from the Scenarios folder."""
    scenarios = []
    for filename in sorted(os.listdir(SCENARIOS_PATH)):
        if filename.endswith(".json"):
            filepath = os.path.join(SCENARIOS_PATH, filename)
            with open(filepath, "r") as f:
                scenario = json.load(f)
                scenario["filepath"] = filepath
                scenarios.append(scenario)
    return scenarios

def run_scenario(scenario):
    """Simulate running a scenario and return a result."""
    print(f"  Running scenario: {scenario['scenario_id']} on {scenario['object']}...")

    # In a full implementation this would launch UE5 headlessly
    # For now we simulate a result based on scenario difficulty
    import random
    tolerance = scenario["placement_tolerance_mm"]
    max_time = scenario["max_cycle_time_s"]

    # Simulate placement error and cycle time
    placement_error = random.uniform(0, tolerance * 1.5)
    cycle_time = random.uniform(1.0, max_time * 0.9)

    # Determine success
    success = placement_error <= tolerance

    # Determine failure tag
    if success:
        failure_tag = "NONE"
    elif cycle_time >= max_time:
        failure_tag = "TIMEOUT"
    elif placement_error > tolerance * 1.2:
        failure_tag = "PLACEMENT_MISS"
    else:
        failure_tag = "GRASP_FAIL"

    return {
        "scenario_id": scenario["scenario_id"],
        "object": scenario["object"],
        "success": success,
        "placement_error_mm": round(placement_error, 2),
        "cycle_time_s": round(cycle_time, 2),
        "failure_tag": failure_tag,
        "placement_tolerance_mm": tolerance,
        "max_cycle_time_s": max_time
    }

def run_suite(trials_per_scenario=5):
    """Run all scenarios for a given number of trials."""
    scenarios = get_all_scenarios()
    all_results = []

    print(f"\n=== OptiSim Test Runner ===")
    print(f"Found {len(scenarios)} scenarios")
    print(f"Running {trials_per_scenario} trials each")
    print(f"Total trials: {len(scenarios) * trials_per_scenario}\n")

    for scenario in scenarios:
        print(f"Scenario: {scenario['scenario_id']} ({scenario['object']})")
        for trial in range(1, trials_per_scenario + 1):
            result = run_scenario(scenario)
            result["trial"] = trial
            all_results.append(result)
            status = "PASS" if result["success"] else "FAIL"
            print(f"    Trial {trial}: {status} | Error: {result['placement_error_mm']}mm | Time: {result['cycle_time_s']}s | Tag: {result['failure_tag']}")
        print()

    return all_results

def export_results(results):
    """Export results to a CSV file."""
    os.makedirs(RESULTS_PATH, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RESULTS_PATH, f"run_{timestamp}.csv")

    fieldnames = ["scenario_id", "object", "trial", "success",
                  "placement_error_mm", "cycle_time_s", "failure_tag",
                  "placement_tolerance_mm", "max_cycle_time_s"]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Results exported to: {filename}")
    return filename

def print_summary(results):
    """Print a summary of the test run."""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    pass_rate = (passed / total) * 100

    print("=== Test Run Summary ===")
    print(f"Total Trials:  {total}")
    print(f"Passed:        {passed} ({pass_rate:.1f}%)")
    print(f"Failed:        {failed}")
    print()

    # Failure breakdown
    failure_tags = {}
    for r in results:
        if not r["success"]:
            tag = r["failure_tag"]
            failure_tags[tag] = failure_tags.get(tag, 0) + 1

    if failure_tags:
        print("Failure Breakdown:")
        for tag, count in failure_tags.items():
            print(f"  {tag}: {count}")
    print()

    # Per scenario summary
    print("Per Scenario Results:")
    scenario_ids = sorted(set(r["scenario_id"] for r in results))
    for sid in scenario_ids:
        scenario_results = [r for r in results if r["scenario_id"] == sid]
        s_passed = sum(1 for r in scenario_results if r["success"])
        s_total = len(scenario_results)
        avg_error = sum(r["placement_error_mm"] for r in scenario_results) / s_total
        print(f"  {sid}: {s_passed}/{s_total} passed | Avg Error: {avg_error:.2f}mm")

if __name__ == "__main__":
    results = run_suite(trials_per_scenario=5)
    print_summary(results)
    export_results(results)