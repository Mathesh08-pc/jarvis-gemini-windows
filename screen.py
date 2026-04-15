"""
JARVIS Screen Awareness — see what's on the user's screen.

Rewritten for Windows using PowerShell and Pillow.
"""

import asyncio
import base64
import json
import logging

log = logging.getLogger("jarvis.screen")


async def get_active_windows() -> list[dict]:
    """Get list of visible windows with app name and window title.
    Uses PowerShell on Windows.
    """
    script = "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Name, MainWindowTitle | ConvertTo-Json"
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)

        if proc.returncode != 0:
            return []

        windows = []
        out_str = stdout.decode().strip()
        if not out_str:
            return []
            
        data = json.loads(out_str)
        if isinstance(data, dict): 
            data = [data]
            
        for item in data:
            windows.append({
                "app": item.get("Name", "Unknown"),
                "title": item.get("MainWindowTitle", "Unknown"),
                "frontmost": False,
            })
        return windows

    except Exception as e:
        log.warning(f"get_active_windows error: {e}")
        return []


async def get_running_apps() -> list[str]:
    """Get list of running application names (visible only)."""
    windows = await get_active_windows()
    return list(set(w["app"] for w in windows))


async def take_screenshot(display_only: bool = True) -> str | None:
    """Take a screenshot and return base64-encoded PNG using Pillow on Windows."""
    try:
        from PIL import ImageGrab
        import io
        
        # This will run synchronously but should be fast enough for local use.
        # all_screens=True gets all monitors.
        img = ImageGrab.grab(all_screens=not display_only)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        
        log.info(f"Screenshot captured: {len(data)} bytes")
        return base64.b64encode(data).decode()

    except Exception as e:
        log.warning(f"Screenshot error: {e}")
        return None


async def describe_screen(anthropic_client) -> str:
    """Describe what's on the user's screen.
    Tries screenshot + vision first. Falls back to window list + LLM summary.
    """
    screenshot_b64 = await take_screenshot()
    if screenshot_b64 and anthropic_client:
        try:
            response = await anthropic_client.messages.create(
                model="gemini-1.5-pro",
                max_tokens=300,
                system=(
                    "You are JARVIS analyzing a screenshot of the user's desktop. "
                    "Describe what you see concisely: which apps are open, what the user "
                    "appears to be working on, any notable content visible. "
                    "Be specific about app names, file names, URLs, code, or documents visible. "
                    "2-4 sentences max. No markdown."
                ),
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "What's on my screen right now?",
                        },
                    ],
                }],
            )
            return response.content[0].text
        except Exception as e:
            log.warning(f"Vision call failed, falling back to window list: {e}")

    windows = await get_active_windows()
    apps = await get_running_apps()

    if not windows and not apps:
        return "I wasn't able to see your screen, sir. Screen recording permission may be needed."

    context_parts = []
    if windows:
        for w in windows:
            context_parts.append(f"{w['app']}: {w['title']}")

    if apps:
        window_apps = set(w["app"] for w in windows) if windows else set()
        bg_apps = [a for a in apps if a not in window_apps]
        if bg_apps:
            context_parts.append(f"Background apps: {', '.join(bg_apps)}")

    if anthropic_client and context_parts:
        try:
            response = await anthropic_client.messages.create(
                model="gemini-1.5-pro",
                max_tokens=100,
                system=(
                    "You are JARVIS. Given the user's open windows and apps, summarize "
                    "what they appear to be working on in 1-2 sentences. Natural voice, no markdown."
                ),
                messages=[{"role": "user", "content": "Open windows:\n" + "\n".join(context_parts)}],
            )
            return response.content[0].text
        except Exception:
            pass

    if windows:
        result = f"You have {len(windows)} windows open across {len(set(w['app'] for w in windows))} apps."
        return result

    return f"Running apps: {', '.join(apps)}. Couldn't read window titles, sir."


def format_windows_for_context(windows: list[dict]) -> str:
    """Format window list as context string for the LLM."""
    if not windows:
        return ""
    lines = ["Currently open on your desktop:"]
    for w in windows:
        lines.append(f"  - {w['app']}: {w['title']}")
    return "\n".join(lines)
