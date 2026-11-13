"""Interactive, local Tk visualizer for the existing transit Q-learning model.

Run from the repository root: python -m transit_rl.visualizer
The viewer does not alter the model, its reward, or existing result files.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .agent.q_learning_agent import QLearningAgent
from .config import ExperimentConfig
from .data.network import load_network_from_csv
from .data.od_loader import load_od_matrices
from .environment.service_plan import RouteService, plan_to_records
from .environment.state import state_to_key
from .environment.transit_environment import TransitEnvironment
from .experiment.trainer import summarise_day


class VisualSession:
    """One learner, stepped using exactly the normal training update order.

    Rendering and replay consume snapshots, never change the learner RNG, and
    do not introduce synthetic actions. Only the current and last completed
    episode are retained, bounding replay storage for long sessions.
    """

    def __init__(self, cfg=None, seed=2024, target=20, network=None, od=None):
        self.cfg = cfg or ExperimentConfig()
        self.cfg.validate()
        self.network = network if network is not None else load_network_from_csv(
            self.cfg.links_path, self.cfg.num_stops, self.cfg.links_are_bidirectional,
            self.cfg.input_stop_id_base)
        od = od if od is not None else load_od_matrices(
            self.cfg.od_dir, self.cfg.od_filename_pattern, self.cfg.num_hours,
            self.cfg.num_stops, self.cfg.od_file_numbers())
        self.env = TransitEnvironment(self.network, od, self.cfg)
        self.agent = QLearningAgent(self.cfg, seed)
        self.target = target
        self.episode = 1
        self.steps = 0
        self.total = 0.0
        self.curves = []
        self.history = []
        self.completed_history = []
        self.last = self.snapshot()

    @property
    def finished(self):
        return len(self.curves) >= self.target

    def snapshot(self, hour=None, plan=None, route=None, evaluation=None):
        env = self.env
        hour = env.hour if hour is None else hour
        plan = env.current_plan if plan is None else plan
        route = env.current_route if route is None else route
        evaluation = evaluation or env.evaluate_plan(plan)
        if isinstance(evaluation, dict):
            metrics = dict(evaluation)
        else:
            metrics = {**evaluation.assignment.metrics(), **evaluation.reward,
                       'total_fleet_used': evaluation.fleet_used}
        return dict(episode=self.episode, hour=hour,
                    clock_hour=self.cfg.od_file_number(hour),
                    plan=plan_to_records(plan), route=list(route),
                    fleet_used=env.fleet.fleet_used(plan), metrics=metrics,
                    epsilon=self.agent.epsilon, steps=self.steps,
                    total=self.total, states=self.agent.num_states,
                    pairs=self.agent.num_state_action_pairs,
                    action='Ready', decision='Waiting for the next decision',
                    reward=0.0, choices=[], highlight=[], hour_finished=False,
                    episode_finished=False, tentative=False)

    def step(self, greedy=False, capture=True):
        if self.finished:
            return None
        if self.env.done:
            self.env.reset()
            self.episode += 1
            self.steps = 0
            self.total = 0.0
            self.history = []
        env, agent = self.env, self.agent
        state = env.state
        key = state_to_key(state)
        valid = env.valid_actions()
        # Probe a COPY of RNG state to label the actual selection mechanism.
        probe = random.Random()
        probe.setstate(agent.rng.getstate())
        explore = not greedy and probe.random() < agent.epsilon
        action = agent.select_action(key, valid, greedy=greedy)
        choices = [(str(a), agent.q_value(key, a), a == action) for a in valid] if capture else []
        highlighted = list(state.current_route)
        if action.type == 'ADD_STOP':
            highlighted = [action.arg]
        elif action.arg is not None and action.type != 'ADD_STOP':
            highlighted = list(state.current_plan[action.arg].route)
        result = env.step(action)
        next_key = None if result.done else state_to_key(result.next_state)
        next_valid = [] if result.done else env.valid_actions()
        if not greedy:
            agent.update(key, action, result.reward, next_key, next_valid, result.done)
        self.steps += 1
        self.total += result.reward
        closed_hour = 'hour_finished' in result.info
        event = None
        if capture:
            if closed_hour:
                plan = env.hourly_plans[state.hour]
                event = self.snapshot(hour=state.hour, plan=plan, route=(),
                                      evaluation=env.hourly_records[-1])
            else:
                tentative_plan = env.current_plan
                freq = env.masker.end_route_frequency(env.state)
                tentative = bool(env.current_route and freq is not None)
                if tentative:
                    tentative_plan += (RouteService(env.current_route, freq, False),)
                event = self.snapshot(evaluation=env.evaluate_plan(tentative_plan))
                event['tentative'] = tentative
            event.update(action=str(action),
                         decision='Greedy evaluation (no learning)' if greedy else (
                             'Random exploration' if explore else 'Greedy choice (learning)'),
                         reward=result.reward, total=self.total, choices=choices,
                         highlight=highlighted, hour_finished=closed_hour,
                         episode_finished=result.done,
                         forced=result.info.get('discarded_unfinished_route') is not None or (
                             closed_hour and env.hourly_records[-1]['forced_finish']))
            self.history.append(event)
            self.last = event
        if result.done:
            day = summarise_day(env.hourly_records)
            self.curves.append(dict(episode=self.episode, reward=self.total,
                                    coverage=day['served_demand_ratio'],
                                    fleet=day['average_fleet_used'], states=agent.num_states,
                                    pairs=agent.num_state_action_pairs, steps=self.steps,
                                    mode='evaluation' if greedy else 'training'))
            self.completed_history = self.history[:]
            if not greedy:
                agent.decay_epsilon()
        return event if capture else result


def graph_positions(network):
    """Deterministic force layout: topology only, not geographical coordinates."""
    n = network.num_stops
    rng = np.random.default_rng(7)
    points = rng.uniform(-1, 1, (n, 2))
    adjacency = np.isfinite(network.travel_time).astype(float)
    np.fill_diagonal(adjacency, 0)
    adjacency = np.maximum(adjacency, adjacency.T)
    for iteration in range(350):
        delta = points[:, None, :] - points[None, :, :]
        dist = np.maximum(np.linalg.norm(delta, axis=2), 0.02)
        force = (delta * (0.45 ** 2 / dist ** 2)[:, :, None]).sum(axis=1)
        force -= (delta * (dist / 0.45 * adjacency)[:, :, None]).sum(axis=1)
        norm = np.maximum(np.linalg.norm(force, axis=1), 0.001)
        temperature = 0.07 * (1 - iteration / 350) + 0.002
        points += force / norm[:, None] * np.minimum(norm, temperature)[:, None]
        points -= points.mean(axis=0)
    low, high = points.min(axis=0), points.max(axis=0)
    return {i + 1: tuple((p - low) / np.maximum(high - low, 0.01)) for i, p in enumerate(points)}


COLORS = ['#2563eb', '#059669', '#db2777', '#7c3aed', '#ea580c', '#0891b2', '#b45309', '#475569']


def enable_dpi_awareness():
    """Keep this app's geometry crisp and on-screen on scaled Windows displays."""
    import sys
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class Visualizer:
    def __init__(self, root, cfg=None, target=20):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk, self.root = tk, ttk, root
        root.tk.call('tk', 'scaling', 4 / 3)
        self.cfg = cfg or ExperimentConfig()
        self.session = VisualSession(self.cfg, target=target)
        self.positions = graph_positions(self.session.network)
        self.running = False
        self.fast = False
        self.greedy = False
        self.replay = None
        self.replay_index = 0
        self.selected = None
        self.dragging = None
        self.closed = False
        self.after_id = None
        self.training_session = None
        self.root.title('RL-New | Training Studio')
        root.geometry(f'{min(1370,root.winfo_screenwidth()-60)}x{min(940,root.winfo_screenheight()-90)}+20+20')
        root.minsize(1080, 760)
        root.configure(bg='#edf2f7')
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#edf2f7')
        style.configure('TLabel', background='#edf2f7', foreground='#16324f', font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), padding=(10, 7))
        style.configure('Treeview', font=('Segoe UI', 9), rowheight=25, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', font=('Segoe UI Semibold', 9))
        self.speed = tk.DoubleVar(value=6)
        self.target_var = tk.StringVar(value=str(target))
        self.show_times = tk.BooleanVar(value=False)
        self.metrics = {}
        self.build()
        self.render(self.session.last)

    def build(self):
        tk, ttk = self.tk, self.ttk
        header = tk.Frame(self.root, bg='#12314b', padx=22, pady=14)
        header.pack(fill='x')
        tk.Label(header, text='RL-New  /  Training Studio', font=('Segoe UI Semibold', 22), fg='white', bg='#12314b').pack(side='left')
        tk.Label(header, text='Real model decisions · raw-state Q-learning', font=('Segoe UI', 10), fg='#b8d7e8', bg='#12314b').pack(side='right')
        toolbar = ttk.Frame(self.root, padding=(14, 10))
        toolbar.pack(fill='x')
        self.play_button = ttk.Button(toolbar, text='▶ Play', command=self.toggle)
        self.play_button.pack(side='left', padx=3)
        self.step_button = ttk.Button(toolbar, text='Step action', command=self.single)
        self.step_button.pack(side='left', padx=3)
        ttk.Button(toolbar, text='Next hour', command=self.next_hour).pack(side='left', padx=3)
        self.fast_button = ttk.Button(toolbar, text='Fast train', command=self.fast_train)
        self.fast_button.pack(side='left', padx=3)
        ttk.Label(toolbar, text='Episodes:').pack(side='left', padx=(12, 3))
        self.target_entry = ttk.Spinbox(toolbar, from_=1, to=10000, textvariable=self.target_var, width=6)
        self.target_entry.pack(side='left')
        ttk.Button(toolbar, text='New session', command=self.reset).pack(side='left', padx=6)
        ttk.Button(toolbar, text='Save session', command=self.save).pack(side='right', padx=3)
        ttk.Button(toolbar, text='How to use', command=self.help).pack(side='right', padx=3)
        modebar = ttk.Frame(self.root, padding=(18, 0, 18, 8))
        modebar.pack(fill='x')
        ttk.Label(modebar, text='Playback speed').pack(side='left')
        ttk.Scale(modebar, from_=1, to=30, variable=self.speed, length=175).pack(side='left', padx=8)
        ttk.Label(modebar, text='1–30 actions/s').pack(side='left')
        ttk.Button(modebar, text='Replay recent episode', command=self.start_replay).pack(side='left', padx=(20, 5))
        ttk.Button(modebar, text='Return to live', command=self.live).pack(side='left', padx=4)
        ttk.Button(modebar, text='Greedy evaluation', command=self.evaluate).pack(side='left', padx=4)
        self.mode_label = ttk.Label(modebar, text='LIVE • paused')
        self.mode_label.pack(side='right')
        cards = tk.Frame(self.root, bg='#edf2f7')
        cards.pack(fill='x', padx=18, pady=(0, 10))
        for name in ['Episode / hour', 'Latest action reward', 'Served demand', 'Fleet committed', 'Q-table states']:
            box = tk.Frame(cards, bg='white', padx=14, pady=9)
            box.pack(side='left', fill='x', expand=True, padx=(0, 8))
            tk.Label(box, text=name.upper(), bg='white', fg='#60748b', font=('Segoe UI', 8)).pack(anchor='w')
            value = tk.Label(box, text='—', bg='white', fg='#12314b', font=('Segoe UI Semibold', 17))
            value.pack(anchor='w')
            self.metrics[name] = value
        main = ttk.Frame(self.root, padding=(18, 0, 18, 8))
        main.pack(fill='both', expand=True)
        left = ttk.Frame(main)
        left.pack(side='left', fill='both', expand=True)
        ttk.Label(left, text='NETWORK  •  grey links: roads   coloured: committed routes   dashed amber: building', font=('Segoe UI Semibold', 9)).pack(anchor='w', pady=(0, 6))
        self.graph = tk.Canvas(left, bg='white', highlightthickness=0, width=730, height=355)
        self.graph.pack(fill='both', expand=True)
        self.graph.bind('<Configure>', lambda e: self.draw_graph())
        self.graph.bind('<ButtonPress-1>', self.drag_start)
        self.graph.bind('<B1-Motion>', self.drag_move)
        self.graph.bind('<ButtonRelease-1>', lambda e: setattr(self, 'dragging', None))
        graphbar = ttk.Frame(left)
        graphbar.pack(fill='x', pady=4)
        ttk.Label(graphbar, text='Schematic layout • drag stops to rearrange').pack(side='left')
        ttk.Checkbutton(graphbar, text='Link travel minutes', variable=self.show_times, command=self.draw_graph).pack(side='right')
        charts = ttk.Frame(left)
        charts.pack(fill='x')
        self.reward_chart = tk.Canvas(charts, bg='white', height=120, highlightthickness=0)
        self.reward_chart.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.state_chart = tk.Canvas(charts, bg='white', height=120, highlightthickness=0)
        self.state_chart.pack(side='left', fill='x', expand=True)
        for chart in (self.reward_chart, self.state_chart):
            chart.bind('<Configure>', lambda e: self.draw_charts())
        right = ttk.Frame(main, padding=(16, 0, 0, 0), width=395)
        right.pack(side='right', fill='y')
        right.pack_propagate(False)
        self.action_text = ttk.Label(right, text='Ready', font=('Segoe UI Semibold', 16), wraplength=375)
        self.action_text.pack(anchor='w')
        self.detail_text = ttk.Label(right, text='', wraplength=375)
        self.detail_text.pack(anchor='w', pady=(4, 10))
        ttk.Label(right, text='COMMITTED ROUTES • select to isolate', font=('Segoe UI Semibold', 9)).pack(anchor='w')
        self.routes = ttk.Treeview(right, columns=('route', 'freq', 'buses'), show='headings', height=6, selectmode='browse')
        for col, title, width in [('route', 'Route / stops', 242), ('freq', '/hour', 55), ('buses', 'Buses', 55)]:
            self.routes.heading(col, text=title); self.routes.column(col, width=width, stretch=col=='route')
        self.routes.pack(fill='x', pady=5)
        self.routes.bind('<<TreeviewSelect>>', self.route_selected)
        ttk.Button(right, text='Show all routes', command=self.clear_selection).pack(anchor='w')
        self.score_text = ttk.Label(right, text='', wraplength=375)
        self.score_text.pack(anchor='w', pady=10)
        ttk.Label(right, text='VALID ACTIONS BEFORE THE LAST DECISION', font=('Segoe UI Semibold', 9)).pack(anchor='w')
        qbox = ttk.Frame(right); qbox.pack(fill='x', pady=5)
        self.qchoices = ttk.Treeview(qbox, columns=('action', 'q'), show='headings', height=5)
        self.qchoices.heading('action', text='Action (● = selected)'); self.qchoices.heading('q', text='Q before update')
        self.qchoices.column('action', width=225); self.qchoices.column('q', width=115)
        self.qchoices.pack(side='left', fill='x', expand=True)
        scroll = ttk.Scrollbar(qbox, orient='vertical', command=self.qchoices.yview)
        scroll.pack(side='right', fill='y'); self.qchoices.configure(yscrollcommand=scroll.set)
        ttk.Label(right, text='RECENT ACTIONS', font=('Segoe UI Semibold', 9)).pack(anchor='w', pady=(8, 3))
        self.log = tk.Text(right, height=4, width=45, bg='white', relief='flat', font=('Consolas', 9), state='disabled')
        self.log.pack(fill='both', expand=True)
        self.status = ttk.Label(self.root, text='', padding=(18, 7), wraplength=1300)
        self.status.pack(fill='x')

    def stop(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.running = False
        self.play_button.configure(text='▶ Play')
        self.mode_label.configure(text=('REPLAY' if self.replay is not None else 'EVALUATION' if self.greedy else 'LIVE')+' • paused')

    def toggle(self):
        if self.running:
            self.stop(); return
        if self.replay is None and self.session.finished:
            self.status.configure(text='Session complete. Replay it, start a greedy evaluation, or create a new session.')
            return
        self.running = True
        self.fast = False
        self.play_button.configure(text='Ⅱ Pause')
        self.tick()

    def advance(self):
        if self.replay is not None:
            if self.replay_index >= len(self.replay):
                self.stop(); return None
            event = self.replay[self.replay_index]
            self.replay_index += 1
            return event
        return self.session.step(greedy=self.greedy)

    def single(self):
        self.stop()
        self.safe_advance()

    def safe_advance(self):
        try:
            event = self.advance()
            if event:
                self.render(event)
            return event
        except Exception as exc:
            self.fail(exc)
            return None

    def tick(self):
        if not self.running or self.closed:
            return
        deadline = time.perf_counter() + (0.035 if self.fast else 0)
        event = None
        try:
            while True:
                event = self.advance()
                if event is None or event['episode_finished'] or not self.fast or time.perf_counter() >= deadline:
                    break
            if event:
                self.render(event)
            if event is None or (self.replay is None and self.session.finished):
                self.stop(); return
            self.mode_label.configure(text=('REPLAY' if self.replay is not None else 'EVALUATION' if self.greedy else 'FAST TRAINING' if self.fast else 'LIVE TRAINING')+' • running')
            self.after_id = self.root.after(1 if self.fast else max(1, int(1000 / self.speed.get())), self.tick)
        except Exception as exc:
            self.fail(exc)

    def next_hour(self):
        self.stop()
        self.running = True
        self.fast = True
        self.play_button.configure(text='Ⅱ Pause')
        def chunk():
            if not self.running or self.closed:
                return
            deadline = time.perf_counter()+0.035
            try:
                event = None
                while time.perf_counter() < deadline:
                    event = self.advance()
                    if event is None or event['hour_finished']:
                        break
                if event:
                    self.render(event)
                if event is None or event['hour_finished']:
                    self.stop()
                else:
                    self.after_id = self.root.after(1, chunk)
            except Exception as exc:
                self.fail(exc)
        chunk()

    def fast_train(self):
        self.stop()
        self.live()
        self.fast = True
        self.running = True
        self.play_button.configure(text='Ⅱ Pause')
        self.tick()

    def reset(self):
        from tkinter import messagebox
        self.stop()
        try:
            target = int(self.target_var.get())
            if not 1 <= target <= 10000:
                raise ValueError('Choose an episode count from 1 to 10,000.')
            if (self.session.steps or self.session.curves) and not messagebox.askyesno(
                    'New session', 'Start a fresh Q-table? Save your current session first if you need it.'):
                return
            self.session = VisualSession(self.cfg, target=target,
                                         network=self.session.network, od=self.session.env.od_matrices)
            self.replay = None; self.greedy = False; self.selected = None
            self.training_session = None
            self.render(self.session.last)
        except Exception as exc:
            self.fail(exc)

    def start_replay(self):
        self.stop()
        events = self.session.completed_history or self.session.history
        if not events:
            self.status.configure(text='Take a few actions first. Replay uses the last completed episode, or the current partial episode.')
            return
        self.replay = events[:]
        self.replay_index = 0
        self.selected = None
        self.safe_advance()
        self.status.configure(text='REPLAY: Step or Play through recorded decisions. The Q-table and live session remain paused.')

    def live(self):
        self.stop(); self.replay = None; self.selected = None
        if self.greedy and self.training_session is not None:
            self.session = self.training_session
            self.training_session = None
            self.greedy = False
        self.render(self.session.last)

    def evaluate(self):
        from tkinter import messagebox
        self.stop()
        if self.greedy:
            self.status.configure(text='Already evaluating. Use Step or Play; New session starts training again.')
            return
        if not self.session.env.done and self.session.steps:
            messagebox.showinfo('Finish the current episode', 'Finish this episode first (Fast train can do this), then choose Greedy evaluation. This preserves the current training episode.')
            return
        old = self.session
        self.training_session = old
        self.session = VisualSession(self.cfg, target=1, network=old.network, od=old.env.od_matrices)
        self.session.agent = old.agent
        self.session.last = self.session.snapshot()
        self.session.last['decision'] = 'Greedy evaluation ready; Q-table will not be updated'
        self.greedy = True; self.replay = None; self.selected = None
        self.render(self.session.last)

    def save(self):
        from tkinter import filedialog, messagebox
        self.stop()
        name = filedialog.asksaveasfilename(title='Save visualizer session', defaultextension='.json',
                                          initialfile='visualizer_session.json', filetypes=[('JSON session','*.json')])
        if not name:
            return
        try:
            payload = dict(format='rl-new-visualizer-v1', config=asdict(self.cfg),
                           curves=self.session.curves, episode_events=self.session.history,
                           training_curves=self.training_session.curves if self.training_session else self.session.curves,
                           last_completed_episode=self.session.completed_history,
                           note='Snapshots and curves only; not a resumable Q-table checkpoint.')
            Path(name).write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
            self.status.configure(text='Saved '+name+' • includes curves and recent action replay, not a resumable Q-table.')
        except Exception as exc:
            messagebox.showerror('Could not save', str(exc))

    def help(self):
        from tkinter import messagebox
        messagebox.showinfo('Training Studio — quick guide',
            '1. Step action: see one real agent decision.\n'
            '2. Play / Pause: animate at the selected speed.\n'
            '3. Next hour: run to the next completed hourly plan.\n'
            '4. Fast train: learn with fewer screen refreshes. Pause anytime.\n'
            '5. Replay recent episode: inspect recorded actions without learning.\n'
            '6. Greedy evaluation: after an episode ends, inspect the learned policy without updates.\n'
            '   Return to live restores your paused training session.\n'
            '7. Select a route to isolate it; drag nodes to rearrange the graph.\n'
            '8. Set Episodes, then New session to apply it with a fresh Q-table.\n\n'
            'The viewer uses the default 10,000-episode epsilon schedule even for a short viewing session. '
            'Dashed amber routes are tentative. Metrics can include tentative service; the fleet card shows committed buses. '
            'Saved sessions contain recent snapshots and curves, not the Q-table. '
            'Existing training outputs are not overwritten.')

    def fail(self, exc):
        from tkinter import messagebox
        self.stop()
        self.status.configure(text='Paused after an error: '+str(exc))
        messagebox.showerror('Visualizer paused', str(exc))

    def render(self, event):
        self.display = event
        self.mode_label.configure(text=('REPLAY' if self.replay is not None else 'EVALUATION' if self.greedy else 'LIVE')+' • paused')
        m = event['metrics']
        hour = event['clock_hour']
        self.metrics['Episode / hour'].configure(text=f"{event['episode']} / {hour:02d}:00")
        self.metrics['Latest action reward'].configure(text=f"{event['reward']:+.4f}")
        self.metrics['Served demand'].configure(text=f"{100*m.get('served_demand_ratio',0):.1f}%"+(' *' if event['tentative'] else ''))
        self.metrics['Fleet committed'].configure(text=f"{event['fleet_used']} / {self.cfg.max_fleet}")
        self.metrics['Q-table states'].configure(text=f"{event['states']:,}")
        self.action_text.configure(text=event['action'])
        self.detail_text.configure(text=f"{event['decision']}\nε {event['epsilon']:.4f}  •  step {event['steps']}  •  return {event['total']:.4f}")
        self.score_text.configure(text=f"Evaluated plan score: {m.get('total_reward',0):.4f}\n"
            f"Coverage {m.get('service_component',0):.4f} − fleet penalty {m.get('operator_penalty',0):.4f} − change penalty {m.get('transition_component',0):.4f}\n"
            f"{'* Includes feasible tentative service; fleet card counts committed routes.' if event['tentative'] else 'Metrics describe the committed service plan.'}")
        self.routes.unbind('<<TreeviewSelect>>')
        self.routes.delete(*self.routes.get_children())
        for k, rec in enumerate(event['plan']):
            buses = self.session.env.fleet.buses_required(tuple(rec['route']), rec['frequency'])
            self.routes.insert('', 'end', iid=str(k), values=(f"R{k+1}{' [locked]' if rec['kept'] else ''}: "+'–'.join(map(str,rec['route'])), f"{rec['frequency']:g}", buses), tags=(str(k),))
            self.routes.tag_configure(str(k), foreground=COLORS[k % len(COLORS)])
        if self.selected is not None and str(self.selected) in self.routes.get_children():
            self.routes.selection_set(str(self.selected))
        else:
            self.selected = None
        self.routes.bind('<<TreeviewSelect>>', self.route_selected)
        self.qchoices.delete(*self.qchoices.get_children())
        for action, q, chosen in sorted(event['choices'], key=lambda x: (not x[2], -x[1])):
            self.qchoices.insert('', 'end', values=(('● ' if chosen else '')+action, f'{q:.5f}'))
        events = self.replay[:self.replay_index] if self.replay is not None else self.session.history
        self.log.configure(state='normal'); self.log.delete('1.0','end')
        for e in events[-6:]:
            self.log.insert('end', f"{e['clock_hour']:02d}:00 {e['action']:<24} {e['reward']:+.4f}\n")
        self.log.configure(state='disabled')
        if event['episode_finished']:
            text = 'Episode finished. Replay its actions or run a greedy evaluation.'
        elif event['hour_finished']:
            text = f"Hourly plan finalised{' at the action limit' if event.get('forced') else ''}. Showing the completed hour; the next action starts the next hour."
        else:
            text = f"Live session target: {self.session.target} episodes • epsilon schedule: {self.cfg.num_episodes:,} episodes • replay keeps the current and last completed episode."
        self.status.configure(text=text)
        self.draw_graph(); self.draw_charts()

    def route_selected(self, _event=None):
        selected = self.routes.selection()
        self.selected = int(selected[0]) if selected else None
        self.draw_graph()

    def clear_selection(self):
        self.selected = None
        self.routes.selection_remove(*self.routes.selection())
        self.draw_graph()

    def node_xy(self, stop):
        x,y = self.positions[stop]
        return 55+x*max(100,self.graph.winfo_width()-110), 45+y*max(80,self.graph.winfo_height()-90)

    def draw_graph(self):
        if not hasattr(self,'display'):
            return
        c = self.graph; c.delete('all')
        net, event = self.session.network, self.display
        for i in net.stops:
            for j in net.stops:
                if i>=j or not (net.has_link(i,j) or net.has_link(j,i)):
                    continue
                x,y = self.node_xy(i); u,v = self.node_xy(j)
                c.create_line(x,y,u,v,fill='#cbd5e1',width=2)
                if self.show_times.get():
                    a,b = (i,j) if net.has_link(i,j) else (j,i)
                    c.create_text((x+u)/2,(y+v)/2-9,text=f'{net.link_time(a,b):g}',fill='#6b7b8f',font=('Segoe UI',8))
        for k, rec in enumerate(event['plan']):
            if self.selected is not None and self.selected != k:
                continue
            route = rec['route']
            for a,b in zip(route,route[1:]):
                x,y=self.node_xy(a); u,v=self.node_xy(b)
                length=max(1,math.hypot(u-x,v-y)); offset=(k-3.5)*2.8
                dx,dy=-(v-y)/length*offset,(u-x)/length*offset
                c.create_line(x+dx,y+dy,u+dx,v+dy,fill=COLORS[k%len(COLORS)],width=4)
        route = event['route']
        for a,b in zip(route,route[1:]):
            c.create_line(*self.node_xy(a),*self.node_xy(b),fill='#f59e0b',width=6,dash=(8,5))
        for s in net.stops:
            x,y=self.node_xy(s)
            if s in event['highlight']:
                c.create_oval(x-21,y-21,x+21,y+21,outline='#fbbf24',width=3)
            fill='#fff3cd' if s in route else '#f8fafc'
            c.create_oval(x-15,y-15,x+15,y+15,fill=fill,outline='#25445f',width=2)
            c.create_text(x,y,text=str(s),fill='#12314b',font=('Segoe UI Semibold',10))
        if not event['plan'] and not route:
            c.create_text(20,18,anchor='w',text='No routes yet — press Step action or Play to start.',fill='#667b90',font=('Segoe UI',10))

    def drag_start(self,e):
        for s in self.positions:
            x,y=self.node_xy(s)
            if math.hypot(e.x-x,e.y-y)<22:
                self.dragging=s; break

    def drag_move(self,e):
        if self.dragging:
            self.positions[self.dragging]=(min(1,max(0,(e.x-55)/max(100,self.graph.winfo_width()-110))),
                                           min(1,max(0,(e.y-45)/max(80,self.graph.winfo_height()-90))))
            self.draw_graph()

    def draw_charts(self):
        if not hasattr(self,'reward_chart'):
            return
        for canvas,field,title,color in [(self.reward_chart,'reward','Completed episode return','#2563eb'),
                                         (self.state_chart,'states','Q-table states after each episode','#059669')]:
            canvas.delete('all'); w,h=canvas.winfo_width(),canvas.winfo_height()
            canvas.create_text(12,14,anchor='w',text=title,fill='#12314b',font=('Segoe UI Semibold',9))
            values=[r[field] for r in self.session.curves]
            if not values:
                canvas.create_text(12,55,anchor='w',text='Appears after a complete 24-hour episode',fill='#7a8ba0',font=('Segoe UI',9)); continue
            # Bucket long runs to a bounded number of chart segments.
            stride=max(1,len(values)//250)
            points=list(range(0,len(values),stride))
            if points[-1]!=len(values)-1: points.append(len(values)-1)
            low,high=min(values),max(values)
            span=high-low or max(1,abs(high)*0.1)
            xy=[]
            for i in points:
                xy.extend([40+i/max(1,len(values)-1)*max(80,w-65),h-23-(values[i]-low)/span*(h-60)])
            if len(xy)>=4: canvas.create_line(*xy,fill=color,width=2)
            else: canvas.create_oval(xy[0]-3,xy[1]-3,xy[0]+3,xy[1]+3,fill=color,outline=color)
            canvas.create_text(12,h-12,anchor='w',text=f'{len(values)} episode(s)  •  latest {values[-1]:,.3f}',fill='#60748b',font=('Segoe UI',8))

    def close(self):
        self.closed=True; self.running=False
        self.root.destroy()


def main():
    parser=argparse.ArgumentParser(description='RL-New live training visualizer')
    parser.add_argument('--episodes', type=int, default=20, help='viewer stop point; epsilon schedule remains the default 10,000 episodes')
    args=parser.parse_args()
    if not 1<=args.episodes<=10000:
        parser.error('--episodes must be between 1 and 10,000')
    enable_dpi_awareness()
    import tkinter as tk
    from tkinter import messagebox
    root=tk.Tk()
    try:
        Visualizer(root,target=args.episodes)
    except Exception as exc:
        root.withdraw(); messagebox.showerror('Could not start RL-New Training Studio',str(exc)); root.destroy(); return 1
    root.mainloop()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
