import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np
import random
from pathlib import Path
import os
import re


# Utility Functions
def load_file(folder: Path, filename: str) -> pd.DataFrame:
    """Load a CSV file."""
    file_path = folder / filename
    if file_path.exists():
        return pd.read_csv(file_path)
    raise FileNotFoundError(f"File {filename} not found in {folder}")


def extract_years(folder: Path) -> list:
    """Extract available years from filenames in the folder."""
    return sorted(
        int(re.match(r"^\d{4}", file.name).group())
        for file in folder.glob("*.csv")
        if re.match(r"^\d{4}", file.name)
    )


def load_adp_data(adp_dir: Path) -> pd.DataFrame:
    """Load a random ADP file."""
    year = random.choice(extract_years(adp_dir))
    return load_file(adp_dir, f"{year}ADP.csv")


def load_seasonal_stats(stats_dir: Path, year: int) -> pd.DataFrame:
    """Load seasonal player stats for a given year."""
    return load_file(stats_dir, f"player_stats_{year}.csv")


def load_defensive_stats(stats_dir: Path, year: int) -> pd.DataFrame:
    """Load defensive team stats for a given year."""
    return load_file(stats_dir, f"seasonal_defensive_stats_{year}.csv")


def merge_stats(adp: pd.DataFrame, offensive: pd.DataFrame, defensive: pd.DataFrame) -> pd.DataFrame:
    """Merge ADP with offensive and defensive stats."""
    adp = adp.merge(offensive[["player_id", "fppr"]], on="player_id", how="left")
    defensive = defensive.rename(columns={"pa_team": "player_id", "fpts": "def_fpts"})
    adp = adp.merge(defensive[["player_id", "def_fpts"]], on="player_id", how="left")
    adp["fpts"] = adp.apply(
        lambda row: row["def_fpts"] if row["POSITION"] == "DST" else row["fppr"], axis=1
    )
    return adp.sort_values(by="fpts", ascending=False).reset_index(drop=True)


# Draft Environment
class DraftEnvironment(gym.Env):
    def __init__(self, adp_dir: Path, stats_dir: Path, num_teams=10, roster_size=8):
        super(DraftEnvironment, self).__init__()

        # Initialize draft data
        self.adp_dir = adp_dir
        self.stats_dir = stats_dir
        self.num_teams = num_teams
        self.roster_size = roster_size
        self.total_picks = num_teams * roster_size
        self.agent_team_id = 1

        # Load and process data
        self.adp_data = load_adp_data(adp_dir)
        self.year = self.adp_data["year"].iloc[0]
        self.offensive_stats = load_seasonal_stats(stats_dir, self.year)
        self.defensive_stats = load_defensive_stats(stats_dir, self.year)
        self.player_pool = merge_stats(self.adp_data, self.offensive_stats, self.defensive_stats)

        # Action and observation spaces
        self.action_space = spaces.Discrete(len(self.player_pool))
        self.observation_space = spaces.Dict({
            "available_players": spaces.Box(low=0, high=1, shape=(len(self.player_pool),), dtype=np.float32),
            "agent_roster": spaces.Box(low=0, high=1, shape=(roster_size, 4), dtype=np.float32)  # QB, RB, WR, TE
        })

        self.reset()

    def reset(self):
        """Reset the environment at the start of each episode."""
        self.drafted_players = set()
        self.agent_roster = []  # The agent's drafted players
        self.current_pick = 0
        return self._get_observation()

    def _get_observation(self):
        """Return the current observation."""
        available_mask = [
            0 if player["player_id"] in self.drafted_players else 1
            for _, player in self.player_pool.iterrows()
        ]
        roster_counts = [0] * 4  # QB, RB, WR, TE
        for player in self.agent_roster:
            position = player["POSITION"]
            if position == "QB":
                roster_counts[0] += 1
            elif position == "RB":
                roster_counts[1] += 1
            elif position == "WR":
                roster_counts[2] += 1
            elif position == "TE":
                roster_counts[3] += 1

        return {"available_players": np.array(available_mask, dtype=np.float32),
                "agent_roster": np.array(roster_counts, dtype=np.float32)}

    def step(self, action):
        """Execute the agent's pick and simulate opponents' picks."""
        selected_player = self.player_pool.iloc[action]
        self.agent_roster.append(selected_player)
        self.drafted_players.add(selected_player["player_id"])
        reward = selected_player["fpts"]

        # Simulate opponent picks
        for _ in range(self.num_teams - 1):
            available_players = self.player_pool[~self.player_pool["player_id"].isin(self.drafted_players)]
            if not available_players.empty:
                opponent_pick = available_players.sample(1).iloc[0]
                self.drafted_players.add(opponent_pick["player_id"])

        # Update draft state
        self.player_pool = self.player_pool[~self.player_pool["player_id"].isin(self.drafted_players)]
        self.current_pick += 1
        done = self.current_pick >= self.total_picks

        return self._get_observation(), reward, done, {}

    def render(self, mode="human"):
        """Render the agent's current roster."""
        print("Agent's Roster:")
        for player in self.agent_roster:
            print(f"{player['player_name']} - {player['POSITION']} - {player['fpts']} points")


# Main Execution
if __name__ == "__main__":
    # Define data directories
    ADP_DIR = Path("./adp_data")
    STATS_DIR = Path("./stats_data")

    # Initialize the environment
    env = DraftEnvironment(ADP_DIR, STATS_DIR)

    # Test the environment
    from stable_baselines3.common.env_checker import check_env
    check_env(env)

    # Train a PPO agent
    from stable_baselines3 import PPO

    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)

    # Save the model
    model.save("ppo_draft_agent")

    # Simulate a draft
    obs = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs)
        obs, reward, done, _ = env.step(action)
        env.render()
