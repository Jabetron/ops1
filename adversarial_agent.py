"""
adversarial_agent.py

Reads ops1 test results, uses GPT-4o (via GitHub Models API) to generate
adversarial scenarios targeting policy weaknesses, runs them, and repeats.

Usage:
    python adversarial_agent.py [--rounds N]

Requirements:
    pip install openai
    export GITHUB_TOKEN=<your_pat>
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
SCENARIOS_DIR = BASE_DIR / "Scenarios"
RESULTS_DIR   = BASE_DIR / "Results"

# ── GitHub Models client ──────────────────────────────────────────────────────
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("Error: GITHUB_TOKEN environment variable not set.")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=TOKEN,
)
MODEL = "gpt-4o"

# ── Scenario helpers ──────────────────────────────────────────────────────────
def next_scenario_ids(n: int) -> list[str]:
    """Return the next n auto-incremented scenario IDs (e.g. SCN_007, SCN_008)."""
    existing = [
        f.stem for f in SCENARIOS_DIR.glob("SCN_*.json")
    ]
    nums = []
    for name in existing:
        m = re.match(r"SCN_(\d+)", name)
        if m:
            nums.append(int(m.group(1)))
    start = max(nums, default=0) + 1
    return [f"SCN_{start + i:03d}" for i in range(n)]


def save_scenario(scenario: dict) -> Path:
    sid = scenario["scenario_id"]
    path = SCENARIOS_DIR / f"{sid}.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists — will not overwrite.")
    path.write_text(json.dumps(scenario, indent=2))
    return path


# ── Result helpers ────────────────────────────────────────────────────────────
def load_all_results() -> list[dict]:
    rows = []
    if not RESULTS_DIR.exists():
        return rows
    for csv_path in sorted(RESULTS_DIR.glob("*.csv")):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                row["success"] = row["success"].strip().lower() in ("true", "1")
                row["placement_error_mm"]  = float(row["placement_error_mm"])
                row["cycle_time_s"]        = float(row["cycle_time_s"])
                row["placement_tolerance_mm"] = float(row["placement_tolerance_mm"])
                row["max_cycle_time_s"]    = float(row["max_cycle_time_s"])
                rows.append(row)
    return rows


def load_scenario_poses() -> dict[str, dict]:
    """Map scenario_id → {distance, y_offset} for distance-bucketing."""
    poses = {}
    for p in SCENARIOS_DIR.glob("SCN_*.json"):
        try:
            s = json.loads(p.read_text())
            sid = s["scenario_id"]
            sp = s.get("start_pose", {})
            tp = s.get("target_pose", {})
            dx = tp.get("x", 0) - sp.get("x", 0)
            dy = tp.get("y", 0) - sp.get("y", 0)
            dist = math.sqrt(dx**2 + dy**2)
            poses[sid] = {"distance_mm": round(dist, 1), "y_offset": tp.get("y", 0)}
        except Exception:
            pass
    return poses


def build_failure_report(results: list[dict]) -> dict:
    if not results:
        return {"error": "no_results"}

    total = len(results)
    passed = sum(1 for r in results if r["success"])

    # -- by object
    objects = {}
    for r in results:
        obj = r["object"]
        bucket = objects.setdefault(obj, {"trials": 0, "passed": 0})
        bucket["trials"] += 1
        if r["success"]:
            bucket["passed"] += 1
    by_object = {
        obj: {
            "pass_rate": round(v["passed"] / v["trials"] * 100, 1),
            "trials": v["trials"],
        }
        for obj, v in objects.items()
    }

    # -- by tolerance
    tols = {}
    for r in results:
        t = r["placement_tolerance_mm"]
        b = tols.setdefault(t, {"trials": 0, "passed": 0})
        b["trials"] += 1
        if r["success"]:
            b["passed"] += 1
    by_tolerance = {
        f"{t}mm": {
            "pass_rate": round(v["passed"] / v["trials"] * 100, 1),
            "trials": v["trials"],
        }
        for t, v in sorted(tols.items())
    }

    # -- by distance bucket (uses scenario pose data)
    poses = load_scenario_poses()
    dist_buckets: dict[str, dict] = {}
    for r in results:
        info = poses.get(r["scenario_id"])
        if info is None:
            continue
        d = info["distance_mm"]
        if d < 100:
            label = "short (<100mm)"
        elif d < 200:
            label = "medium (100-200mm)"
        elif d < 300:
            label = "long (200-300mm)"
        else:
            label = "very_long (>300mm)"
        b = dist_buckets.setdefault(label, {"trials": 0, "passed": 0})
        b["trials"] += 1
        if r["success"]:
            b["passed"] += 1
    by_distance = {
        label: {
            "pass_rate": round(v["passed"] / v["trials"] * 100, 1),
            "trials": v["trials"],
        }
        for label, v in dist_buckets.items()
    }

    # -- failure tag distribution
    tag_counts: dict[str, int] = {}
    for r in results:
        if not r["success"]:
            tag = r["failure_tag"]
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # -- per scenario
    scen_map: dict[str, dict] = {}
    for r in results:
        sid = r["scenario_id"]
        b = scen_map.setdefault(sid, {"trials": 0, "passed": 0, "errors": []})
        b["trials"] += 1
        if r["success"]:
            b["passed"] += 1
        else:
            b["errors"].append(r["placement_error_mm"])
    by_scenario = {}
    for sid, v in sorted(scen_map.items()):
        pr = round(v["passed"] / v["trials"] * 100, 1)
        avg_err = round(sum(v["errors"]) / len(v["errors"]), 2) if v["errors"] else 0
        pose_info = poses.get(sid, {})
        by_scenario[sid] = {
            "pass_rate": pr,
            "trials": v["trials"],
            "avg_failure_error_mm": avg_err,
            "distance_mm": pose_info.get("distance_mm"),
            "y_offset": pose_info.get("y_offset"),
        }

    # -- untested parameter space
    tested_tols   = sorted(tols.keys())
    tested_dists  = sorted(poses[sid]["distance_mm"] for sid in poses)
    all_tols      = [5.0, 10.0, 15.0, 20.0]
    untested_tols = [t for t in all_tols if t not in tested_tols]

    return {
        "summary": {
            "total_trials": total,
            "overall_pass_rate": round(passed / total * 100, 1),
        },
        "by_object":    by_object,
        "by_tolerance": by_tolerance,
        "by_distance":  by_distance,
        "failure_tags": tag_counts,
        "by_scenario":  by_scenario,
        "coverage_gaps": {
            "untested_tolerances_mm": untested_tols,
            "distance_range_tested_mm": {
                "min": min(tested_dists) if tested_dists else None,
                "max": max(tested_dists) if tested_dists else None,
            },
        },
    }


# ── GPT-4o interaction ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an adversarial simulation engineer. Your job is to break a humanoid \
robot pick-and-place policy by designing test scenarios that expose its \
weaknesses.

You will receive a structured failure report from previous test runs. Analyze \
it and generate exactly 3 new scenarios as a JSON array. Each scenario must \
follow this schema exactly:

[
  {
    "scenario_id": "SCN_XXX",
    "object": "TestBox" | "TestCylinder" | "TestSphere",
    "start_pose": {"x": float, "y": float, "z": 100.0},
    "target_pose": {"x": float, "y": float, "z": 100.0},
    "placement_tolerance_mm": 5.0 | 10.0 | 15.0 | 20.0,
    "max_cycle_time_s": 3.0 | 4.0 | 5.0 | 6.0
  },
  ...
]

Rules:
- Target x must be in range 50–400
- Target y (lateral offset) must be in range -150 to 150
- Start pose is always {"x": 0, "y": 0, "z": 100}
- Scenarios must be plausible real-world conditions, not absurd extremes
- Vary object type, distance, lateral offset, tolerance, and time constraint
- If PLACEMENT_MISS dominates failures → probe tighter tolerances
- If GRASP_FAIL dominates → probe closer distances with awkward lateral offsets
- If TIMEOUT dominates → probe tighter time constraints
- Prioritize untested regions of the parameter space
- Fill in the correct SCN_XXX IDs from the provided next_ids list

Before outputting the JSON, write 2–3 sentences explaining your reasoning. \
Then output the JSON array on its own, starting with [ and ending with ]. \
No markdown fences, no extra text after the array.\
"""


