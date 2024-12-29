import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

import nfl_data_py as nfl
import pandas as pd
import os

from utility.constants import *


# Create a folder to save defensive stats
if not os.path.exists(DEFENSIVE_STATS_DIR):
    print("Defensive Stats Directory Created.")
    os.makedirs(DEFENSIVE_STATS_DIR)

def calculate_seasonal_defensive_stats_with_points_allowed_and_buckets(year):
    # Load play-by-play data for the given year
    pbp_data = nfl.import_pbp_data([year])

    # Filter data to include only Weeks 1 through 14
    pbp_data = pbp_data[(pbp_data['week'] >= 1) & (pbp_data['week'] <= 14)]

    # Initialize PA column
    pbp_data['PA'] = 0

    # Assign points for field goals, extra points, two-point conversions, and offensive touchdowns
    pbp_data.loc[pbp_data['field_goal_result'] == 'made', 'PA'] += 3  # Field goals
    pbp_data.loc[pbp_data['extra_point_result'] == 'good', 'PA'] += 1  # Extra points
    pbp_data.loc[pbp_data['two_point_conv_result'] == 'success', 'PA'] += 2  # Two-point conversions

    # Case 1: td_team == 'posteam' -> PA for `defteam`
    pa_tds_posteam = pbp_data[
        (pbp_data['td_team'] == pbp_data['posteam'])
    ].groupby(['season', 'week', 'defteam']).size().reset_index(name='pa_tds')

    # Case 2: td_team == 'defteam' -> PA for `posteam`
    pa_tds_defteam = pbp_data[
        (pbp_data['td_team'] == pbp_data['defteam']) &
        (pbp_data['return_touchdown'] == 0)
    ].groupby(['season', 'week', 'posteam']).size().reset_index(name='pa_tds')

    # Rename columns for consistency
    pa_tds_posteam.rename(columns={'defteam': 'pa_team'}, inplace=True)
    pa_tds_defteam.rename(columns={'posteam': 'pa_team'}, inplace=True)

    # Combine the two cases and aggregate `pa_tds`
    pa_tds_combined = pd.concat([pa_tds_posteam, pa_tds_defteam], ignore_index=True)
    pa_tds_combined = pa_tds_combined.groupby(['season', 'week', 'pa_team'])['pa_tds'].sum().reset_index()

    pbp_data['d_td'] = 0

    d_td_defteam = pbp_data[
        (pbp_data['td_team'] == pbp_data['defteam']) &
        (pbp_data['play_type'] != 'kickoff')
    ].groupby(['season', 'week', 'defteam']).size().reset_index(name='d_td')

    d_td_defteam.rename(columns={'defteam': 'pa_team'}, inplace=True)

    d_td_posteam = pbp_data[
        (pbp_data['td_team'] == pbp_data['posteam']) &
        (pbp_data['play_type'] == 'kickoff')
    ].groupby(['season', 'week', 'posteam']).size().reset_index(name='d_td')

    d_td_posteam.rename(columns={'posteam': 'pa_team'}, inplace=True)

    d_td_combined = pd.concat([d_td_posteam, d_td_defteam], ignore_index=True)
    d_td_combined = d_td_combined.groupby(['season', 'week', 'pa_team'])['d_td'].sum().reset_index()

    pbp_data['fr'] = 0
    
    fr_mask = pbp_data[(pbp_data['fumble_lost'] == 1)].groupby(['season', 'week', 'fumble_recovery_1_team']).size().reset_index(name='fr')
    fr_mask.rename(columns={'fumble_recovery_1_team': 'pa_team'}, inplace=True)

    # Group defensive stats by `defteam`
    weekly_defensive_stats = pbp_data.groupby(['season', 'week', 'defteam']).agg(
        ya=('yards_gained', 'sum'),
        int=('interception', 'sum'),
        sk=('sack', 'sum'),
        sfty=('safety', 'sum'),
        pbk=('punt_blocked', 'sum'),
        pa=('PA', 'sum')
    ).reset_index()

    # Rename `defteam` to `pa_team` and merge with `pa_tds`
    weekly_defensive_stats.rename(columns={'defteam': 'pa_team'}, inplace=True)
    
    weekly_defensive_stats = weekly_defensive_stats.merge(pa_tds_combined, on=['season', 'week', 'pa_team'], how='left')
    weekly_defensive_stats = weekly_defensive_stats.merge(fr_mask, on=['season', 'week', 'pa_team'], how='left')
    weekly_defensive_stats['fr'] = weekly_defensive_stats['fr'].fillna(0)

    # Add `pa_tds` to `PA` (6 points per touchdown)
    weekly_defensive_stats['pa_tds'] = weekly_defensive_stats['pa_tds'].fillna(0)
    weekly_defensive_stats['pa'] += 6 * weekly_defensive_stats['pa_tds']

    weekly_defensive_stats = weekly_defensive_stats.merge(d_td_combined, on=['season', 'week', 'pa_team'], how='left')
    weekly_defensive_stats['d_td'] = weekly_defensive_stats['d_td'].fillna(0)

    # Extract blocked kicks (blkk) – both field goal and PAT blocks
    blocked_kicks = pbp_data[
        (pbp_data['play_type'] == 'field_goal') &  # Field goal play type
        (pbp_data['field_goal_result'] == 'blocked')  # Field goal result is blocked
    ]
    pat_blocks = pbp_data[
        (pbp_data['play_type'] == 'extra_point') &  # PAT attempts are also treated as kickoff plays
        (pbp_data['extra_point_result'] == 'blocked')  # PAT result is blocked
    ]
    
    blocked_kicks_count = pd.concat([blocked_kicks, pat_blocks]).groupby(['season', 'week', 'defteam']).size().reset_index(name='blkk')
    blocked_kicks_count.rename(columns={'defteam': 'pa_team'}, inplace=True)

    # Merge the additional stats (FRTD, INTTD, blkk) into the weekly defensive stats
    weekly_defensive_stats = weekly_defensive_stats.merge(blocked_kicks_count, on=['season', 'week', 'pa_team'], how='left')

    # Fill NaN values with 0 (in case no fumble TDs, interception TDs, or blocked kicks occurred)
    weekly_defensive_stats['blkk'].fillna(0, inplace=True)

    # Create yardage bucket indicator columns
    ya_bins = [0, 99, 199, 299, 349, 399, 449, 499, 549, float('inf')]
    ya_labels = ['YA100', 'YA199', 'YA299', 'YA349', 'YA399', 'YA449', 'YA499', 'YA549', 'YA550']
    weekly_defensive_stats['ya_bucket'] = pd.cut(weekly_defensive_stats['ya'], bins=ya_bins, labels=ya_labels, right=True)
    for label in ya_labels:
        weekly_defensive_stats[label] = (weekly_defensive_stats['ya_bucket'] == label).astype(int)
    weekly_defensive_stats.drop(columns=['ya_bucket'], inplace=True)

    # Create points allowed (PA) bucket indicator columns
    pa_bins = [-0.01, 0.99, 6.99, 13.99, 17.99, 27.99, 34.99, 45.99, float('inf')]
    pa_labels = ['PA0', 'PA1', 'PA7', 'PA14', 'PA18', 'PA28', 'PA35', 'PA46']
    weekly_defensive_stats['pa_bucket'] = pd.cut(weekly_defensive_stats['pa'], bins=pa_bins, labels=pa_labels, right=True)
    for label in pa_labels:
        weekly_defensive_stats[label] = (weekly_defensive_stats['pa_bucket'] == label).astype(int)
    weekly_defensive_stats.drop(columns=['pa_bucket'], inplace=True)

    # Calculating fantasy points (weekly)
    weekly_defensive_stats['fpts'] = (
        6 * weekly_defensive_stats['d_td'] +
        1 * weekly_defensive_stats['sk'] +
        2 * weekly_defensive_stats['pbk'] +
        2 * weekly_defensive_stats['blkk'] +
        2 * weekly_defensive_stats['int'] +
        2 * weekly_defensive_stats['fr'] +
        2 * weekly_defensive_stats['sfty'] +
        5 * weekly_defensive_stats['PA0'] +
        4 * weekly_defensive_stats['PA1'] +
        3 * weekly_defensive_stats['PA7'] +
        1 * weekly_defensive_stats['PA14'] +
        0 * weekly_defensive_stats['PA18'] -
        1 * weekly_defensive_stats['PA28'] -
        3 * weekly_defensive_stats['PA35'] -
        5 * weekly_defensive_stats['PA46'] +
        5 * weekly_defensive_stats['YA100'] +
        3 * weekly_defensive_stats['YA199'] +
        2 * weekly_defensive_stats['YA299'] +
        0 * weekly_defensive_stats['YA349'] -
        1 * weekly_defensive_stats['YA399'] -
        3 * weekly_defensive_stats['YA449'] -
        5 * weekly_defensive_stats['YA499'] -
        6 * weekly_defensive_stats['YA549'] -
        7 * weekly_defensive_stats['YA550']
    )
    
    # Sum weekly bucket indicators across the season
    seasonal_defensive_stats = weekly_defensive_stats.groupby(['season', 'pa_team']).agg(
        d_td=('d_td', 'sum'),
        int=('int', 'sum'),
        fr=('fr', 'sum'),
        sk=('sk', 'sum'),
        sfty=('sfty', 'sum'),
        pbk=('pbk', 'sum'),
        blkk=('blkk', 'sum'),
        fpts=('fpts', 'sum'),
        **{label: (label, 'sum') for label in ya_labels},  # Sum YA buckets
        **{label: (label, 'sum') for label in pa_labels}   # Sum PA buckets
    ).reset_index()

    # Calculating fantasy points

    # Save the season-long stats to a CSV file
    weekly_file_path = DEFENSIVE_STATS_DIR / f'weekly_defensive_stats_{year}.csv'
    weekly_defensive_stats.to_csv(weekly_file_path, index=False)
    print(f"Weekly defensive stats for {year} saved to '{weekly_file_path}'")
    seasonal_file_path = DEFENSIVE_STATS_DIR / f'seasonal_defensive_stats_{year}.csv'
    seasonal_defensive_stats.to_csv(seasonal_file_path, index=False)
    print(f"Seasonal defensive stats for {year} saved to '{seasonal_file_path}'")

# Process data for each season from 2018 to 2024
for year in range(YEAR_BEGINNING, YEAR_END):
    calculate_seasonal_defensive_stats_with_points_allowed_and_buckets(year)
