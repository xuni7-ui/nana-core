"""Persistent Self C-stage: a single bounded causal subject loop."""
from .contracts import SubjectInput, PreferenceSignal, WakeCondition, StandingDelegation
from .loop import SubjectLoop

__all__ = ['SubjectInput', 'PreferenceSignal', 'WakeCondition', 'StandingDelegation', 'SubjectLoop']
