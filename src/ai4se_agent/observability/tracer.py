import json
import time
from pathlib import Path
from ai4se_agent.observability.events import Event


class Tracer:
    def __init__(self):
        self._events: list[Event] = []
        self._start_time: float = time.time()
        self.total_tokens: int = 0

    def record(self, event: Event) -> None:
        import datetime
        event.timestamp = datetime.datetime.now().isoformat()
        event.elapsed_ms = (time.time() - self._start_time) * 1000
        self._events.append(event)

    def record_token(self, prompt: int, completion: int) -> None:
        self.total_tokens += prompt + completion

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

    @staticmethod
    def replay_filtered(path: str, *, event_type: str | None = None,
                        min_iteration: int = 0) -> list[dict]:
        events = Tracer.replay(path)
        result = []
        for e in events:
            if event_type is not None and e.get("type") != event_type:
                continue
            if e.get("iteration", 0) < min_iteration:
                continue
            result.append(e)
        return result


class NullTracer(Tracer):
    def record(self, event: Event) -> None:
        pass

    def save(self, path: str) -> None:
        pass
