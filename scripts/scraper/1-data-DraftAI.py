import nfl_data_py as nfl
import pandas as pd
import os
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from utility.constants import *

# Create the 'seasonalstats' folder if it doesn't exist
if not os.path.exists(SEASONAL_STATS_DIR):
    print("Seasonal Stats Directory Created.")
    os.makedirs(SEASONAL_STATS_DIR)

# Function to process data for a given year
def process_season_data(year):
    # Load play-by-play data for the given year
    pbp_data = nfl.import_pbp_data([year])

    # Filter the data up to Week 14
    pbp_data = pbp_data[pbp_data['week'] <= 18]

    # Collecting stats for all players
    passing_tds = pbp_data[pbp_data['pass_touchdown'] == 1].groupby(['passer_player_id']).size().reset_index(name='pass_touchdown')
    rushing_tds = pbp_data[pbp_data['rush_touchdown'] == 1].groupby(['rusher_player_id']).size().reset_index(name='rush_touchdown')
    receiving_tds = pbp_data[(pbp_data['touchdown'] == 1) & (pbp_data['pass_touchdown'] == 1)].groupby(['receiver_player_id']).size().reset_index(name='rec_touchdown')
    passing_yards = pbp_data.groupby(['passer_player_id'])['passing_yards'].sum().reset_index()
    rushing_yards = pbp_data.groupby(['rusher_player_id'])['rushing_yards'].sum().reset_index()
    receiving_yards = pbp_data.groupby(['receiver_player_id'])['receiving_yards'].sum().reset_index()
    receptions = pbp_data[pbp_data['complete_pass'] == 1].groupby(['receiver_player_id']).size().reset_index(name='receptions')
    targets = pbp_data[pbp_data['pass_attempt'] == 1].groupby(['receiver_player_id']).size().reset_index(name='targets')
    interceptions = pbp_data.groupby(['passer_player_id'])['interception'].sum().reset_index()

    # Fumble lost calculation using fumbled_1_player_id
    fumble_lost = pbp_data[pbp_data['fumble_lost'] == 1].groupby(['fumbled_1_player_id']).size().reset_index(name='fumble_lost')
    fumble_lost = fumble_lost.rename(columns={'fumbled_1_player_id': 'player_id'})  # Consistent naming
    
    # Field goals (specific to kickers)
    field_goals = pbp_data[pbp_data['play_type'] == 'field_goal'].copy()
    field_goals['yardage_range'] = pd.cut(
        field_goals['kick_distance'],
        bins=[0, 39, 49, 59, float('inf')],
        labels=['0-39', '40-49', '50-59', '60+']
    )
    fg_made = field_goals[field_goals['field_goal_result'] == 'made'].groupby(['kicker_player_id', 'yardage_range']).size().unstack(fill_value=0)
    fg_made.columns = [f"fg_made_{col}" for col in fg_made.columns]
    fg_missed = field_goals[field_goals['field_goal_result'].isin(['missed', 'blocked'])].groupby(['kicker_player_id', 'yardage_range']).size().unstack(fill_value=0)
    fg_missed.columns = [f"fg_missed_{col}" for col in fg_missed.columns]

    # PAT stats
    pat = pbp_data[pbp_data['play_type'] == 'extra_point']
    pat_made = pat[pat['extra_point_result'] == 'good'].groupby(['kicker_player_id']).size().reset_index(name='pat_made')
    pat_missed = pat[pat['extra_point_result'].isin(['failed', 'blocked'])].groupby(['kicker_player_id']).size().reset_index(name='pat_missed')

    # Kick and punt return touchdowns
    kick_return_tds = pbp_data[(pbp_data['play_type'] == 'kickoff') & (pbp_data['return_touchdown'] == 1)].groupby(['kickoff_returner_player_id']).size().reset_index(name='kick_return_touchdown')
    punt_return_tds = pbp_data[(pbp_data['play_type'] == 'punt') & (pbp_data['return_touchdown'] == 1)].groupby(['punt_returner_player_id']).size().reset_index(name='punt_return_touchdown')

    # Successful two-point conversions
    two_point_conversions = pbp_data[pbp_data['two_point_attempt'] == 1]
    two_point_successful = two_point_conversions[two_point_conversions['two_point_conv_result'] == 'success']
    two_point_successful = two_point_successful.drop_duplicates(subset=['game_id', 'play_id'])

    two_point_pass = two_point_successful[(two_point_successful['passer_player_id'].notna())]
    two_point_pass = two_point_pass.groupby(['passer_player_id']).size().reset_index(name='two_point_pass_success')
    two_point_rush = two_point_successful[(two_point_successful['rusher_player_id'].notna())]
    two_point_rush = two_point_rush.groupby(['rusher_player_id']).size().reset_index(name='two_point_rush_success')
    two_point_rec = two_point_successful[(two_point_successful['receiver_player_id'].notna())]
    two_point_rec = two_point_rec.groupby(['receiver_player_id']).size().reset_index(name='two_point_rec_success')

    # Combine all stats for players
    players = pd.concat([
        passing_tds.rename(columns={'passer_player_id': 'player_id'}),
        rushing_tds.rename(columns={'rusher_player_id': 'player_id'}),
        receiving_tds.rename(columns={'receiver_player_id': 'player_id'}),
        passing_yards.rename(columns={'passer_player_id': 'player_id'}),
        rushing_yards.rename(columns={'rusher_player_id': 'player_id'}),
        receiving_yards.rename(columns={'receiver_player_id': 'player_id'}),
        receptions.rename(columns={'receiver_player_id': 'player_id'}),
        targets.rename(columns={'receiver_player_id': 'player_id'}),
        interceptions.rename(columns={'passer_player_id': 'player_id'}),
        fumble_lost,  # Already renamed to player_id
        two_point_pass.rename(columns={'passer_player_id': 'player_id'}),
        two_point_rush.rename(columns={'rusher_player_id': 'player_id'}),
        two_point_rec.rename(columns={'receiver_player_id': 'player_id'}),
        kick_return_tds.rename(columns={'kickoff_returner_player_id': 'player_id'}),
        punt_return_tds.rename(columns={'punt_returner_player_id': 'player_id'}),
        fg_made.reset_index().rename(columns={'kicker_player_id': 'player_id'}),  # Add fg_made columns
        fg_missed.reset_index().rename(columns={'kicker_player_id': 'player_id'}),  # Add fg_missed columns
        pat_made.rename(columns={'kicker_player_id': 'player_id'}),
        pat_missed.rename(columns={'kicker_player_id': 'player_id'})                               
    ], ignore_index=True)

    # Group by player_id to aggregate all stats
    final_stats = players.groupby('player_id', as_index=False).sum(numeric_only=True)
    final_stats.fillna(0, inplace=True)

    # Calculate fantasy points
    final_stats['fppr'] = (
        0.04 * final_stats['passing_yards'] +
        4 * final_stats['pass_touchdown'] -
        2 * final_stats['interception'] +
        0.1 * final_stats['rushing_yards'] +
        6 * final_stats['rush_touchdown'] +
        0.1 * final_stats['receiving_yards'] +
        1 * final_stats['receptions'] +
        6 * final_stats['rec_touchdown'] +
        1 * final_stats['pat_made'] +
        3 * final_stats.get('fg_made_0-39', 0) +
        4 * final_stats.get('fg_made_40-49', 0) +
        5 * final_stats.get('fg_made_50-59', 0) +
        6 * final_stats.get('fg_made_60+', 0) -
        1 * final_stats.get('fg_missed_0-39', 0) -
        1 * final_stats.get('fg_missed_40-49', 0) -
        1 * final_stats.get('fg_missed_50-59', 0) -
        1 * final_stats.get('fg_missed_60+', 0) +
        6 * final_stats.get('kick_return_touchdown', 0) +
        6 * final_stats.get('punt_return_touchdown', 0) -
        2 * final_stats['fumble_lost'] +
        2 * (
            final_stats.get('two_point_pass_success', 0) +
            final_stats.get('two_point_rush_success', 0) +
            final_stats.get('two_point_rec_success', 0)
        )
    )

    # Convert to numeric to ensure it is treated as a numeric column
    final_stats['fppr'] = pd.to_numeric(final_stats['fppr'], errors='coerce')

    # Calculate fantasy points
    final_stats['hppr'] = (
        0.04 * final_stats['passing_yards'] +
        4 * final_stats['pass_touchdown'] -
        2 * final_stats['interception'] +
        0.1 * final_stats['rushing_yards'] +
        6 * final_stats['rush_touchdown'] +
        0.1 * final_stats['receiving_yards'] +
        0.5 * final_stats['receptions'] +
        6 * final_stats['rec_touchdown'] +
        1 * final_stats['pat_made'] +
        3 * final_stats.get('fg_made_0-39', 0) +
        4 * final_stats.get('fg_made_40-49', 0) +
        5 * final_stats.get('fg_made_50-59', 0) +
        6 * final_stats.get('fg_made_60+', 0) -
        1 * final_stats.get('fg_missed_0-39', 0) -
        1 * final_stats.get('fg_missed_40-49', 0) -
        1 * final_stats.get('fg_missed_50-59', 0) -
        1 * final_stats.get('fg_missed_60+', 0) +
        6 * final_stats.get('kick_return_touchdown', 0) +
        6 * final_stats.get('punt_return_touchdown', 0) -
        2 * final_stats['fumble_lost'] +
        2 * (
            final_stats.get('two_point_pass_success', 0) +
            final_stats.get('two_point_rush_success', 0) +
            final_stats.get('two_point_rec_success', 0)
        )
    )

    # Convert to numeric to ensure it is treated as a numeric column
    final_stats['hppr'] = pd.to_numeric(final_stats['hppr'], errors='coerce')

    # Add player names
    passer_names = pbp_data[['passer_player_id', 'passer_player_name']].drop_duplicates()
    rusher_names = pbp_data[['rusher_player_id', 'rusher_player_name']].drop_duplicates()
    receiver_names = pbp_data[['receiver_player_id', 'receiver_player_name']].drop_duplicates()
    kicker_names = pbp_data[['kicker_player_id', 'kicker_player_name']].drop_duplicates()

    all_player_names = pd.concat([
        passer_names.rename(columns={'passer_player_id': 'player_id', 'passer_player_name': 'player_name'}),
        rusher_names.rename(columns={'rusher_player_id': 'player_id', 'rusher_player_name': 'player_name'}),
        receiver_names.rename(columns={'receiver_player_id': 'player_id', 'receiver_player_name': 'player_name'}),
        kicker_names.rename(columns={'kicker_player_id': 'player_id', 'kicker_player_name': 'player_name'})
    ], ignore_index=True).drop_duplicates(subset=['player_id'])

    # Merge names with stats
    final_stats = pd.merge(final_stats, all_player_names, on='player_id', how='left')
    cols = ['player_id', 'player_name'] + [col for col in final_stats.columns if col not in ['player_id', 'player_name']]
    final_stats = final_stats[cols]

    roster_df = pd.read_csv(ROSTER_DIR)
    final_stats = pd.merge(final_stats, roster_df[['player_id','position']], on='player_id', how='left')

    # Save the stats to a CSV file for this season
    file_path = SEASONAL_STATS_DIR / f'player_stats_{year}.csv'
    final_stats.to_csv(file_path, index=False)
    print(f"Stats for {year} saved to '{file_path}'")

# Loop through years 2018 to 2023 and process data
for year in range(YEAR_BEGINNING, YEAR_END):
    process_season_data(year)