# RL-New Training Studio

A desktop viewer of the existing environment and tabular Q-learning agent.
It uses the actual network and OD CSVs; the graph is schematic, not geographical.

## Start

From the repository root, use the same Python environment as training:

```powershell
python -m pip install -r requirements.txt
python -m transit_rl.visualizer
```

Tkinter is included in standard Windows Python installations. NumPy is required.
SciPy is recommended so route matching uses the same Hungarian algorithm as normal
training. Without SciPy the model's existing greedy fallback is used.

Double-click `Open Training Studio.cmd` to launch it. The launcher uses the dedicated
`.venv-visualizer` environment when available, then the repository's Windows `venv`,
and otherwise your default Python. It never installs packages automatically.

The dedicated environment has been set up on this PC with NumPy and SciPy. To
recreate it on another Windows PC:

```powershell
python -m venv .venv-visualizer
.\.venv-visualizer\Scripts\python.exe -m pip install numpy scipy
```

## First demonstration

1. Press **Step action** a few times. The highlighted stop is part of the action;
   dashed amber segments are the route under construction.
2. Press **Play**. Change the speed, then **Pause** to inspect the action panel.
3. **Next hour** runs to a completed hourly plan and pauses there.
4. Select a route in the route table to isolate it. **Show all routes** restores
   all overlays. Drag stops to rearrange the schematic without changing the model.
5. **Fast train** runs without deliberate animation delays, refreshing in batches.
   Pause anytime. Graph snapshots add overhead; use the normal training command for
   unattended performance experiments.
6. After an episode completes, **Replay recent episode**, then Play or Step.
   Replay reads snapshots only; it cannot update Q-values or change live RNG state.
7. **Return to live** restores the paused learner. **Greedy evaluation** is available
   between episodes and runs one day with the same learned Q-table and no updates.
   Return to live restores the original training session after evaluation.
8. **Save session** exports curves and recent action snapshots as JSON. It does not
   save a resumable Q-table. The original training/export command is still available.

The viewer stops after 20 episodes by default. To use a different limit, change
**Episodes**, then press **New session** (starts a fresh Q-table), or launch with
`python -m transit_rl.visualizer --episodes 50`. The epsilon schedule always stays
at the default 10,000-episode configuration; shortening the viewing session does
not accelerate exploration decay. Seed is 2024 unless configuration changes.

## Reading the display

- Grey lines are physical links; colours identify committed route indices.
- Dashed amber is a tentative route. Feasible tentative service can affect dense
  rewards before END_ROUTE; the fleet card always counts only committed buses.
- The latest action reward is an RL feedback value; the evaluated plan score is
  a different value. Hour-end corrections can produce rewards without a route edit.
- Action Q-values are from the state **before** the displayed action/update.
- Random exploration versus greedy selection is identified from a copy of the RNG
  state without changing the agent's selection algorithm. Greedy ties remain random.
- At FINISH_PLAN or a forced deadline, the graph shows the finalised hour's plan.
  The following action operates in the next hour.
- Routes marked locked were kept for this hour; they can be edited again next hour.
- Curves show completed episode returns and Q-table state counts. A growing table
  does not by itself demonstrate better service or convergence.

The viewer retains the current and most recent completed episode for bounded
replay storage. It is a local interactive session, not a monitor attached to a
separately running terminal training job. Its evaluation uses the same RNG as the
agent, so evaluation changes subsequent random choices if training is resumed.
Existing training results are not automatically overwritten or reused.
