import time
from dataclasses import dataclass, field


@dataclass
class AgentEvent:
    type: str
    iteration: int
    state: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "state": self.state,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentEvent":
        return cls(
            type=data["type"],
            iteration=data["iteration"],
            state=data["state"],
            timestamp=data.get("timestamp", 0.0),
            payload=data.get("payload", {}),
        )