def ask_gpt4o(failure_report: dict, next_ids: list[str], attempt: int = 1) -> tuple[str, list[dict]]:
    """
    Returns (reasoning_text, list_of_scenario_dicts).
    Retries once with stricter prompt if JSON is malformed.
    """
    user_content = (
        f"Next scenario IDs to use: {next_ids}\n\n"
        f"Failure report:\n{json.dumps(failure_report, indent=2)}"
    )

    if attempt == 2:
        user_content = (
            "Your previous response had malformed JSON. "
            "Output ONLY the JSON array — no explanation, no markdown.\n\n"
            + user_content
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        temperature=0.7,
        max_tokens=1200,
    )

    raw = response.choices[0].message.content.strip()

    # Split reasoning from JSON array
    # Find the first '[' that starts the array
    bracket_idx = raw.find("[")
    reasoning = raw[:bracket_idx].strip() if bracket_idx > 0 else ""
    json_part  = raw[bracket_idx:] if bracket_idx >= 0 else raw

    try:
        scenarios = json.loads(json_part)
        if not isinstance(scenarios, list):
            raise ValueError("Expected a JSON array")
        return reasoning, scenarios
    except (json.JSONDecodeError, ValueError) as e:
        if attempt == 1:
            print(f"  [warn] Malformed JSON from GPT-4o ({e}), retrying...")
            return ask_gpt4o(failure_report, next_ids, attempt=2)
        raise RuntimeError(f"GPT-4o returned invalid JSON after retry: {e}\n\nRaw:\n{raw}")


