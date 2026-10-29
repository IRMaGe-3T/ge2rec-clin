
import os
import re
import csv
import logging


logger = logging.getLogger(__name__)


def get_reco_result(input_file, output_file):

    logger.info(f"Get reco result from eprime file: {input_file}")

    # ============================================================
    # Configuration
    # ============================================================

    if not input_file.endswith(".txt"): 
        logger.info("Cannot used Eprime file")
        return


    conditions_to_keep = ["NEW", "CONTROL", "OLD"]

    # ============================================================
    # Read E-Prime file
    # ============================================================

    with open(input_file, "r", encoding="utf-16") as f:
        text = f.read()


    # ============================================================
    # Parse LogFrames
    # ============================================================

    logframes = text.split("*** LogFrame Start ***")

    trials = []

    for frame in logframes:

        if "*** LogFrame End ***" not in frame:
            continue

        frame = frame.split("*** LogFrame End ***")[0]

        data = {}

        for line in frame.splitlines():

            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            key = key.strip()
            value = value.strip()

            data[key] = value

        # Keep only task trials
        if data.get("Procedure", "").lower() != "task":
            continue

        condition = data.get("CONDITION", "").strip().upper()

        if condition not in conditions_to_keep:
            continue

        response = data.get("RESPONSE", "").strip().lower()
        expected = data.get("MOT.RESP", "").strip().lower()

        # Reaction time
        rt = data.get("MOT.RT", "").strip()

        try:
            rt = float(rt)
        except (ValueError, TypeError):
            rt = None

        # Correct / incorrect
        if response == "":
            accuracy = "missing"
        elif response == expected:
            accuracy = "correct"
        else:
            accuracy = "error"

        trials.append({
            "CONDITION": condition,
            "RESPONSE": response,
            "MOT.RESP": expected,
            "ACCURACY": accuracy,
            "RT_ms": rt
        })


    # ============================================================
    # Calculate statistics for each condition
    # ============================================================

    results = []

    for condition in conditions_to_keep:

        condition_trials = [
            trial for trial in trials
            if trial["CONDITION"] == condition
        ]

        n_trials = len(condition_trials)

        n_correct = sum(
            trial["ACCURACY"] == "correct"
            for trial in condition_trials
        )

        n_errors = sum(
            trial["ACCURACY"] == "error"
            for trial in condition_trials
        )

        n_missing = sum(
            trial["ACCURACY"] == "missing"
            for trial in condition_trials
        )

        # Percentages calculated over all trials
        if n_trials > 0:
            percent_correct = 100 * n_correct / n_trials
            percent_error = 100 * n_errors / n_trials
        else:
            percent_correct = None
            percent_error = None

        # Mean RT
        valid_rts = [
            trial["RT_ms"]
            for trial in condition_trials
            if trial["RT_ms"] is not None
        ]

        if valid_rts:
            mean_rt = sum(valid_rts) / len(valid_rts)
        else:
            mean_rt = None

        results.append({
            "CONDITION": condition,
            "N_trials": n_trials,
            "N_correct": n_correct,
            "N_error": n_errors,
            "N_missing": n_missing,
            "Percent_correct": round(percent_correct, 2)
                if percent_correct is not None else "",
            "Percent_error": round(percent_error, 2)
                if percent_error is not None else "",
            "Mean_RT_ms": round(mean_rt, 2)
                if mean_rt is not None else ""
        })


    # ============================================================
    # Save CSV
    # ============================================================

    fieldnames = [
        "CONDITION",
        "N_trials",
        "N_correct",
        "N_error",
        "N_missing",
        "Percent_correct",
        "Percent_error",
        "Mean_RT_ms"
    ]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=","
        )

        writer.writeheader()
        writer.writerows(results)


    logger.info(f"Results saved to: {output_file}")