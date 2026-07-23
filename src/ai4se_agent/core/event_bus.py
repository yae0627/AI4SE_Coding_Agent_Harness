from collections import defaultdict
from typing import Callable
from ai4se_agent.core.events import AgentEvent


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[AgentEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[AgentEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: AgentEvent) -> None:
        for handler in self._handlers.get(event.type, []):
            handler(event)
