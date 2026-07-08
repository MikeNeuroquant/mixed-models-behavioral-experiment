# Install R packages used by the analysis and plotting scripts.
# Run once from the repo root:  Rscript requirements/R_packages.R

pkgs <- c(
  "dplyr", "tidyverse", "readxl",
  "lme4", "car", "emmeans",
  "rstatix", "DHARMa", "performance", "lmtest",
  "ggsignif", "gridExtra"
)

to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install) > 0) {
  install.packages(to_install, repos = "https://cloud.r-project.org")
}
