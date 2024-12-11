import os
import pandas as pd
import random

# Folder containing the ADP files
adp_folder = 'adp'

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

# Initialize the draft simulation
def simulate_draft(trial_number):
    # Load the ADP data
    adp_df = load_adp_file()

    # Filter and sort by 'FPPRAVG'
    adp_df = adp_df[['player_name', 'player_id', 'FPPRAVG', 'POSITION', 'year']]
    adp_df = adp_df.sort_values(by='FPPRAVG', ascending=True).reset_index(drop=True)

    # Initialize draft variables
    num_managers = 8
    num_rounds = 16
    draft_order = list(range(1, num_managers + 1))
    random.shuffle(draft_order)  # Randomize the draft order
    results = []

    # Track required positions for each manager (1 QB, 1 K, 1 DST)
    required_positions = {f"Team_{i}": {"QB": 1, "K": 1, "DST": 1} for i in range(1, num_managers + 1)}
    drafted_players = {f"Team_{i}": {"QB": 0, "K": 0, "DST": 0} for i in range(1, num_managers + 1)} # Track drafted players

    # Simulate the draft
    for round_num in range(1, num_rounds + 1):
        # Alternate between ascending and descending order for snake draft
        current_order = draft_order if round_num % 2 != 0 else draft_order[::-1]

        for pick, manager in enumerate(current_order, start=1):
            team_name = f"Team_{manager}"

            if adp_df.empty:
                print("No players left to draft!")
                break

            # Check which positions are still needed for the team
            remaining_required_positions = {pos for pos, count in drafted_players[team_name].items() if count == 0}

            # From round 14 onwards, if any positions are required, draft from them
            if round_num >= num_rounds - 3:
                # Check if the team still needs positions to be filled
                if remaining_required_positions:
                    # Filter players for the remaining required positions
                    available_players = adp_df[adp_df['POSITION'].isin(remaining_required_positions)]

                    if not available_players.empty:
                        # Select the lowest FPPRAVG player from the remaining required positions
                        selected_player = available_players.iloc[0]
                    else:
                        # If no player for the required position is left, pick the lowest FPPRAVG player
                        selected_player = adp_df.iloc[0]
                else:
                    # If no remaining required positions, pick the lowest FPPRAVG player
                    selected_player = adp_df.iloc[0]
            else:
                # In earlier rounds, select based on lowest FPPRAVG (no position constraints)
                selected_player = adp_df.iloc[0]

            # Record the pick
            results.append({
                'trial_number': trial_number,
                'round': round_num,
                'pick': pick,
                'player_name': selected_player['player_name'],
                'player_id': selected_player['player_id'],
                'fppravg': selected_player['FPPRAVG'],
                'position': selected_player['POSITION'],
                'team_name': team_name,
                'year': selected_player['year']
            })

            # Remove the selected player from the pool
            adp_df = adp_df[adp_df['player_id'] != selected_player['player_id']].reset_index(drop=True)

            # Update the drafted positions for the team
            drafted_positions = drafted_players[team_name]
            if selected_player['POSITION'] in drafted_positions:
                drafted_positions[selected_player['POSITION']] += 1

    return results

# Run the simulation 10 times
all_results = []
for trial in range(1, 11):
    all_results.extend(simulate_draft(trial))

# Save all results to a single CSV file
results_df = pd.DataFrame(all_results)
output_file = os.path.join(adp_folder, 'draft_results.csv')
results_df.to_csv(output_file, index=False)
print(f"Draft results for all trials saved to {output_file}")
