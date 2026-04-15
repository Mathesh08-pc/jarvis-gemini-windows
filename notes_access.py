"""
JARVIS Notes Access — Stub for Windows
"""

async def get_recent_notes(limit: int = 5) -> list:
    return []

async def read_note(name: str) -> str | None:
    return "Notes access is not supported on Windows, sir."

async def search_notes_apple(query: str, limit: int = 5) -> list:
    return []

async def create_apple_note(name: str, body: str, folder: str = "") -> dict:
    return {"success": False, "error": "Not supported on Windows"}
