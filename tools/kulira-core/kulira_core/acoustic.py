"""Acoustic inter-node channel: harmonic phrases and pheromone-style cues.

Nodes have microphone input and speaker output. This host model captures
the experiment's physics honestly at lab scale: sound attenuates with
distance, a node is deaf to itself during its own settling window, and
what travels is features (pitch, onset, level) - never identity. On top
sit the two measurements that make it science: synchrony (do phases
align into coordinated music/dance?) and vocabulary growth (do shared
pitches/phrases emerge and spread, pheromone-style, without a designer
assigning their meaning?).
"""
from __future__ import annotations
import cmath, collections, math
from dataclasses import dataclass

@dataclass(frozen=True)
class TonePhrase:
    node: str; pitch_hz: float; start_s: float; duration_s: float; amplitude: float = 0.5

class AcousticChannel:
    def __init__(self, settle_s: float = 0.25, ref_distance_m: float = 1.0):
        self.settle_s = settle_s; self.ref_distance_m = ref_distance_m
    def hear(self, phrase: TonePhrase, listener_xy, source_xy) -> float:
        d = max(math.dist(listener_xy, source_xy), 0.1)
        return phrase.amplitude * (self.ref_distance_m / d)
    def audible(self, phrase: TonePhrase, listener: str, own_last_end_s: float | None) -> bool:
        if phrase.node == listener and own_last_end_s is not None:
            return phrase.start_s - own_last_end_s >= self.settle_s
        return True

def synchrony(phases) -> float:
    """Kuramoto order parameter: 1 = perfect phase alignment."""
    if not phases: return 0.0
    return abs(sum(cmath.exp(1j * p) for p in phases) / len(phases))

def vocabulary_growth(heard) -> dict:
    """heard: iterable of (listener, pitch). A pitch is shared when >=2 nodes use it."""
    by_pitch = collections.defaultdict(set)
    for node, pitch in heard: by_pitch[pitch].add(node)
    shared = {p: sorted(ns) for p, ns in by_pitch.items() if len(ns) >= 2}
    return {"distinct": len(by_pitch), "shared_pitches": len(shared),
            "shared": {str(p): ns for p, ns in sorted(shared.items())}}
