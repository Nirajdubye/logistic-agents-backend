import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")

def _ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

def load_all_chats() -> Dict[str, Any]:
    """Load all chat sessions dictionary from JSON storage file."""
    _ensure_data_file()
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading chats file: {e}")
        return {}

def save_all_chats(chats: Dict[str, Any]) -> bool:
    """Save all chat sessions dictionary to JSON storage file."""
    _ensure_data_file()
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving chats file: {e}")
        return False

def get_chat_headers() -> List[Dict[str, Any]]:
    """Return summary headers for all saved chat sessions."""
    chats = load_all_chats()
    headers = []
    for thread_id, session in chats.items():
        headers.append({
            "thread_id": thread_id,
            "title": session.get("title", f"Session {thread_id}"),
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
            "message_count": len(session.get("messages", [])),
        })
    # Sort headers by updated_at descending
    headers.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return headers

def get_chat_session(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full JSON payload of a specific chat session."""
    chats = load_all_chats()
    return chats.get(thread_id)

def create_or_update_turn(
    thread_id: str,
    query: str,
    answer: str,
    route: str,
    execution_timeline: List[Dict[str, Any]],
    policy_result: Optional[Dict[str, Any]] = None,
    operation_data: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    email_data: Optional[Dict[str, Any]] = None,
    timestamp: str = "",
) -> Dict[str, Any]:
    """Append a new user/assistant exchange turn to a chat session JSON file."""
    chats = load_all_chats()
    now_str = timestamp or time.strftime("%Y-%m-%d %H:%M:%S")

    if thread_id not in chats:
        # Generate title from first query
        clean_query = query.strip()
        title = clean_query[:45] + "..." if len(clean_query) > 45 else clean_query
        chats[thread_id] = {
            "thread_id": thread_id,
            "title": title or f"Chat Session {thread_id}",
            "created_at": now_str,
            "updated_at": now_str,
            "messages": [],
        }

    session = chats[thread_id]
    session["updated_at"] = now_str

    # Construct user message entry
    user_msg_id = f"user-{int(time.time() * 1000)}"
    asst_msg_id = f"asst-{int(time.time() * 1000) + 1}"

    turn_entry = {
        "turn_id": f"turn-{len(session['messages']) // 2 + 1}",
        "user_message": {
            "id": user_msg_id,
            "sender": "user",
            "content": query,
            "timestamp": now_str,
        },
        "assistant_message": {
            "id": asst_msg_id,
            "sender": "assistant",
            "content": answer,
            "timestamp": now_str,
            "route": route,
            "execution_timeline": execution_timeline,
            "policy_result": policy_result,
            "operation_data": operation_data,
            "sources": sources or [],
            "email_data": email_data,
        },
    }

    session["messages"].append(turn_entry["user_message"])
    session["messages"].append(turn_entry["assistant_message"])

    save_all_chats(chats)
    return session

def delete_chat_session(thread_id: str) -> bool:
    """Delete a chat session from storage."""
    chats = load_all_chats()
    if thread_id in chats:
        del chats[thread_id]
        return save_all_chats(chats)
    return False

def get_history_for_langchain(thread_id: str) -> List[Dict[str, str]]:
    """Convert stored messages to LangChain compatible list of dicts for OrchestratorAgent memory."""
    session = get_chat_session(thread_id)
    if not session:
        return []
    history = []
    for msg in session.get("messages", []):
        role = "user" if msg.get("sender") == "user" else "assistant"
        content = msg.get("content", "")
        history.append({"role": role, "content": content})
    return history
