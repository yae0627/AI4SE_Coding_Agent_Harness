from ai4se_agent.memory.persistent import PersistentMemory

__all__ = ["PersistentMemory"]


def get_memory_manager():
    from ai4se_agent.memory.manager import MemoryManager
    return MemoryManager
