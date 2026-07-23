from ai4se_agent.memory.session import SessionMemory
from ai4se_agent.memory.persistent import PersistentMemory


class MemoryManager:
    def __init__(self, session: SessionMemory | None = None, persistent: PersistentMemory | None = None):
        self.session = session or SessionMemory()
        self.persistent = persistent or PersistentMemory()

    def add_to_session(self, role: str, content: str) -> None:
        self.session.add(role, content)

    def get_session_history(self) -> list:
        return self.session.get_all()

    def get_rules(self) -> list[str]:
        rule_names = self.persistent.list_rules()
        rules = []
        for name in rule_names:
            content = self.persistent.load_rule(name)
            if content:
                rules.append(content.strip())
        return rules
