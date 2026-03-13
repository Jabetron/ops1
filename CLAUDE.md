# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OptiSim** — a robotics simulation validation framework built in Unreal Engine 5.7. It validates robot pick-and-place performance through closed-loop simulation with data-driven JSON scenarios.

## Build & Development Commands

### Build C++ Code
Open `ops1.sln` in Visual Studio 2022 and build from there, or use Unreal Build Tool:
```bash
"C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ops1 Win64 Development "C:\Users\rodri\Documents\Unreal Projects\ops1\ops1.uproject"
```

### Run the Editor
```bash
"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Users\rodri\Documents\Unreal Projects\ops1\ops1.uproject"
```

### Run Automated Test Suite
```bash
python test_runner.py
```
Results are written to `Results/` as timestamped CSVs. Trials per scenario can be configured inside `test_runner.py` (default: 5).

## Architecture

### Core C++ Classes (`Source/ops1/`)

**`GraspComponent`** (`UGraspComponent`, extends `USphereComponent`)
- Central physics logic. Manages a state machine: `Idle → Reaching → Grasping → Carrying → Placing → Complete/Failed`
- Detects 4 failure modes: `GraspFail`, `PlacementMiss`, `Timeout`, `DropInTransit`
- Key config: `PlacementToleranceMM` (default 20mm), `MaxCycleTimeSeconds` (default 6s)
- Grasp detection uses a 15cm sphere overlap on physics-enabled actors; placement uses teleport physics for determinism

**`RobotArm`** (`ARobotArm`, `AActor`)
- Owns the `GraspComponent`. Orchestrates a trial via `ExecuteTrial()` / `IsTrialComplete()` / `ResetForNextTrial()`

**`ScenarioLoader`** (`AScenarioLoader`, `AActor`)
- Parses JSON scenario files into `FScenarioConfig` structs and positions actors in the level
- Depends on UE5 `Json` and `JsonUtilities` modules

**Build deps** (`ops1.Build.cs`): Core, CoreUObject, Engine, InputCore, EnhancedInput, Json, JsonUtilities

### Scenario System

Scenarios are JSON files in `Scenarios/` (e.g. `SCN_001.json`):
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
Target objects: `TestBox`, `TestCylinder`, `TestSphere`.

### Key Levels

- **TE2.umap** — Main physics test arena (3 objects); use this for validation runs
- **TE1.umap** — Default startup map

### Blueprint Layer

`BP_RobotArm` and `BP_ScenarioLoader` in `Content/` are thin Blueprint wrappers over the C++ classes. Core logic lives in C++.

## Failure Taxonomy

| Tag | Meaning |
|-----|---------|
| `PLACEMENT_MISS` | Placed outside tolerance radius |
| `GRASP_FAIL` | Object not successfully grasped |
| `TIMEOUT` | Trial exceeded `max_cycle_time_s` |
| `DROP_IN_TRANSIT` | Object dropped before reaching target |
| `NONE` | Success |

## Test Results Format

CSV columns: `scenario_id, object, trial, success, placement_error_mm, cycle_time_s, failure_tag, placement_tolerance_mm, max_cycle_time_s`
