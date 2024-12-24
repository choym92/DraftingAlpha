import gymnasium as gym
from stable_baselines3 import PPO, A2C
import os


# Create the environment
env = gym.make("LunarLander-v3", render_mode="human")
obs, info = env.reset()  # Unpack the reset output (obs, info)

models_dir = "models/PPO"
model_path = f"{models_dir}/100000*i.zip"

model = PPO.load(model_path, env=env)


episodes = 10

for ep in range(episodes):
    obs = env.reset()
    done = False

    while not done:

        env.render()
        action = env.action_space.sample()  # Sample a random action
        obs, reward, done, truncated, info = env.step(action)  # Update to include 'truncated'
        # print(reward)
        if done or truncated:  # Check for termination or truncation
            obs, info = env.reset()  # Reset the environment

env.close()
