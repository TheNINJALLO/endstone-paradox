# evidence_replay.py - Evidence replay system for Paradox AntiCheat
# Records player actions in a ring buffer and snapshots on violations
# so staff can review what happened.

import time
import math
from collections import defaultdict, deque
from typing import Dict, List, Optional
from endstone_paradox.modules.base import BaseModule


class EvidenceReplayModule(BaseModule):
    """Evidence replay system.

    Continuously records player state (position, rotation, actions) in a
    per-player ring buffer.  When a violation is emitted, the buffer is
    snapshotted and stored for staff review via /ac-replay.

    Each frame captures:
      - timestamp, position (x, y, z), yaw, pitch
      - current action (walking, breaking, placing, attacking, idle)
      - optional metadata (target entity, block type)

    Staff can then replay these snapshots to verify violations.
    """

    name = "evidencereplay"

    BUFFER_SECONDS = 15       # keep last N seconds of frames
    FRAME_INTERVAL_TICKS = 4  # capture every 4 ticks (~200ms)
    MAX_SNAPSHOTS_PER_PLAYER = 5   # keep last N violation snapshots
    MAX_TOTAL_SNAPSHOTS = 100      # global cap

    def on_start(self):
        # Ring buffers: uuid -> deque of frame dicts
        self._buffers: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=int(self.BUFFER_SECONDS / 0.2))
        )

        # Stored snapshots: list of {uuid, name, module, time, frames}
        self._snapshots: List[dict] = []
        self._load_snapshots()

        # Action tracking helpers
        self._last_action: Dict[str, str] = defaultdict(lambda: "idle")
        self._last_target: Dict[str, str] = {}

    @property
    def check_interval(self) -> int:
        return self.FRAME_INTERVAL_TICKS

    def check(self):
        """Capture a frame for every online player."""
        now = time.time()
        try:
            for player in self.plugin.server.online_players:
                try:
                    uuid_str = str(player.unique_id)
                    loc = player.location

                    frame = {
                        "t": round(now, 2),
                        "x": round(loc.x, 2),
                        "y": round(loc.y, 2),
                        "z": round(loc.z, 2),
                        "yaw": round(loc.yaw, 1),
                        "pitch": round(loc.pitch, 1),
                        "action": self._last_action.get(uuid_str, "idle"),
                    }

                    target = self._last_target.get(uuid_str)
                    if target:
                        frame["target"] = target

                    self._buffers[uuid_str].append(frame)

                    # Reset action to idle (will be re-set if player does something)
                    self._last_action[uuid_str] = "idle"
                    self._last_target.pop(uuid_str, None)
                except Exception:
                    pass
        except Exception:
            pass

    # --- Action tracking (called from event handlers in paradox.py) ---

    def record_action(self, uuid_str: str, action: str, target: str = None):
        """Record a player action for the next frame.

        Actions: 'breaking', 'placing', 'attacking', 'chatting', 'moving'
        """
        self._last_action[uuid_str] = action
        if target:
            self._last_target[uuid_str] = target

    # --- Violation snapshot ---

    def on_violation(self, player, module: str, severity: int, evidence: dict):
        """Called when a violation is emitted. Snapshots the replay buffer."""
        try:
            uuid_str = str(player.unique_id)
            name = player.name if hasattr(player, 'name') else "?"
            buf = self._buffers.get(uuid_str)
            if not buf:
                return

            # Copy the current buffer
            frames = list(buf)
            if not frames:
                return

            snapshot = {
                "uuid": uuid_str,
                "name": name,
                "module": module,
                "severity": severity,
                "time": time.time(),
                "evidence": {k: str(v) for k, v in list(evidence.items())[:5]},
                "frames": frames,
                "frame_count": len(frames),
                "duration": round(frames[-1]["t"] - frames[0]["t"], 1) if len(frames) > 1 else 0,
            }

            self._snapshots.append(snapshot)

            # Per-player cap
            player_snaps = [s for s in self._snapshots if s["uuid"] == uuid_str]
            if len(player_snaps) > self.MAX_SNAPSHOTS_PER_PLAYER:
                # Remove oldest for this player
                oldest = player_snaps[0]
                self._snapshots.remove(oldest)

            # Global cap
            if len(self._snapshots) > self.MAX_TOTAL_SNAPSHOTS:
                self._snapshots = self._snapshots[-self.MAX_TOTAL_SNAPSHOTS:]

            self._save_snapshots()
        except Exception:
            pass

    # --- Staff replay API ---

    def get_snapshots(self, uuid_str: str = None, limit: int = 10) -> List[dict]:
        """Get recent snapshots, optionally filtered by player."""
        if uuid_str:
            results = [s for s in self._snapshots if s["uuid"] == uuid_str]
        else:
            results = self._snapshots[:]
        return results[-limit:]

    def get_snapshot_summary(self, snapshot: dict) -> str:
        """Generate a human-readable summary of a snapshot."""
        frames = snapshot.get("frames", [])
        if not frames:
            return "No frames captured."

        # Calculate movement stats
        total_dist = 0.0
        for i in range(1, len(frames)):
            dx = frames[i]["x"] - frames[i-1]["x"]
            dy = frames[i]["y"] - frames[i-1]["y"]
            dz = frames[i]["z"] - frames[i-1]["z"]
            total_dist += math.sqrt(dx*dx + dy*dy + dz*dz)

        # Count actions
        actions = defaultdict(int)
        for f in frames:
            actions[f.get("action", "idle")] += 1

        duration = snapshot.get("duration", 0)
        action_str = ", ".join(f"{a}×{c}" for a, c in sorted(actions.items(), key=lambda x: -x[1]))

        return (
            f"§e{snapshot['name']}§r — §c{snapshot['module']}§r "
            f"({snapshot.get('severity', '?')}) at {time.strftime('%H:%M:%S', time.localtime(snapshot['time']))}\n"
            f"  §7Duration: {duration}s | Frames: {len(frames)} | "
            f"Distance: {total_dist:.1f} blocks\n"
            f"  §7Actions: {action_str}"
        )

    def format_replay(self, snapshot: dict, start_frame: int = 0,
                      count: int = 20) -> List[str]:
        """Format replay frames for in-game display."""
        frames = snapshot.get("frames", [])
        subset = frames[start_frame:start_frame + count]
        lines = []
        t0 = frames[0]["t"] if frames else 0

        for f in subset:
            elapsed = f["t"] - t0
            action = f.get("action", "idle")
            target = f.get("target", "")
            target_str = f" → {target}" if target else ""

            lines.append(
                f"§7[{elapsed:5.1f}s] §f({f['x']:.1f}, {f['y']:.1f}, {f['z']:.1f}) "
                f"§e{action}{target_str}"
            )

        return lines

    def clear_snapshots(self, uuid_str: str = None):
        """Clear snapshots, optionally for a specific player."""
        if uuid_str:
            self._snapshots = [s for s in self._snapshots if s["uuid"] != uuid_str]
        else:
            self._snapshots.clear()
        self._save_snapshots()

    # --- Persistence ---

    def _save_snapshots(self):
        try:
            # Store without frames for the index (frames stored separately)
            summaries = []
            for s in self._snapshots[-50:]:
                summary = {k: v for k, v in s.items() if k != "frames"}
                summaries.append(summary)
            self.db.set("evidence", "snapshot_index", summaries)

            # Store full snapshots with frames
            for s in self._snapshots[-50:]:
                key = f"snap_{s['uuid']}_{int(s['time'])}"
                self.db.set("evidence", key, s)
        except Exception:
            pass

    def _load_snapshots(self):
        try:
            index = self.db.get("evidence", "snapshot_index", [])
            if not isinstance(index, list):
                self._snapshots = []
                return

            self._snapshots = []
            for summary in index[-self.MAX_TOTAL_SNAPSHOTS:]:
                key = f"snap_{summary.get('uuid', '')}_{int(summary.get('time', 0))}"
                full = self.db.get("evidence", key)
                if full and isinstance(full, dict):
                    self._snapshots.append(full)
                else:
                    self._snapshots.append(summary)
        except Exception:
            self._snapshots = []

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._buffers.pop(uuid_str, None)
        self._last_action.pop(uuid_str, None)
        self._last_target.pop(uuid_str, None)
