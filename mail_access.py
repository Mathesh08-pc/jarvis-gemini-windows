"""
JARVIS Mail Access — Stub for Windows
"""

async def get_unread_count() -> int:
    return 0

async def get_unread_messages() -> list:
    return []

async def get_recent_messages(limit: int = 5) -> list:
    return []

async def search_mail(query: str, limit: int = 5) -> list:
    return []

async def read_message(message_id: str) -> str | None:
    return "Mail access is not supported on Windows, sir."

def format_unread_summary(count: int, messages: list) -> str:
    return "No new mail, sir."

def format_messages_for_context(messages: list) -> str:
    return "No mail data."

def format_messages_for_voice(messages: list) -> str:
    return "Inbox is clear, sir."
