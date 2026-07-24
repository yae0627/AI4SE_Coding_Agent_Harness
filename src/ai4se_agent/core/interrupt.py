import threading
import queue
from dataclasses import dataclass, field


@dataclass
class InterruptChannel:
    """Thread-safe communication channel between CLI main thread and agent thread.

    Used by the state machine to check for stop requests and wait for
    HITL approval responses without blocking stdin.
    """

    stop_requested: threading.Event = field(default_factory=threading.Event)
    approval_response: queue.Queue = field(default_factory=queue.Queue)

    def request_stop(self) -> None:
        self.stop_requested.set()

    def send_approval(self, approved: bool) -> None:
        self.approval_response.put("approve" if approved else "reject")