# ── Running new scenarios inline ──────────────────────────────────────────────
def run_scenarios_inline(scenarios: list[dict], trials: int = 5) -> list[dict]:
    """
    Run a specific list of scenario dicts using test_runner's simulation logic
    without re-running the entire suite.
    """
    import random
    results = []
    for scenario in scenarios:
        tolerance = scenario["placement_tolerance_mm"]
        max_time  = scenario["max_cycle_time_s"]
        for trial in range(1, trials + 1):
            placement_error = random.uniform(0, tolerance * 1.5)
            cycle_time      = random.uniform(1.0, max_time * 0.9)
            success         = placement_error <= tolerance
            if success:
                failure_tag = "NONE"
            elif cycle_time >= max_time:
                failure_tag = "TIMEOUT"
            elif placement_error > tolerance * 1.2:
                failure_tag = "PLACEMENT_MISS"
            else:
                failure_tag = "GRASP_FAIL"
            results.append({
                "scenario_id":           scenario["scenario_id"],
                "object":                scenario["object"],
                "trial":                 trial,
                "success":               success,
                "placement_error_mm":    round(placement_error, 2),
                "cycle_time_s":          round(cycle_time, 2),
                "failure_tag":           failure_tag,
                "placement_tolerance_mm": tolerance,
                "max_cycle_time_s":      max_time,
            })
    return results


