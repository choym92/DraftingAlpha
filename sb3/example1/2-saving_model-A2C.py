import gymnasium as gym
from stable_baselines3 import PPO, A2C
import time
import os


models = "A2C"
models_dir = f"models/{models}-{int(time.time())}"
logdir = f"logs/{models}-{int(time.time())}"
ITER_COUNT = 100

if not os.path.exists(models_dir):
    os.makedirs(models_dir)

if not os.path.exists(logdir):
    os.makedirs(logdir)

# Create the environment
env = gym.make("LunarLander-v3")
obs, info = env.reset()  # Unpack the reset output (obs, info)

model = A2C("MlpPolicy", env, verbose=1, tensorboard_log=logdir)

TIMESTEPS = 100000

for i in range(1, ITER_COUNT):
    model.learn(total_timesteps=TIMESTEPS, reset_num_timesteps=False, tb_log_name=f"{models}-{TIMESTEPS}")
    model.save(f"{models_dir}/{TIMESTEPS*i}")

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
