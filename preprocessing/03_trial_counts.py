"""
03 — Trial-count QA
===================

Compute the average number of trials per subject × session (Pre / Post_1 /
Post_2) and per subject × 10-min bin during isolation, matching the numbers
reported in the Methods section of the paper.

Inputs (from preprocessing 01 and 02):
    - long_format_single_trial.csv
    - all_isolation_time_split_single_trial.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

DERIV = Path("./derivatives")

# -----------------------------------------------------------------------------
# 1. Pre / Post trial counts
# -----------------------------------------------------------------------------
df = pd.read_csv(DERIV / "long_format_single_trial.csv")

counts = (
    df.groupby(["Subject", "Session", "Stimulation"])
      .size()
      .reset_index(name="Trials")
)

for session in ["Pre", "Post_1", "Post_2"]:
    subset = counts.query("Session == @session")["Trials"]
    if not subset.empty:
        print(f"{session:>7}:  mean = {subset.mean():.2f}   sd = {subset.std():.2f}")

# -----------------------------------------------------------------------------
# 2. Isolation trials — total per subject × stimulation
# -----------------------------------------------------------------------------
iso = pd.read_csv(DERIV / "all_isolation_time_split_single_trial.csv")

per_subj_stim = (
    iso.groupby(["Subject", "Stimulation"]).size().reset_index(name="Trials")
)
print("\nIsolation total (per subject × stim):")
print(f"   mean = {per_subj_stim['Trials'].mean():.2f}   "
      f"sd = {per_subj_stim['Trials'].std():.2f}")

# -----------------------------------------------------------------------------
# 3. Isolation trials — per 10-min bin
# -----------------------------------------------------------------------------
per_bin = (
    iso.groupby(["Subject", "Stimulation", "Time Split"]).size().reset_index(name="Trials")
)
print("\nIsolation per 10-min bin (per subject × stim × bin):")
print(f"   mean = {per_bin['Trials'].mean():.2f}   "
      f"sd = {per_bin['Trials'].std():.2f}")
