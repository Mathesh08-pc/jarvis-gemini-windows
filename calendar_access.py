"""
JARVIS Calendar Access — Stub for Windows
"""

async def get_todays_events() -> list:
    return []

async def get_upcoming_events() -> list:
    return []

async def get_next_event() -> dict | None:
    return None

def format_events_for_context(events: list) -> str:
    return "No calendar data available."

def format_schedule_summary(events: list) -> str:
    return "Schedule is empty, sir."

def refresh_cache():
    pass
