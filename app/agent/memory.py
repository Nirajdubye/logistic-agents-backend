"""
Legacy conversation memory adapter.
Note: Modern OrchestratorAgent manages session history via chat_history_manager
and per-thread in-memory state. This module is maintained for backwards compatibility.
"""

try:
    from langchain_community.memory import ConversationBufferMemory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
except ImportError:
    try:
        from langchain.memory import ConversationBufferMemory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    except ImportError:
        memory = None