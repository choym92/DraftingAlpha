import nfl_data_py as nfl
import pandas as pd

# Step 1: Import rosters for the range of seasons
seasons = list(range(2018, 2024))  # Create a list for seasons 2018 to 2023
rosters = nfl.import_seasonal_rosters(seasons)

# Step 2: Remove duplicates by 'player_id'
unique_rosters = rosters.drop_duplicates(subset='player_id')

# Step 3: Drop the 'season' column
cleaned_rosters = unique_rosters.drop(columns=['season'])

# Display the result
print(cleaned_rosters.head())

# Save to CSV if needed
cleaned_rosters.to_csv('nfl_rosters_2018_to_2023.csv', index=False)