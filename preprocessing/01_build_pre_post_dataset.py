"""
01 — Build the Pre / Post-1 / Post-2 single-trial dataset
=========================================================

Reads raw trial-level .txt logs produced by the PsychoPy MOT task,
tags each trial with subject, session (Pre / Post_1 / Post_2), sham vs.
active stimulation, visual field, experimental group (UR / UL / Bi),
manipulation label (Attended / Ignored / Control) and Collection
(1 = right montage cohort, 2 = left montage cohort).

Outputs:
    - long_format_single_trial.csv          (one row per trial)
    - long_format_collapsed.csv             (subject × condition means)
    - delta_long_format_averaged.csv        (post-pre gain, for Δ-analyses)
    - Trials.csv                            (trial counts, QA)

Configure the RAW_ROOT and OUT_ROOT paths below before running.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# CONFIG — set these to your own paths
# -----------------------------------------------------------------------------
RAW_ROOT = Path("./raw_data")           # contains subfolders "data" and "data_2"
OUT_ROOT = Path("./derivatives")         # cleaned datasets are written here
RAW_SUBDIRS = ["data", "data_2"]         # two acquisition batches

OUT_ROOT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Subject-to-condition lookup tables (assignment done at recruitment)
# -----------------------------------------------------------------------------
SUBJECT_RIGHT = [  # unilateral right MOT (UR)
    "S2", "S3", "S4", "S5", "S8", "S9", "S11", "S17", "S25", "S26", "S27",
    "S30", "S36", "S40", "S41", "S43", "S44", "S45", "S46", "S48", "S55",
    "S53", "S49", "S56", "S47", "S51",
]
SUBJECT_LEFT = [   # unilateral left MOT (UL)
    "S6", "S7", "S10", "S13", "S15", "S16", "S19", "S20", "S28", "S29",
    "S32", "S34", "S38", "S50", "S42", "S64", "S58", "S61", "S63", "S59",
    "S60", "S62", "S52", "S65", "S57", "S54",
]
SUBJECT_BIL = [    # bilateral control (Bi)
    "S1", "S12", "S14", "S18", "S21", "S22", "S23", "S24", "S31", "S33",
    "S37", "S35", "S39",
]

# Cohort split by stimulation montage
COHORT_RIGHT_MONTAGE = [  # Experiment 1
    "S2", "S3", "S4", "S5", "S8", "S9", "S11", "S17", "S25", "S26", "S27",
    "S30", "S36", "S6", "S7", "S10", "S13", "S15", "S16", "S19", "S20",
    "S28", "S29", "S32", "S34", "S38", "S1", "S12", "S14", "S18", "S21",
    "S22", "S23", "S24", "S31", "S33", "S37", "S35", "S39",
]
COHORT_LEFT_MONTAGE = [   # Experiment 2
    "S40", "S41", "S42", "S43", "S44", "S45", "S46", "S47", "S48", "S49",
    "S50", "S51", "S52", "S53", "S54", "S55", "S56", "S57", "S58", "S59",
    "S60", "S61", "S62", "S63", "S64", "S65",
]

CONDITIONS = ["Sham", "Active"]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def list_subjects(raw_root: Path, subdirs: list[str]) -> list[str]:
    """Return a sorted list of subject IDs across all acquisition subdirs."""
    all_subjects = []
    for sub in subdirs:
        d = raw_root / sub
        for item in os.listdir(d):
            if item in {"Scartare", ".DS_Store"}:
                continue
            all_subjects.append(item)
    # Sort by numeric part of the ID (S1, S2, ..., S65)
    return sorted(all_subjects, key=lambda x: int(x[1:]))


def find_subject_path(raw_root: Path, subdirs: list[str], subject: str) -> Path | None:
    """Locate which raw subdir contains a given subject."""
    for sub in subdirs:
        candidate = raw_root / sub / subject
        if candidate.exists():
            return candidate
    return None


def load_session_trials(folder_path: Path, subject: str, session: str, condition: str) -> pd.DataFrame | None:
    """Load the single .txt trial log inside a session folder."""
    for file in os.listdir(folder_path):
        if file.endswith(".txt"):
            df = pd.read_table(folder_path / file).dropna()
            df["Subject"] = subject
            df["Session"] = session
            df["Stimulation"] = condition
            return df
    return None


def label_manipulation(row: pd.Series) -> str | None:
    """Attended / Ignored / Control label based on tracked hemifield × group."""
    vf, group = row["VisualF"], row["manipulation"]
    if group == "UL":
        return "Attended Visual Field" if vf == "Left" else "Ignored Visual Field"
    if group == "UR":
        return "Attended Visual Field" if vf == "Right" else "Ignored Visual Field"
    if group == "Bi":
        return "Control"
    return None


# -----------------------------------------------------------------------------
# 1. Walk the raw tree and collect Pre / Post_1 / Post_2 trials
# -----------------------------------------------------------------------------
subjects = list_subjects(RAW_ROOT, RAW_SUBDIRS)
print(f"Found {len(subjects)} subjects")

session_folders = {
    "Pre":    "trackingFixed_PRE",
    "Post_1": "trackingFixed_POST1",
    "Post_2": "trackingFixed_POST2",
}

trials_by_session: dict[str, list[pd.DataFrame]] = {k: [] for k in session_folders}

for condition in CONDITIONS:
    for subject in subjects:
        subject_path = find_subject_path(RAW_ROOT, RAW_SUBDIRS, subject)
        if subject_path is None:
            continue
        cond_path = subject_path / condition
        if not cond_path.exists():
            continue

        for folder in os.listdir(cond_path):
            for session, prefix in session_folders.items():
                if prefix in folder:
                    df = load_session_trials(cond_path / folder, subject, session, condition)
                    if df is not None:
                        trials_by_session[session].append(df)

# -----------------------------------------------------------------------------
# 2. Concatenate and build the master long-format single-trial dataset
# -----------------------------------------------------------------------------
long_trials = pd.concat(
    trials_by_session["Pre"] + trials_by_session["Post_1"] + trials_by_session["Post_2"]
)

# Recode the response as 0/1 and derive visual field from trial condition string
long_trials["Response"] = long_trials["Response"].map(lambda x: 1 if x else 0)
long_trials["VisualF"] = long_trials["Trial Condition"].map(
    lambda x: "Left" if x == "Bilateral-Left" else "Right"
)

# Between-subject manipulation group (UR / UL / Bi)
long_trials["manipulation"] = long_trials["Subject"].map(
    lambda x: "UL" if x in SUBJECT_LEFT else "UR" if x in SUBJECT_RIGHT else "Bi"
)

# Trial-level manipulation label
long_trials["Manipulation"] = long_trials.apply(label_manipulation, axis=1)

# Collection (montage cohort)
long_trials["Collection"] = long_trials["Subject"].map(
    lambda x: "1" if x in COHORT_RIGHT_MONTAGE else "2"
)

# Keep only the columns needed downstream
long_trials = long_trials[[
    "Subject", "manipulation", "Manipulation", "Stimulation",
    "Session", "VisualF", "Response", "StartTime", "Collection",
]]

# -----------------------------------------------------------------------------
# 3. Collapse to subject × condition means (used by many models)
# -----------------------------------------------------------------------------
long_collapsed = (
    long_trials
    .groupby(["Subject", "manipulation", "Manipulation",
              "Stimulation", "Session", "VisualF", "Collection"], sort=False)
    .mean(numeric_only=True)
    .reset_index()
)

# -----------------------------------------------------------------------------
# 4. Build the Δ-accuracy (Post − Pre) file for both post time-points
# -----------------------------------------------------------------------------
mf = long_collapsed.drop(columns=["Collection", "StartTime"], errors="ignore")

pre     = mf[mf["Session"] == "Pre"]
post_1  = mf[mf["Session"] == "Post_1"]
post_2  = mf[mf["Session"] == "Post_2"]

merge_keys = ["Subject", "manipulation", "Manipulation", "Stimulation", "VisualF"]
merged = pre.merge(post_1, on=merge_keys).merge(post_2, on=merge_keys)

# Response_x = Pre, Response_y = Post_1, Response = Post_2 after successive merges
delta_p1 = merged["Response_y"] - merged["Response_x"]
delta_p2 = merged["Response"]   - merged["Response_x"]

base = merged[merge_keys].copy()
delta_p1_df = base.copy(); delta_p1_df["delta_accuracy"] = delta_p1; delta_p1_df["Session"] = "P1"
delta_p2_df = base.copy(); delta_p2_df["delta_accuracy"] = delta_p2; delta_p2_df["Session"] = "P2"

delta_final = pd.concat([delta_p1_df, delta_p2_df], ignore_index=True)
delta_final = delta_final.sort_values(
    by="Subject", key=lambda x: x.str.replace("S", "").astype(int)
).reset_index(drop=True)
delta_final["Collection"] = delta_final["Subject"].map(
    lambda x: "1" if x in COHORT_RIGHT_MONTAGE else "2"
)

# -----------------------------------------------------------------------------
# 5. Trial-count QA table
# -----------------------------------------------------------------------------
qa_rows = []
for subj in long_trials["Subject"].unique():
    for stim in CONDITIONS:
        for sess in ["Pre", "Post_1", "Post_2"]:
            n = long_trials.query(
                "Subject == @subj and Stimulation == @stim and Session == @sess"
            ).shape[0]
            qa_rows.append({"Subject": subj, "Stimulation": stim,
                            "Session": sess, "Trials": n})
qa_df = pd.DataFrame(qa_rows)

# -----------------------------------------------------------------------------
# 6. Save
# -----------------------------------------------------------------------------
long_trials.to_csv(OUT_ROOT / "long_format_single_trial.csv", index=False)
long_collapsed.to_csv(OUT_ROOT / "long_format_collapsed.csv", index=False)
delta_final.to_csv(OUT_ROOT / "delta_long_format_averaged.csv", index=False)
qa_df.to_csv(OUT_ROOT / "Trials.csv", index=False)

print(f"Wrote {len(long_trials)} single trials across {long_trials['Subject'].nunique()} subjects")
print(f"Output written to: {OUT_ROOT.resolve()}")
