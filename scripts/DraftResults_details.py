import os
import pandas as pd
import random
import numpy as np

n = 16

# Folder containing the ADP files
results_folder ='results'
adp_folder = 'adp'
seasonal_stats_folder = 'seasonalstats'
defensive_stats_folder = 'defensivestats'

# Load the draft results file
draft_results_file = os.path.join(results_folder, 'draft_results.csv')
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

        # Add to the fantasy ranking results
        def get_fpts(player):
            # Check if the player exists and their fpts value is valid
            if player is not None and not pd.isna(player['fpts']) and player['fpts'] not in ['', 'NA']:
                return player['fpts']
            return 0

        fantasy_ranking.append({
            'year': team_data['year'].iloc[0],
            'trial_number': trial,
            'team_name': team,
            'QB1': QB1['player_name'] if QB1 is not None else None,
            'QB1_fpts': get_fpts(QB1),
            'RB1': RB1['player_name'] if RB1 is not None else None,
            'RB1_fpts': get_fpts(RB1),
            'RB2': RB2['player_name'] if RB2 is not None else None,
            'RB2_fpts': get_fpts(RB2),
            'WR1': WR1['player_name'] if WR1 is not None else None,
            'WR1_fpts': get_fpts(WR1),
            'WR2': WR2['player_name'] if WR2 is not None else None,
            'WR2_fpts': get_fpts(WR2),
            'TE1': TE1['player_name'] if TE1 is not None else None,
            'TE1_fpts': get_fpts(TE1),
            'K1': K1['player_name'] if K1 is not None else None,
            'K1_fpts': get_fpts(K1),
            'DST1': DST1['player_name'] if DST1 is not None else None,
            'DST1_fpts': get_fpts(DST1),
            'Flex1': Flex1['player_name'] if Flex1 is not None else None,
            'Flex1_fpts': get_fpts(Flex1),
        })

# Convert the fantasy ranking to a DataFrame
fantasy_ranking_df = pd.DataFrame(fantasy_ranking)

def load_seasonal_stats(year):
    """Load seasonal stats for the given year."""
    file_name = f"player_stats_{year}.csv"
    file_path = os.path.join(seasonal_stats_folder, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Seasonal stats file not found for year {year}: {file_path}")
    return pd.read_csv(file_path)

def calculate_waiver_points(seasonal_stats_df, position, factor, n):
    """Calculate the waiver points for a specific position.
    """
    position_data = seasonal_stats_df[seasonal_stats_df['position'].str.upper() == position.upper()]
    position_data_sorted = position_data.sort_values(by='fppr', ascending=False)
    threshold_index = int(np.floor(n * factor)) - 1  # Convert to zero-based index
    if threshold_index < len(position_data_sorted):
        return position_data_sorted.iloc[threshold_index]['fppr']
    return 0  # Return 0 if not enough players in the position

# Add waiver columns to fantasy_ranking_df
waiver_columns = ['qb_waiver_fpts', 'wr_waiver_fpts', 'rb_waiver_fpts', 'te_waiver_fpts', 'k_waiver_fpts']
fantasy_ranking_df[waiver_columns] = 0  # Initialize columns

# Process each year
for year in fantasy_ranking_df['year'].unique():
    seasonal_stats_df = load_seasonal_stats(year)

    qb_waiver_fpts = calculate_waiver_points(seasonal_stats_df, 'QB', 1.6, n)
    wr_waiver_fpts = calculate_waiver_points(seasonal_stats_df, 'WR', 3.6, n)
    rb_waiver_fpts = calculate_waiver_points(seasonal_stats_df, 'RB', 3.6, n)
    te_waiver_fpts = calculate_waiver_points(seasonal_stats_df, 'TE', 1.6, n)
    k_waiver_fpts = calculate_waiver_points(seasonal_stats_df, 'K', 1.6, n)

    # Update the corresponding rows in the DataFrame
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'qb_waiver_fpts'] = qb_waiver_fpts
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'wr_waiver_fpts'] = wr_waiver_fpts
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'rb_waiver_fpts'] = rb_waiver_fpts
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'te_waiver_fpts'] = te_waiver_fpts
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'k_waiver_fpts'] = k_waiver_fpts

