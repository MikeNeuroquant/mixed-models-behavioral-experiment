"""
02 — Build the 30-min attentional-isolation dataset (single-trial + time-split)
==============================================================================

Extracts the trials collected during the 30-minute isolation window
(unilateral tracking for UR/UL groups, bilateral tracking for the control
group), tags each trial with the visual field, ipsilateral/contralateral
label relative to stimulation site, and a 10-min time bin (10 / 20 / 30).

Outputs:
    - all_isolation_time_split_single_trial.csv   (one row per trial in the window)
    - all_isolation_time_collapsed.csv            (subject × condition means)

Configure the RAW_ROOT and OUT_ROOT paths below before running.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# CONFIG — set these to your own paths
# -----------------------------------------------------------------------------
RAW_ROOT = Path("./raw_data")
OUT_ROOT = Path("./derivatives")
RAW_SUBDIRS = ["data", "data_2"]

OUT_ROOT.mkdir(parents=True, exist_ok=True)

CONDITIONS = ["Sham", "Active"]

# Cohort (montage) split
COHORT_RIGHT_MONTAGE = [
    "S2", "S3", "S4", "S5", "S8", "S9", "S11", "S17", "S25", "S26", "S27",
    "S30", "S36", "S6", "S7", "S10", "S13", "S15", "S16", "S19", "S20",
    "S28", "S29", "S32", "S34", "S38", "S1", "S12", "S14", "S18", "S21",
    "S22", "S23", "S24", "S31", "S33", "S37", "S35", "S39",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def list_subjects(raw_root: Path, subdirs: list[str]) -> list[str]:
    all_subjects = []
    for sub in subdirs:
        for item in os.listdir(raw_root / sub):
            if item in {"Scartare", ".DS_Store"}:
                continue
            all_subjects.append(item)
    return sorted(all_subjects, key=lambda x: int(x[1:]))


def find_subject_path(raw_root: Path, subdirs: list[str], subject: str) -> Path | None:
    for sub in subdirs:
        candidate = raw_root / sub / subject
        if candidate.exists():
            return candidate
    return None


def load_isolation_file(folder: Path, subject: str, isolation_label: str,
                        condition: str) -> pd.DataFrame | None:
    for file in os.listdir(folder):
        if file.endswith(".txt"):
            df = pd.read_table(folder / file).dropna()
            df["Subject"] = subject
            df["Isolation"] = isolation_label
            df["Stimulation"] = condition
            return df
    return None


# -----------------------------------------------------------------------------
# 1. Walk raw tree and pick up isolation trials (unilateral OR bilateral control)
# -----------------------------------------------------------------------------
subjects = list_subjects(RAW_ROOT, RAW_SUBDIRS)

collected = []
for condition in CONDITIONS:
    for subject in subjects:
        subj_path = find_subject_path(RAW_ROOT, RAW_SUBDIRS, subject)
        if subj_path is None:
            continue
        cond_path = subj_path / condition
        if not cond_path.exists():
            continue

        for folder in os.listdir(cond_path):
            folder_path = cond_path / folder
            if "trackingUnilat" in folder:
                df = load_isolation_file(folder_path, subject,
                                         "Attended Visual Field", condition)
                if df is not None:
                    collected.append(df)
            elif "trackingFixed_Bilateral" in folder:
                df = load_isolation_file(folder_path, subject,
                                         "Bilateral_Control", condition)
                if df is not None:
                    collected.append(df)

all_isolation = pd.concat(collected, ignore_index=True)
print(f"Loaded {len(all_isolation)} isolation trials from "
      f"{all_isolation['Subject'].nunique()} subjects")

# -----------------------------------------------------------------------------
# 2. Recode Response (bool → 0/1), derive visual field and 10-min time bin
# -----------------------------------------------------------------------------
all_isolation["Response"] = all_isolation["Response"].map(lambda x: 1 if x else 0)

all_isolation["VisualF"] = all_isolation["Trial Condition"].map(
    lambda x: "Left" if x in ["Bilateral-Left", "Unilateral-Left"] else "Right"
)

# 10-minute bins across the 30-min window (StartTime is in seconds)
def time_bin(t: float) -> int:
    if t <= 600:
        return 10
    if t <= 1200:
        return 20
    return 30

all_isolation["Time Split"] = all_isolation["StartTime"].map(time_bin)

# Collection (montage cohort)
all_isolation["Collection"] = all_isolation["Subject"].map(
    lambda x: "1" if x in COHORT_RIGHT_MONTAGE else "2"
)

# Drop columns not needed downstream (kept as separate copy for the collapsed file)
single_trial = all_isolation.drop(columns=["NTrial"], errors="ignore").copy()
single_trial = single_trial.drop(columns=["Trial", "Trial Condition"], errors="ignore")

# -----------------------------------------------------------------------------
# 3. Subject × condition × time-bin means (collapsed file)
# -----------------------------------------------------------------------------
collapsed = (
    single_trial
    .groupby(["Subject", "Isolation", "Stimulation", "Time Split",
              "VisualF", "Collection"], as_index=False)
    .mean(numeric_only=True)
)

# -----------------------------------------------------------------------------
# 4. Save
# -----------------------------------------------------------------------------
single_trial.to_csv(OUT_ROOT / "all_isolation_time_split_single_trial.csv", index=False)
collapsed.to_csv(OUT_ROOT / "all_isolation_time_collapsed.csv", index=False)

print(f"Output written to: {OUT_ROOT.resolve()}")
