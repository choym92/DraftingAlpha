import os
import pandas as pd
import random
import time

start_time = time.time()

# Set Total number of trial
number_of_trial = 1000

# Folder containing the ADP files
adp_folder = 'adp'
seasonal_stats_folder = 'seasonalstats'
defensive_stats_folder = 'defensivestats'
results_folder = 'results'

# Function to load a random year's ADP file
def load_adp_file():
    year = random.choice([2018, 2019, 2020, 2021, 2022, 2023])
    file_name = f"{year}ADP.csv"
    file_path = os.path.join(adp_folder, file_name)
    if os.path.exists(file_path):
        adp_df = pd.read_csv(file_path)
        adp_df['year'] = year  # Add year column for debugging (not shown to players)
        return adp_df
    else:
        raise FileNotFoundError(f"ADP file for year {year} not found in folder {adp_folder}")

# Function to load seasonal stats file for a given year
def load_seasonal_stats(year):
    file_name = f"player_stats_{year}.csv"
    file_path = os.path.join(seasonal_stats_folder, file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        raise FileNotFoundError(f"Seasonal stats file for year {year} not found in folder {seasonal_stats_folder}")

# Function to load defensive stats file for a given year
def load_defensive_stats(year):
    file_name = f"seasonal_defensive_stats_{year}.csv"
    file_path = os.path.join(defensive_stats_folder, file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        raise FileNotFoundError(f"Defensive stats file for year {year} not found in folder {defensive_stats_folder}")

# Initialize the draft simulation
def simulate_draft(trial_number):
    # Load the ADP data
    adp_df = load_adp_file()

    # Filter and sort by 'FPPRAVG'
    adp_df = adp_df[['player_name', 'player_id', 'FPPRAVG', 'POSITION', 'year']]
    adp_df = adp_df.sort_values(by='FPPRAVG', ascending=True).reset_index(drop=True)

    # Load the seasonal stats and defensive stats for the selected year
    year = adp_df['year'].iloc[0]
    seasonal_stats_df = load_seasonal_stats(year)
    defensive_stats_df = load_defensive_stats(year)

    # Merge FPPR data for non-DST players
    adp_df = pd.merge(
        adp_df,
        seasonal_stats_df[['player_id', 'fppr']],
        on='player_id',
        how='left'
    )

    # Merge fpts for DST players
    defensive_stats_df = defensive_stats_df.rename(columns={'pa_team': 'player_id', 'fpts': 'def_fpts'})
    adp_df = pd.merge(
        adp_df,
        defensive_stats_df[['player_id', 'def_fpts']],
        on='player_id',
        how='left'
    )

    # Assign fpts column based on position
    adp_df['fpts'] = adp_df.apply(
        lambda row: row['def_fpts'] if row['POSITION'] == 'DST' else row['fppr'], axis=1
    )

    # Initialize draft variables
    num_managers = 12
    num_rounds = 16
    draft_order = list(range(1, num_managers + 1))
    random.shuffle(draft_order)  # Randomize the draft order
    results = []

    # Track required positions for each manager (1 QB, 1 K, 1 DST, 2 RB, 2 WR, 1 TE)
    required_positions = {
        f"Team_{i}": {"QB": 1, "K": 1, "DST": 1, "RB": 2, "WR": 2, "TE": 1} for i in range(1, num_managers + 1)
    }

    # Track current position counts for each team
    team_position_counts = {
        f"Team_{i}": {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "K": 0, "DST": 0} for i in range(1, num_managers + 1)
    }

    # Position limits
    position_limits = {"QB": 4, "RB": 8, "WR": 8, "TE": 3, "K": 3, "DST": 3}

    # Simulate the draft
    for round_num in range(1, num_rounds + 1):
    # Alternate between ascending and descending order for snake draft
        current_order = draft_order if round_num % 2 != 0 else draft_order[::-1]

        for pick, manager in enumerate(current_order, start=1):
            team_name = f"Team_{manager}"

            # Check if it's Player 1's pick in round 1, 2, or 3
            if team_name == "Team_1" and round_num <= 3:
                # Force Player 1 to select an RB in rounds 1, 2, and 3
                available_rbs = adp_df[adp_df['POSITION'] == 'RB']
                if not available_rbs.empty:
                    selected_player = available_rbs.sort_values(by='FPPRAVG', ascending=True).iloc[0]
                    team_position_counts[team_name]['RB'] += 1                    
                    if required_positions[team_name]['RB'] > 0:
                        required_positions[team_name]['RB'] -= 1
                else:
                    # If no RBs are left, fallback to the best available player
                    selected_player = adp_df.iloc[0]
                    team_position_counts[team_name][selected_player['POSITION']] += 1
                    if required_positions[team_name][selected_player['POSITION']] > 0:
                        required_positions[team_name][selected_player['POSITION']] -= 1
            else:
                # Normal draft logic for other managers or after round 3 for Player 1
                if adp_df.empty:
                    print("No players left to draft!")
                    break

                # Determine unmet required positions
                unmet_positions = {pos: count for pos, count in required_positions[team_name].items() if count > 0}
                num_unmet_positions = sum(unmet_positions.values())
                rounds_left = num_rounds - round_num + 1

                # Prioritize unmet positions if constraints apply
                if num_unmet_positions > 0 and rounds_left <= num_unmet_positions:
                    # Filter to only players that meet unmet required positions
                    available_players = adp_df[
                        (adp_df['POSITION'].isin(unmet_positions.keys())) &
                        (adp_df['POSITION'].apply(lambda pos: team_position_counts[team_name][pos] < position_limits[pos]))
                    ]
                    if not available_players.empty:
                        # Select the lowest FPPRAVG player from unmet positions
                        selected_player = available_players.iloc[0]
                        required_positions[team_name][selected_player['POSITION']] -= 1
                        team_position_counts[team_name][selected_player['POSITION']] += 1
                    else:
                        # If no players for unmet positions are available, select the lowest overall
                        selected_player = adp_df.iloc[0]
                        team_position_counts[team_name][selected_player['POSITION']] += 1
                        if required_positions[team_name][selected_player['POSITION']] > 0:
                            required_positions[team_name][selected_player['POSITION']] -= 1
                else:
                    # Otherwise, pick the lowest FPPRAVG player within position limits
                    available_players = adp_df[
                        adp_df['POSITION'].apply(lambda pos: team_position_counts[team_name][pos] < position_limits[pos])
                    ]
                    if not available_players.empty:
                        selected_player = available_players.iloc[0]
                        team_position_counts[team_name][selected_player['POSITION']] += 1
                        if required_positions[team_name][selected_player['POSITION']] > 0:
                            required_positions[team_name][selected_player['POSITION']] -= 1
                    else:
                        # Fallback to the lowest overall if no players meet limits
                        selected_player = adp_df.iloc[0]
                        team_position_counts[team_name][selected_player['POSITION']] += 1
                        if required_positions[team_name][selected_player['POSITION']] > 0:
                            required_positions[team_name][selected_player['POSITION']] -= 1

            # Record the pick
            results.append({
                'trial_number': trial_number,
                'round': round_num,
                'pick': pick,
                'player_name': selected_player['player_name'],
                'player_id': selected_player['player_id'],
                'fppravg': selected_player['FPPRAVG'],
                'fpts': selected_player['fpts'],
                'position': selected_player['POSITION'],
                'team_name': team_name,
                'year': selected_player['year']
            })

            # Remove the selected player from the pool
            adp_df = adp_df[adp_df['player_id'] != selected_player['player_id']].reset_index(drop=True)

    return results

# Run the simulation 100 times
all_results = []
for trial in range(1, number_of_trial):
    all_results.extend(simulate_draft(trial))

# Save all results to a single CSV file
results_df = pd.DataFrame(all_results)
output_file = os.path.join(results_folder, 'draft_results.csv')
results_df.to_csv(output_file, index=False)
print(f"Draft results for all trials saved to {output_file}")

end_time = time.time()
elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time} seconds")
