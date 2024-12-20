import nfl_data_py as nfl
import pandas as pd
from utility.constants import ROSTER_DIR, YEAR_BEGINNING, YEAR_END


# Step 1: Import rosters for the range of seasons
seasons = list(range(YEAR_BEGINNING, YEAR_END + 1))  # Create a list for seasons 2018 to 2023

rosters = nfl.import_seasonal_rosters(seasons)

# Step 2: Remove duplicates by 'player_id'
unique_rosters = rosters.drop_duplicates(subset='player_id')

# Step 3: Drop the 'season' column
cleaned_rosters = unique_rosters.drop(columns=['season'])

# Save to CSV if needed
cleaned_rosters.to_csv(ROSTER_DIR, index=False)