# Update player fantasy points and names based on waiver points
for index, row in fantasy_ranking_df.iterrows():
    # Update QB1
    if row['qb_waiver_fpts'] > row['QB1_fpts']:
        fantasy_ranking_df.at[index, 'QB1_fpts'] = row['qb_waiver_fpts']
        fantasy_ranking_df.at[index, 'QB1'] = "waiver_qb"

    # Update RB1
    if row['rb_waiver_fpts'] > row['RB1_fpts']:
        fantasy_ranking_df.at[index, 'RB1_fpts'] = row['rb_waiver_fpts']
        fantasy_ranking_df.at[index, 'RB1'] = "waiver_rb"

    # Update RB2
    if row['rb_waiver_fpts'] > row['RB2_fpts']:
        fantasy_ranking_df.at[index, 'RB2_fpts'] = row['rb_waiver_fpts']
        fantasy_ranking_df.at[index, 'RB2'] = "waiver_rb"

    # Update WR1
    if row['wr_waiver_fpts'] > row['WR1_fpts']:
        fantasy_ranking_df.at[index, 'WR1_fpts'] = row['wr_waiver_fpts']
        fantasy_ranking_df.at[index, 'WR1'] = "waiver_wr"

    # Update WR2
    if row['wr_waiver_fpts'] > row['WR2_fpts']:
        fantasy_ranking_df.at[index, 'WR2_fpts'] = row['wr_waiver_fpts']
        fantasy_ranking_df.at[index, 'WR2'] = "waiver_wr"

    # Update TE1
    if row['te_waiver_fpts'] > row['TE1_fpts']:
        fantasy_ranking_df.at[index, 'TE1_fpts'] = row['te_waiver_fpts']
        fantasy_ranking_df.at[index, 'TE1'] = "waiver_te"

    # Update K1
    if row['k_waiver_fpts'] > row['K1_fpts']:
        fantasy_ranking_df.at[index, 'K1_fpts'] = row['k_waiver_fpts']
        fantasy_ranking_df.at[index, 'K1'] = "waiver_k"

def load_defensive_stats(year):
    """Load seasonal defensive stats for the given year."""
    file_name = f"seasonal_defensive_stats_{year}.csv"
    file_path = os.path.join(defensive_stats_folder, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Defensive stats file not found for year {year}: {file_path}")
    return pd.read_csv(file_path)

def calculate_defensive_waiver_points(defensive_stats_df, factor, n):
    """Calculate the waiver points for DST based on fpts."""
    defensive_data_sorted = defensive_stats_df.sort_values(by='fpts', ascending=False)
    threshold_index = int(np.floor(n * factor)) - 1  # Convert to zero-based index
    if threshold_index < len(defensive_data_sorted):
        waiver_point = defensive_data_sorted.iloc[threshold_index]['fpts']
        return waiver_point
    return 0

# Extend the waiver points calculation for each year
for year in fantasy_ranking_df['year'].unique():
    # Load seasonal defensive stats
    defensive_stats_df = load_defensive_stats(year)

    # Calculate DST waiver points
    dst_waiver_fpts = calculate_defensive_waiver_points(defensive_stats_df, 1.6, n)

    # Update the corresponding rows in the DataFrame
    fantasy_ranking_df.loc[fantasy_ranking_df['year'] == year, 'dst_waiver_fpts'] = dst_waiver_fpts

# Update DST1 fantasy points and names based on defensive waiver points
for index, row in fantasy_ranking_df.iterrows():
    # Update DST1
    if row['dst_waiver_fpts'] > row['DST1_fpts']:
        fantasy_ranking_df.at[index, 'DST1_fpts'] = row['dst_waiver_fpts']
        fantasy_ranking_df.at[index, 'DST1'] = "waiver_dst"

# Recalculate total_fpts after applying the rule
fantasy_ranking_df['total_fpts'] = fantasy_ranking_df[['QB1_fpts', 'RB1_fpts', 'RB2_fpts', 'WR1_fpts', 'WR2_fpts', 'TE1_fpts', 'K1_fpts', 'DST1_fpts', 'Flex1_fpts']].sum(axis=1)

# Handle missing or infinite values in 'total_fpts'
fantasy_ranking_df['total_fpts'] = pd.to_numeric(fantasy_ranking_df['total_fpts'], errors='coerce')

# Replace NaN values with 0 (or another default value if desired)
fantasy_ranking_df['total_fpts'].fillna(0, inplace=True)

# Replace infinite values with 0 (or another default value if desired)
fantasy_ranking_df['total_fpts'].replace([float('inf'), -float('inf')], 0, inplace=True)

# Rank the teams by trial based on total_fpts
fantasy_ranking_df['rank'] = fantasy_ranking_df.groupby('trial_number')['total_fpts'].rank(ascending=False).astype(int)

# Save to CSV
fantasy_ranking_file = os.path.join(results_folder, 'fantasy_ranking.csv')
fantasy_ranking_df.to_csv(fantasy_ranking_file, index=False)
print(f"Fantasy ranking saved to {fantasy_ranking_file}")
