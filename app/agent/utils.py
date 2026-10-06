# app/agent/utils.py

def extract_text(message) -> str:
    """
    Normalize a LangChain AIMessage's content into plain text.
    Gemini sometimes returns content as a string, and sometimes as a
    list of content blocks (e.g. [{'type': 'text', 'text': '...'}]).
    """
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()

    return str(content)