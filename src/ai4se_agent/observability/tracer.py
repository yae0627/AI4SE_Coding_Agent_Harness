# src/ai4se_agent/observability/tracer.py
import json
from pathlib import Path
from ai4se_agent.observability.events import Event


class Tracer:
    def __init__(self):
        self._events: list[Event] = []

    def record(self, event: Event) -> None:
        self._events.append(event)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._events]
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def replay(path: str) -> list[dict]:
        p = Path(path)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))


class NullTracer(Tracer):
    def record(self, event: Event) -> None:
        pass

    def save(self, path: str) -> None:
        pass
