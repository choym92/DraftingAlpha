import os
import pandas as pd
import random

# Folder containing the ADP files
adp_folder = 'adp'
seasonal_stats_folder = 'seasonalstats'
defensive_stats_folder = 'defensivestats'

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
    num_managers = 8
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

            if adp_df.empty:
                print("No players left to draft!")
                break

            # Determine unmet required positions
            unmet_positions = {pos: count for pos, count in required_positions[team_name].items() if count > 0}
            num_unmet_positions = len(unmet_positions)
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

# Run the simulation 10 times
all_results = []
for trial in range(1, 11):
    all_results.extend(simulate_draft(trial))

# Save all results to a single CSV file
results_df = pd.DataFrame(all_results)
output_file = os.path.join(adp_folder, 'draft_results.csv')
results_df.to_csv(output_file, index=False)
print(f"Draft results for all trials saved to {output_file}")

# Load the draft results file
draft_results_file = os.path.join(adp_folder, 'draft_results.csv')
draft_results_df = pd.read_csv(draft_results_file)

# Ensure the draft results contain the 'year' column
if 'year' not in draft_results_df.columns:
    raise ValueError("'year' column is missing in the draft results file.")

# Initialize the fantasy ranking results
fantasy_ranking = []

# Group by trial and team
for trial, trial_data in draft_results_df.groupby('trial_number'):
    for team, team_data in trial_data.groupby('team_name'):
        # Identify the top players by position
        team_data_sorted = team_data.sort_values(by='fpts', ascending=False)

        # Get the top QB
        top_qbs = team_data_sorted[team_data_sorted['position'] == 'QB']
        QB1 = top_qbs.iloc[0] if not top_qbs.empty else None

        # Get the top 2 RBs
        top_rbs = team_data_sorted[team_data_sorted['position'] == 'RB']
        RB1 = top_rbs.iloc[0] if len(top_rbs) > 0 else None
        RB2 = top_rbs.iloc[1] if len(top_rbs) > 1 else None

        # Get the top 2 WRs
        top_wrs = team_data_sorted[team_data_sorted['position'] == 'WR']
        WR1 = top_wrs.iloc[0] if len(top_wrs) > 0 else None
        WR2 = top_wrs.iloc[1] if len(top_wrs) > 1 else None

        # Get the top TE
        top_tes = team_data_sorted[team_data_sorted['position'] == 'TE']
        TE1 = top_tes.iloc[0] if not top_tes.empty else None

        # Get the top K
        top_ks = team_data_sorted[team_data_sorted['position'] == 'K']
        K1 = top_ks.iloc[0] if not top_ks.empty else None

        # Get the top DST
        top_dsts = team_data_sorted[team_data_sorted['position'] == 'DST']
        DST1 = top_dsts.iloc[0] if not top_dsts.empty else None

        # Get the top Flex (non-QB, non-DST, and not already selected)
        selected_players = {player['player_id'] for player in [QB1, RB1, RB2, WR1, WR2, TE1, K1, DST1] if player is not None}
        top_flex_candidates = team_data_sorted[
            (~team_data_sorted['position'].isin(['QB', 'DST'])) & 
            (~team_data_sorted['player_id'].isin(selected_players))
        ]
        Flex1 = top_flex_candidates.iloc[0] if not top_flex_candidates.empty else None

        # Calculate total fpts
        total_fpts = sum([
            player['fpts'] for player in [QB1, RB1, RB2, WR1, WR2, TE1, K1, DST1, Flex1] if player is not None
        ])

        # Add to the fantasy ranking results
        fantasy_ranking.append({
            'year': team_data['year'].iloc[0],  # Add the year from the current team's data
            'trial_number': trial,
            'team_name': team,
            'QB1': QB1['player_name'] if QB1 is not None else None,
            'QB1_fpts': QB1['fpts'] if QB1 is not None else 0,
            'RB1': RB1['player_name'] if RB1 is not None else None,
            'RB1_fpts': RB1['fpts'] if RB1 is not None else 0,
            'RB2': RB2['player_name'] if RB2 is not None else None,
            'RB2_fpts': RB2['fpts'] if RB2 is not None else 0,
            'WR1': WR1['player_name'] if WR1 is not None else None,
            'WR1_fpts': WR1['fpts'] if WR1 is not None else 0,
            'WR2': WR2['player_name'] if WR2 is not None else None,
            'WR2_fpts': WR2['fpts'] if WR2 is not None else 0,
            'TE1': TE1['player_name'] if TE1 is not None else None,
            'TE1_fpts': TE1['fpts'] if TE1 is not None else 0,
            'K1': K1['player_name'] if K1 is not None else None,
            'K1_fpts': K1['fpts'] if K1 is not None else 0,
            'DST1': DST1['player_name'] if DST1 is not None else None,
            'DST1_fpts': DST1['fpts'] if DST1 is not None else 0,
            'Flex1': Flex1['player_name'] if Flex1 is not None else None,
            'Flex1_fpts': Flex1['fpts'] if Flex1 is not None else 0,
            'total_fpts': total_fpts
        })

# Convert the fantasy ranking to a DataFrame
fantasy_ranking_df = pd.DataFrame(fantasy_ranking)

# Rank the teams by trial based on total_fpts
fantasy_ranking_df['rank'] = fantasy_ranking_df.groupby('trial_number')['total_fpts'].rank(ascending=False).astype(int)

# Save to CSV
fantasy_ranking_file = os.path.join(adp_folder, 'fantasy_ranking.csv')
fantasy_ranking_df.to_csv(fantasy_ranking_file, index=False)
print(f"Fantasy ranking saved to {fantasy_ranking_file}")
