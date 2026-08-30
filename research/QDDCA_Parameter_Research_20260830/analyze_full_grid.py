"""Audit monotonic regions and Pareto points in the full Q-DDCA grid."""

import csv
import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
INPUT = DIRECTORY / "full_grid.csv"
OUTPUT = DIRECTORY / "full_grid_analysis.json"
ALGORITHM = "real_time_memory_aware"


def load_records():
    with INPUT.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["algorithm"] == ALGORITHM]
    records = {}
    for row in rows:
        key = (int(row["window_size"]), int(row["send_max_try"]))
        records[key] = {
            "window_size": key[0],
            "send_max_try": key[1],
            "edr": float(row["total_edr_pairs_s"]),
            "dropped": float(row["mean_dropped_pairs"]),
            "cv": float(row["mean_edr_cv"]),
            "edr_sd": float(row["edr_std_pairs_s"]),
            "dropped_sd": float(row["dropped_std_pairs"]),
            "cv_sd": float(row["edr_cv_std"]),
        }
    return records


def load_raw_records():
    records = {}
    with (DIRECTORY / "full_grid_raw.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["algorithm"] != ALGORITHM:
                continue
            key = (
                int(row["window_size"]),
                int(row["send_max_try"]),
                int(row["seed"]),
            )
            records[key] = {
                "edr": float(row["total_edr_pairs_s"]),
                "dropped": float(row["dropped_pairs"]),
                "cv": float(row["edr_cv"]),
            }
    return records


def is_nonworse(previous, current, tolerance=1e-12):
    return (
        current["edr"] + tolerance >= previous["edr"]
        and current["dropped"] <= previous["dropped"] + tolerance
        and current["cv"] <= previous["cv"] + tolerance
    )


def is_strict(previous, current, tolerance=1e-12):
    return (
        current["edr"] > previous["edr"] + tolerance
        and current["dropped"] < previous["dropped"] - tolerance
        and current["cv"] < previous["cv"] - tolerance
    )


def prefix_end(records, fixed_axis, fixed_value):
    if fixed_axis == "M":
        keys = [(w, fixed_value) for w in range(1, 31)]
    else:
        keys = [(fixed_value, m) for m in range(1, 11)]
    end = keys[0]
    transitions = []
    for previous_key, current_key in zip(keys, keys[1:]):
        ok = is_nonworse(records[previous_key], records[current_key])
        transitions.append({"from": previous_key, "to": current_key, "nonworse": ok})
        if not ok:
            break
        end = current_key
    return {"end": end, "transitions": transitions}


def monotone_paths(records):
    paths = {(1, 1): [(1, 1)]}
    for w in range(1, 31):
        for m in range(1, 11):
            key = (w, m)
            if key == (1, 1):
                continue
            candidates = []
            for predecessor in ((w - 1, m), (w, m - 1)):
                if predecessor in paths and is_nonworse(records[predecessor], records[key]):
                    candidates.append(paths[predecessor] + [key])
            if candidates:
                paths[key] = max(candidates, key=len)
    best_key = max(
        paths,
        key=lambda key: (
            records[key]["edr"],
            -records[key]["cv"],
            -records[key]["dropped"],
        ),
    )
    return paths, best_key


def pareto_front(records):
    front = []
    for key, candidate in records.items():
        dominated = False
        for other_key, other in records.items():
            if other_key == key:
                continue
            weak = (
                other["edr"] >= candidate["edr"]
                and other["dropped"] <= candidate["dropped"]
                and other["cv"] <= candidate["cv"]
            )
            strict = (
                other["edr"] > candidate["edr"]
                or other["dropped"] < candidate["dropped"]
                or other["cv"] < candidate["cv"]
            )
            if weak and strict:
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return sorted(front, key=lambda row: (row["window_size"], row["send_max_try"]))


def seed_transition_audit(raw_records, previous, current, cv_tolerance=0.0001):
    rows = []
    for seed in (101, 202, 303):
        before = raw_records[(*previous, seed)]
        after = raw_records[(*current, seed)]
        rows.append({
            "seed": seed,
            "delta_edr": after["edr"] - before["edr"],
            "delta_dropped": after["dropped"] - before["dropped"],
            "delta_cv": after["cv"] - before["cv"],
            "exact_nonworse": is_nonworse(before, after),
            "practical_nonworse": (
                after["edr"] >= before["edr"] - 1e-6
                and after["dropped"] <= before["dropped"] + 1e-6
                and after["cv"] <= before["cv"] + cv_tolerance
            ),
        })
    return {
        "from": list(previous),
        "to": list(current),
        "cv_tolerance": cv_tolerance,
        "seeds": rows,
        "exact_consistent_seed_count": sum(row["exact_nonworse"] for row in rows),
        "practical_consistent_seed_count": sum(row["practical_nonworse"] for row in rows),
    }


def main():
    records = load_records()
    raw_records = load_raw_records()
    paths, best_key = monotone_paths(records)
    strict_transitions = []
    nonworse_transitions = []
    for (w, m), previous in records.items():
        for current_key in ((w + 1, m), (w, m + 1)):
            if current_key not in records:
                continue
            current = records[current_key]
            item = {"from": [w, m], "to": list(current_key)}
            if is_nonworse(previous, current):
                nonworse_transitions.append(item)
            if is_strict(previous, current):
                strict_transitions.append(item)

    result = {
        "definition": {
            "nonworse": "EDR current >= previous, dropped current <= previous, CV current <= previous",
            "strict": "EDR current > previous, dropped current < previous, CV current < previous",
            "path_moves": "Increase either w or M by exactly one at each step",
        },
        "record_count": len(records),
        "best_reachable_endpoint": records[best_key],
        "best_reachable_path": [list(key) for key in paths[best_key]],
        "reachable_cell_count": len(paths),
        "reachable_cells": [list(key) for key in sorted(paths)],
        "prefix_by_fixed_attempts": {
            str(m): prefix_end(records, "M", m) for m in range(1, 11)
        },
        "prefix_by_fixed_window": {
            str(w): prefix_end(records, "w", w) for w in range(1, 31)
        },
        "nonworse_transition_count": len(nonworse_transitions),
        "strict_transition_count": len(strict_transitions),
        "strict_transitions": strict_transitions,
        "pareto_front": pareto_front(records),
        "seed_transition_audits": [
            seed_transition_audit(raw_records, (2, 1), (2, 2)),
            seed_transition_audit(raw_records, (2, 2), (2, 3)),
            seed_transition_audit(raw_records, (1, 3), (2, 3)),
            seed_transition_audit(raw_records, (3, 1), (3, 2)),
            seed_transition_audit(raw_records, (3, 2), (3, 3)),
            seed_transition_audit(raw_records, (3, 3), (3, 4)),
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "best_reachable_endpoint": result["best_reachable_endpoint"],
        "best_reachable_path": result["best_reachable_path"],
        "reachable_cell_count": result["reachable_cell_count"],
        "strict_transition_count": result["strict_transition_count"],
        "pareto_front_count": len(result["pareto_front"]),
    }, indent=2))


if __name__ == "__main__":
    main()
