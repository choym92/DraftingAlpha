import os
import pandas as pd
import random
import time
from pathlib import Path
import re
from typing import Dict, List
from utility.constants import *


# Utility: Load files
def load_file(folder, filename):
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    raise FileNotFoundError(f"File {filename} not found in folder {folder}")

def extract_years(folder_path: Path) -> List[int]:
    """Extract years from CSV file names."""
    years = [int(re.match(r"^\d{4}", file.name).group()) 
                for file in folder_path.glob("*.csv") if re.match(r"^\d{4}", file.name)]
    return sorted(years)

# Load ADP file
def load_adp_file():
    year = random.choice(extract_years(ADP_DIR))
    file_name = f"{year}ADP.csv"
    adp_df = load_file(ADP_DIR, file_name)
    adp_df['year'] = year   
    return adp_df

# Load stats
def load_seasonal_stats(year):
    return load_file(SEASONAL_STATS_DIR, f"player_stats_{year}.csv")

def load_defensive_stats(year):
    return load_file(DEFENSIVE_STATS_DIR, f"seasonal_defensive_stats_{year}.csv")

# Merge stats into ADP
def merge_stats(adp_df, seasonal_stats_df, defensive_stats_df):
    adp_df = adp_df.merge(
        seasonal_stats_df[["player_id", "fppr"]], on="player_id", how="left"
    )
    defensive_stats_df = defensive_stats_df.rename(columns={"pa_team": "player_id", "fpts": "def_fpts"})
    adp_df = adp_df.merge(
        defensive_stats_df[["player_id", "def_fpts"]], on="player_id", how="left"
    )
    adp_df["fpts"] = adp_df.apply(
        lambda row: row["def_fpts"] if row["POSITION"] == "DST" else row["fppr"], axis=1
    )
    return adp_df

# Select player with weighted probabilities
def select_player_with_weights(players, weights):
    """
    Randomly select a player based on weighted probabilities.
    """
    return random.choices(players.to_dict("records"), weights=weights[:len(players)], k=1)[0]

# Simulate draft
def simulate_draft(trial_number):
    # Load data
    adp_df = load_adp_file()
    year = adp_df['year'].iloc[0]
    seasonal_stats_df = load_seasonal_stats(year)
    defensive_stats_df = load_defensive_stats(year)
    data_df = merge_stats(adp_df, seasonal_stats_df, defensive_stats_df)

    # Sort players by FPPRAVG
    data_df = data_df.sort_values(by="FPPRAVG").reset_index(drop=True)
    
    # Initialize draft setup
    draft_order = list(range(1, NUM_MANAGERS + 1))
    random.shuffle(draft_order)
    results = []
    pick_order = 1

    # Track positions
    required_positions = {f"Team_{i}": STARTER_POSITIONS.copy() for i in range(1, NUM_MANAGERS + 1)}
    team_counts = {f"Team_{i}": STARTER_POSITIONS.copy() for i in range(1, NUM_MANAGERS + 1)}

    # Simulate rounds
    for round_num in range(1, NUM_ROUNDS + 1):
        current_order = draft_order if round_num % 2 != 0 else draft_order[::-1]

        for manager in current_order:
            team_name = f"Team_{manager}"

            # Special rule for Team_1 in rounds 1–3
            if team_name == "Team_1" and round_num <= 3:
                available_rbs = data_df[data_df["POSITION"] == "RB"]
                selected_player = available_rbs.iloc[0] if not available_rbs.empty else data_df.iloc[0]
            else:
                # Select player based on position constraints
                unmet_positions = [pos for pos, count in required_positions[team_name].items() if count > 0]
                available_players = data_df[
                    data_df["POSITION"].apply(lambda pos: team_counts[team_name][pos] < POSITION_LIMITS[pos])
                ]
                if unmet_positions:
                    available_players = available_players[available_players["POSITION"].isin(unmet_positions)]

                # Weighted selection
                if round_num <= 3:
                    top_players = available_players.head(5)
                    selected_player = select_player_with_weights(top_players, ROUND_1_3_WEIGHTS)
                else:
                    top_players = available_players.head(6)
                    selected_player = select_player_with_weights(top_players, ROUND_4_16_WEIGHTS)

            # Update position counts
            position = selected_player["POSITION"]
            team_counts[team_name][position] += 1
            if required_positions[team_name][position] > 0:
                required_positions[team_name][position] -= 1

            # Record pick
            results.append({
                "trial_number": trial_number,
                "round": round_num,
                "overall_pick": pick_order,
                "team_name": team_name,
                "player_name": selected_player["player_name"],
                "player_id": selected_player["player_id"],
                "position": position,
                "fpts": selected_player["fpts"],
                "year": year
            })

            pick_order += 1
            data_df = data_df[data_df["player_id"] != selected_player["player_id"]].reset_index(drop=True)  # Round FFPRAVG to 2 decimal
            data_df["fpts"] = data_df["fpts"].round(2)
    return results

# Main execution
if __name__ == "__main__":
    start_time = time.time()

    all_results = []
    for trial in range(1, NUMBER_OF_TRIALS + 1):
        all_results.extend(simulate_draft(trial))

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results_df = pd.DataFrame(all_results)
    output_file = os.path.join(RESULTS_DIR, "draft_results.csv")
    results_df.to_csv(output_file, index=False)
    print(f"Draft results saved to {output_file}")

    end_time = time.time()
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")