def save_results(results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"run_{timestamp}.csv"
    fieldnames = [
        "scenario_id", "object", "trial", "success",
        "placement_error_mm", "cycle_time_s", "failure_tag",
        "placement_tolerance_mm", "max_cycle_time_s",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    return path


# ── GPT-4o final conclusion ───────────────────────────────────────────────────
def get_conclusion(all_adv_results: list[dict], all_scenarios_generated: list[dict]) -> str:
    report = build_failure_report(all_adv_results)
    prompt = (
        "You have completed adversarial scenario generation for a humanoid robot "
        "pick-and-place policy. Here is the aggregated failure report across all "
        "adversarial scenarios:\n\n"
        f"{json.dumps(report, indent=2)}\n\n"
        "Write exactly one paragraph (4–6 sentences) concluding on the policy's "
        "robustness: what it handles well, where it breaks down, and what the most "
        "critical vulnerability is. Be direct and technical."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


# ── Main agent loop ───────────────────────────────────────────────────────────
SEP = "=" * 70

def run_agent(num_rounds: int = 3, trials_per_scenario: int = 5):
    print(f"\n{SEP}")
    print("  ops1 Adversarial Scenario Agent")
    print(f"  Rounds: {num_rounds}  |  Trials per scenario: {trials_per_scenario}")
    print(SEP)

    all_adv_results:    list[dict] = []
    all_new_scenarios:  list[dict] = []

    for round_num in range(1, num_rounds + 1):
        print(f"\n{'─' * 70}")
        print(f"  ROUND {round_num}/{num_rounds}")
        print(f"{'─' * 70}")

        # 1. Load all results so far
        cumulative_results = load_all_results() + all_adv_results

        if not cumulative_results:
            print("  [warn] No results found in Results\\. Run test_runner.py first.")
            print("  Running base suite now to bootstrap...")
            import test_runner as tr
            base_results = tr.run_suite(trials_per_scenario)
            tr.export_results(base_results)
            cumulative_results = base_results

        # 2. Build failure report
        report = build_failure_report(cumulative_results)
        total   = report["summary"]["total_trials"]
        overall = report["summary"]["overall_pass_rate"]
        print(f"\n  Failure Report Summary")
        print(f"  Overall pass rate : {overall}%  ({total} trials)")
        print(f"  By object         : " + ", ".join(
            f"{obj} {v['pass_rate']}%" for obj, v in report["by_object"].items()
        ))
        print(f"  By tolerance      : " + ", ".join(
            f"{t} {v['pass_rate']}%" for t, v in report["by_tolerance"].items()
        ))
        top_tag = max(report["failure_tags"].items(), key=lambda x: x[1]) if report["failure_tags"] else ("N/A", 0)
        print(f"  Dominant failure  : {top_tag[0]} ({top_tag[1]} occurrences)")

        # 3. Ask GPT-4o for new scenarios
        new_ids = next_scenario_ids(3)
        print(f"\n  Querying GPT-4o for adversarial scenarios (IDs: {new_ids})...")

        try:
            reasoning, new_scenarios = ask_gpt4o(report, new_ids)
        except RuntimeError as e:
            print(f"  [error] {e}")
            break

        # Patch IDs in case GPT-4o used wrong ones
        for i, scen in enumerate(new_scenarios[:3]):
            scen["scenario_id"] = new_ids[i]

        # 4. Print GPT-4o reasoning
        if reasoning:
            print(f"\n  GPT-4o reasoning:\n  {reasoning.replace(chr(10), chr(10) + '  ')}")

        # 5. Save new scenario JSONs
        print(f"\n  Generated scenarios:")
        saved_scenarios = []
        for scen in new_scenarios[:3]:
            try:
                path = save_scenario(scen)
                tp = scen["target_pose"]
                dist = round(math.sqrt(tp["x"]**2 + tp["y"]**2), 1)
                print(f"    {scen['scenario_id']} | {scen['object']:14s} | "
                      f"dist={dist}mm | y={tp['y']} | "
                      f"tol={scen['placement_tolerance_mm']}mm | "
                      f"max_t={scen['max_cycle_time_s']}s  → {path.name}")
                saved_scenarios.append(scen)
            except FileExistsError as e:
                print(f"    [skip] {e}")

        if not saved_scenarios:
            print("  [warn] No new scenarios saved this round.")
            continue

        all_new_scenarios.extend(saved_scenarios)

        # 6. Run new scenarios
        print(f"\n  Running {len(saved_scenarios)} new scenarios ({trials_per_scenario} trials each)...")
        round_results = run_scenarios_inline(saved_scenarios, trials_per_scenario)
        all_adv_results.extend(round_results)

        # 7. Save results to CSV
        csv_path = save_results(round_results)
        print(f"  Results saved → {csv_path.name}")

        # 8. Round summary
        r_total  = len(round_results)
        r_passed = sum(1 for r in round_results if r["success"])
        r_rate   = round(r_passed / r_total * 100, 1)
        round_tags: dict[str, int] = {}
        for r in round_results:
            if not r["success"]:
                round_tags[r["failure_tag"]] = round_tags.get(r["failure_tag"], 0) + 1

        print(f"\n  Round {round_num} results: {r_rate}% pass rate ({r_passed}/{r_total})")
        if round_tags:
            top = max(round_tags, key=round_tags.__getitem__)
            new_modes = set(round_tags) - set(t for t, _ in [top_tag])
            print(f"  Failure breakdown : " + ", ".join(f"{t}={c}" for t, c in round_tags.items()))
            if new_modes:
                print(f"  *** New failure mode detected: {new_modes} ***")
            else:
                print(f"  Policy held on known failure modes (no new modes found).")
        else:
            print(f"  Policy held — all adversarial trials passed.")

    # ── Final Report ──────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  FINAL ADVERSARIAL REPORT")
    print(SEP)

    print(f"\n  Total new scenarios generated : {len(all_new_scenarios)}")

    if all_adv_results:
        # Hardest scenarios
        adv_report = build_failure_report(all_adv_results)
        by_scen = adv_report.get("by_scenario", {})
        sorted_scen = sorted(by_scen.items(), key=lambda x: x[1]["pass_rate"])
        print(f"\n  Hardest scenarios (lowest pass rate):")
        for sid, info in sorted_scen[:5]:
            print(f"    {sid}: {info['pass_rate']}% pass rate ({info['trials']} trials)")

        # Dominant failure tag
        all_tags = adv_report.get("failure_tags", {})
        if all_tags:
            dom_tag = max(all_tags, key=all_tags.__getitem__)
            print(f"\n  Dominant failure tag across adversarial runs: {dom_tag} ({all_tags[dom_tag]} occurrences)")

        # GPT-4o conclusion
        print(f"\n  Requesting policy robustness conclusion from GPT-4o...")
        try:
            conclusion = get_conclusion(all_adv_results, all_new_scenarios)
            print(f"\n  Policy Robustness Conclusion:")
            print(f"  {'─' * 60}")
            # Wrap at 68 chars
            words = conclusion.split()
            line = "  "
            for word in words:
                if len(line) + len(word) + 1 > 70:
                    print(line)
                    line = "  " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(line)
            print(f"  {'─' * 60}")
        except Exception as e:
            print(f"  [error] Could not get conclusion: {e}")
    else:
        print("\n  No adversarial results to report.")

    print(f"\n{SEP}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ops1 adversarial scenario agent")
    parser.add_argument("--rounds", type=int, default=3, help="Number of agent rounds (default: 3)")
    parser.add_argument("--trials", type=int, default=5, help="Trials per scenario (default: 5)")
    args = parser.parse_args()
    run_agent(num_rounds=args.rounds, trials_per_scenario=args.trials)
