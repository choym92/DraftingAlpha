# Training PPO for Fantasy Football Draft Strategy

## Key Aspects to Be Aware Of

### 1. Environment Design
- **Observation Space**:
  - Include features that are **generalizable**, not year-specific or overly unique.
  - Core features:
    - Binary availability of players (e.g., `1` for available, `0` for drafted).
    - Agent's roster composition (e.g., counts for QB, RB, WR, TE).
    - Positional scarcity (optional: remaining players per position).
  - Avoid explicit year identifiers or player names.

- **Action Space**:
  - Discrete action space where each action corresponds to drafting a specific player from the available pool.
  - The action space will shrink as players are drafted, so ensure your environment logic handles this dynamically.

- **Reward Function**:
  - Rewards should guide the agent to:
    - Maximize fantasy points for the final team.
    - Balance the roster (e.g., filling required positions).
  - Example Reward:
    ```
    reward = drafted_player_projected_points
    - penalty_for_overdrafting_a_position
    ```

- **Opponents (Rule-Based Drafting)**:
  - Simulate the 11 other members drafting based on ADP with slight randomness.
  - Randomly shuffle the top 5 players in ADP when simulating their picks to add variability.

---

### 2. PPO Basics and Considerations
- **Why PPO?**
  - PPO is stable and efficient for large and dynamic environments like drafts.
  - It balances exploration (trying new picks) and exploitation (sticking to high-reward strategies).

- **Key PPO Hyperparameters**:
  - **Learning Rate**: Start with `3e-4`, adjust based on training progress.
  - **Gamma**: Discount factor, usually `0.99` to focus on long-term rewards (the entire draft result).
  - **Clip Range**: Typically `0.2` to stabilize updates by avoiding overly large policy changes.
  - **Entropy Coefficient**: Encourages exploration, start with `0.01` or similar.

---

### 3. Training Strategies
- **Data Randomization**:
  - Shuffle ADP and draft order between training episodes to simulate diverse scenarios.

- **Validation**:
  - Test the trained agent against unseen years (e.g., train on 2018–2022, validate on 2023).
  - Evaluate generalization by measuring fantasy points across multiple simulated drafts.

- **Reward Tuning**:
  - Iteratively refine the reward function to encourage good drafting behavior.
  - Example:
    - Reward points for drafting high-projected players.
    - Bonus for drafting scarce positions.
    - Penalties for exceeding positional limits or failing to draft required positions.

- **Evaluation Metrics**:
  - Fantasy points for the agent’s final team compared to rule-based drafters.
  - Positional balance of the agent’s roster.

---

### 4. Opponent Simulation
- Opponent logic should reflect realistic drafting behavior:
  - **Base Rule**: Pick players in order of ADP.
  - **Add Randomness**: Randomly choose among the top 5 players in ADP, considering positional needs.
  - **Team Roster Constraints**:
    - Simulate opponents drafting to fill their positional requirements.

---

## Best Practices for Training PPO

### 1. Environment Validation
- Use `stable_baselines3.common.env_checker.check_env` to verify the environment complies with Gymnasium standards.
- Debug the environment by simulating a single episode and printing:
  - Observations.
  - Rewards.
  - Agent’s roster at the end.

---

### 2. Training Pipeline
- **Training Loop**:
  - Train the PPO agent for multiple timesteps (e.g., `1e5–1e6`).
  - Save intermediate models to evaluate performance at different stages.
- **Simulations per Episode**:
  - Run one full draft simulation (rounds = number of teams * roster size) as a single episode.

---

### 3. Reward Engineering
- Test different reward strategies:
  - Fantasy points for the drafted player.
  - Bonus for drafting scarce positions.
  - Penalties for exceeding positional limits or failing to draft required positions.

---

### 4. Regularization
- Use PPO’s built-in entropy bonus to prevent the agent from overfitting or sticking to deterministic strategies.
- Monitor training to ensure the agent doesn’t get stuck in local optima.

---

### 5. Evaluation
- **During Training**:
  - Evaluate after every few thousand timesteps by simulating drafts.
  - Track cumulative rewards and compare the agent’s performance against rule-based opponents.
- **Post-Training**:
  - Simulate hundreds of drafts with randomized settings (e.g., ADP, draft order).
  - Compare the agent’s final fantasy points with those of other teams.

---

## Workflow

### Step 1: Design the Environment
- Create a custom Gym environment for drafting.
- Define:
  - Observation space: Available players, agent’s roster, positional needs.
  - Action space: Player pool indices.
  - Rewards: Fantasy points, balance penalties.

---

### Step 2: Train the PPO Agent
- Use Stable-Baselines3 with the following settings:
  ```python
  from stable_baselines3 import PPO
  model = PPO("MlpPolicy", env, verbose=1, learning_rate=3e-4, gamma=0.99, clip_range=0.2)
  model.learn(total_timesteps=100000)  # Adjust based on draft complexity

### Step 3: Evaluate the Agent

- **Run Simulations**:
  - Evaluate the trained PPO agent by running draft simulations with **unseen draft settings**.
    - Examples: Different years, shuffled ADP distributions, randomized player stats.

- **Compare Performance Against Baseline**:
  - Measure the agent’s performance relative to rule-based drafters.
  - Metrics:
    - Total fantasy points scored by the drafted team.
    - Positional balance (e.g., filling required slots effectively).

---

### Key Challenges

#### Sparse Rewards
- **Problem**:
  - Draft outcomes (fantasy points) are fully realized only at the end of the draft, leading to sparse rewards.
- **Solution**:
  - Use **intermediate rewards** for each pick.
    - Example: Reward the agent based on the projected points of the drafted player.

#### Balancing Exploration and Exploitation
- **Problem**:
  - The agent might overly exploit known strategies or fail to explore diverse ones.
- **Solution**:
  - Adjust **entropy bonuses** in PPO to encourage exploration and ensure the agent doesn’t get stuck in deterministic strategies.

#### Data Variability
- **Problem**:
  - The agent may overfit to specific patterns in the training data (e.g., fixed ADP or player pools).
- **Solution**:
  - Introduce variability in training by:
    - Randomizing ADP orders.
    - Altering player pools.
    - Simulating different opponent behaviors.