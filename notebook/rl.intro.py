# pip install "gym[box2d]"

import gym

env = gym.make("LunarLander-v2", render_mode="human")  # 'human' for on-screen rendering
env.reset()

for _ in range(100):
    env.render()
    action = env.action_space.sample()  # Random action
    env.step(action)

env.close()