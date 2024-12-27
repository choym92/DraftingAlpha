from pathlib import Path

from pathlib import Path

def find_project_root(marker: str = "requirements.txt") -> Path:
    """Find the project root by searching for a marker file."""
    current = Path.cwd()
    for parent in current.parents:
        if (parent / marker).exists():
            return parent
    return current  # Fallback to the current working directory

PROJECT_ROOT = find_project_root()

# Directory Locations
DATA_DIR = PROJECT_ROOT / "src/data"
ADP_DIR = PROJECT_ROOT / "src/data/adp"
SEASONAL_STATS_DIR = PROJECT_ROOT / "src/data/seasonalstats"
DEFENSIVE_STATS_DIR = PROJECT_ROOT / "src/data/defensivestats"
RESULTS_DIR = PROJECT_ROOT / "src/data/results"
ROSTER_DIR = PROJECT_ROOT / "src/data/nfl_rosters.csv"

# Years to pull data from
YEAR_BEGINNING = 2018
YEAR_END = 2023

# Constants for Simulator
NUMBER_OF_TRIALS = 1000
NUM_MANAGERS = 12
TOTAL_NUM_ROUNDS = 16

# Position limits and requirements
POSITION_LIMITS = {"QB": 4, "RB": 8, "WR": 8, "TE": 3, "K": 3, "DST": 3}
REQUIRED_POSITIONS = {"QB": 1, "K": 1, "DST": 1, "RB": 2, "WR": 2, "TE": 1}

# Weighted probabilities for Draft Logic
ROUND_1_3_WEIGHTS = [0.64, 0.20, 0.10, 0.05, 0.01]
ROUND_4_16_WEIGHTS = [0.50, 0.10, 0.10, 0.10, 0.10, 0.10]