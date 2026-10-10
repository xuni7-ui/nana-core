"""Only the ports required by the offline experiment."""
from typing import Protocol
from .contracts import Invocation, ModelRequest, PlanProposal, Receipt, Verification


class ModelPort(Protocol):
    descriptor: str
    def propose(self, request: ModelRequest) -> PlanProposal: ...


class CapabilityPort(Protocol):
    def execute(self, invocation: Invocation) -> Receipt: ...
    def verify(self, invocation: Invocation) -> Verification: ...
