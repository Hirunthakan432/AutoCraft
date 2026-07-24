from typing import List, Dict, Any

class ConversationMemory:
    """Manages chat history and conversation context for AutoCraft agents."""
    
    def __init__(self, system_instruction: str = None):
        self.system_instruction = system_instruction
        self.history: List[Dict[str, str]] = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})

    def add_agent_message(self, content: str):
        self.history.append({"role": "model", "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def clear(self):
        self.history.clear()