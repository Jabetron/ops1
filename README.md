# OptiSim — Robot Pick-and-Place Validation Framework

A closed-loop simulation validation framework built in Unreal Engine 5 and Python,
designed to evaluate robot arm grasp-and-place performance across data-driven test scenarios.


---

## Overview

OptiSim provides a complete test automation pipeline for validating robot pick-and-place
behavior in simulation. The system loads scenario configurations from JSON, executes trials
in a physics-based UE5 environment, captures pass/fail metrics, and exports structured
results for analysis.

---

## Architecture
```
Scenarios/          # Data-driven JSON scenario configs
Source/ops1/        # UE5 C++ simulation core
  GraspComponent    # Physics-based grasp detection and object transport
  RobotArm          # Actor owning GraspComponent, executes trial lifecycle
  ScenarioLoader    # Parses JSON configs, repositions actors, applies constraints
Content/
  TE2               # Test environment level (floor, table, 3 physics objects)
  BP_RobotArm       # Blueprint wrapper for RobotArm C++ class
  BP_ScenarioLoader # Blueprint wrapper for ScenarioLoader C++ class
test_runner.py      # Python automated test runner with CSV export
Results/            # Auto-generated CSV results per run
```

---

## Scenario System

Each scenario is a JSON file that defines:
- Target object (TestBox, TestCylinder, TestSphere)
- Start pose and target pose in 3D space
- Placement tolerance in millimeters
- Maximum allowed cycle time in seconds

Example scenario:
```json
{
  "scenario_id": "SCN_001",
  "object": "TestBox",
  "start_pose": {"x": 0.0, "y": 0.0, "z": 100.0},
  "target_pose": {"x": 120.0, "y": 0.0, "z": 100.0},
  "placement_tolerance_mm": 20.0,
  "max_cycle_time_s": 6.0
}
```

6 scenarios are included covering easy and hard placement tasks across all 3 object types.

---

## Failure Taxonomy

Each failed trial is tagged with a failure mode:

| Tag | Description |
|---|---|
| `PLACEMENT_MISS` | Object placed outside tolerance radius |
| `GRASP_FAIL` | Object not successfully grasped |
| `TIMEOUT` | Trial exceeded max cycle time |
| `DROP_IN_TRANSIT` | Object dropped before reaching target |

---

## Test Runner

The Python test runner (`test_runner.py`) automates scenario execution:
```bash
python test_runner.py
```

Output includes per-trial pass/fail, placement error in mm, cycle time, and failure tag.
Results are exported to `Results/run_<timestamp>.csv` for offline analysis.

---

## Sample Results
```
=== Test Run Summary ===
Total Trials:  30
Passed:        22 (73.3%)
Failed:        8

Failure Breakdown:
  PLACEMENT_MISS: 5
  GRASP_FAIL: 3

Per Scenario Results:
  SCN_001: 3/5 passed | Avg Error: 17.67mm
  SCN_002: 4/5 passed | Avg Error: 5.62mm
  SCN_003: 5/5 passed | Avg Error: 15.63mm
  SCN_004: 3/5 passed | Avg Error: 7.58mm
  SCN_005: 3/5 passed | Avg Error: 9.32mm
  SCN_006: 4/5 passed | Avg Error: 6.91mm
```

---

## Tech Stack

- Unreal Engine 5.7
- C++ (UE5 Actor/Component system)
- Blueprint (UE5 visual scripting)
- Python 3.14
- JSON scenario authoring
- CSV results export