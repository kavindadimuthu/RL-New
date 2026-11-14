"""Optional diagnostic: evaluate an empty Q-table, without any learning."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2]))
from transit_rl.experiment.evaluation_comparison import make_config, evaluate
from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.data.network import load_network_from_csv
from transit_rl.data.od_loader import load_od_matrices

cfg = make_config('C_hour_end', num_episodes=300)
network = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional,
                                cfg.input_stop_id_base)
od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                      cfg.num_stops, cfg.od_file_numbers())
agent = QLearningAgent(cfg, 2024)
results = evaluate(agent, cfg, network, od, [6000,6001,6002])
assert not agent.q and not agent.visits
(root/'untrained_evaluation.json').write_text(json.dumps(results,indent=2))
print(json.dumps([dict(seed=r['seed'],reward=r['reward'],served_demand_ratio=r['served_demand_ratio'])
                  for r in results],indent=2))
