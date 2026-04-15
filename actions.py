"""
JARVIS Action Executor — Windows compatible system actions.

Execute actions IMMEDIATELY, before generating any LLM response.
Each function returns {"success": bool, "confirmation": str}.
"""

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import quote
import webbrowser

log = logging.getLogger("jarvis.actions")

DESKTOP_PATH = Path.home() / "Desktop"


async def _mark_terminal_as_jarvis(revert_after: float = 5.0):
    """Not supported natively on Windows"""
    pass

async def _revert_terminal_theme(profile_name: str):
    """Not supported natively on Windows"""
    pass


async def open_terminal(command: str = "") -> dict:
    """Open Terminal.app (cmd) and optionally run a command."""
    try:
        if command:
            cmd = f'start cmd /k "{command}"'
        else:
            cmd = 'start cmd'
        proc = await asyncio.create_subprocess_shell(cmd)
        await proc.communicate()
        return {
            "success": True,
            "confirmation": "Terminal is open, sir.",
        }
    except Exception as e:
        log.error(f"open_terminal failed: {e}")
        return {
            "success": False,
            "confirmation": "I had trouble opening Terminal, sir."
        }


async def open_browser(url: str, browser: str = "chrome") -> dict:
    """Open URL in user's browser."""
    try:
        webbrowser.open(url)
        success = True
    except Exception as e:
        log.error(f"open_browser failed: {e}")
        success = False

    return {
        "success": success,
        "confirmation": f"Pulled that up, sir." if success else f"The browser ran into a problem, sir.",
    }


# Keep backward compat
async def open_chrome(url: str) -> dict:
    return await open_browser(url, "chrome")


async def open_claude_in_project(project_dir: str, prompt: str) -> dict:
    """Open Terminal, cd to project dir, run Claude Code interactively."""
    claude_md = Path(project_dir) / "CLAUDE.md"
    claude_md.write_text(f"# Task\n\n{prompt}\n\nBuild this completely. If web app, make index.html work standalone.\n")

    try:
        cmd = f'start cmd /k "cd /d {project_dir} && claude --dangerously-skip-permissions"'
        proc = await asyncio.create_subprocess_shell(cmd)
        await proc.communicate()
        success = True
    except Exception as e:
        log.error(f"open_claude_in_project failed: {e}")
        success = False

    return {
        "success": success,
        "confirmation": "Claude Code is running in Terminal, sir. You can watch the progress." 
        if success else "Had trouble spawning Claude Code, sir.",
    }


async def prompt_existing_terminal(project_name: str, prompt: str) -> dict:
    """Injecting keystrokes into existing windows is complex on Windows. Just returns error."""
    return {
        "success": False,
        "confirmation": f"Injecting to existing terminals is not natively supported on Windows, sir."
    }


async def get_chrome_tab_info() -> dict:
    """Cannot easily read Chrome tabs natively on Windows."""
    return {}


async def monitor_build(project_dir: str, ws=None, synthesize_fn=None) -> None:
    """Monitor a Claude Code build for completion. Notify via WebSocket when done."""
    import base64

    output_file = Path(project_dir) / ".jarvis_output.txt"
    start = time.time()
    timeout = 600  # 10 minutes

    while time.time() - start < timeout:
        await asyncio.sleep(5)
        if output_file.exists():
            content = output_file.read_text()
            if "--- JARVIS TASK COMPLETE ---" in content:
                log.info(f"Build complete in {project_dir}")
                if ws and synthesize_fn:
                    try:
                        msg = "The build is complete, sir."
                        audio_bytes = await synthesize_fn(msg)
                        if audio_bytes:
                            encoded = base64.b64encode(audio_bytes).decode()
                            await ws.send_json({"type": "status", "state": "speaking"})
                            await ws.send_json({"type": "audio", "data": encoded, "text": msg})
                            await ws.send_json({"type": "status", "state": "idle"})
                    except Exception as e:
                        log.warning(f"Build notification failed: {e}")
                return

    log.warning(f"Build timed out in {project_dir}")


async def execute_action(intent: dict, projects: list = None) -> dict:
    """Route a classified intent to the right action function."""
    action = intent.get("action", "chat")
    target = intent.get("target", "")

    if action == "open_terminal":
        result = await open_terminal("claude --dangerously-skip-permissions")
        result["project_dir"] = None
        return result

    elif action == "browse":
        if target.startswith("http://") or target.startswith("https://"):
            url = target
        else:
            url = f"https://www.google.com/search?q={quote(target)}"

        target_lower = target.lower()
        browser = "firefox" if "firefox" in target_lower else "chrome"

        result = await open_browser(url, browser)
        result["project_dir"] = None
        return result

    elif action == "build":
        project_name = _generate_project_name(target)
        project_dir = str(DESKTOP_PATH / project_name)
        os.makedirs(project_dir, exist_ok=True)
        result = await open_claude_in_project(project_dir, target)
        result["project_dir"] = project_dir
        return result

    else:
        return {"success": False, "confirmation": "", "project_dir": None}


def _generate_project_name(prompt: str) -> str:
    quoted = re.search(r'"([^"]+)"', prompt)
    if quoted:
        name = quoted.group(1).strip()
        name = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip()
        if name:
            return re.sub(r"[\s]+", "-", name.lower())

    called = re.search(r'(?:called|named)\s+(\S+(?:[-_]\S+)*)', prompt, re.IGNORECASE)
    if called:
        name = re.sub(r"[^a-zA-Z0-9-]", "", called.group(1))
        if len(name) > 3:
            return name.lower()

    words = re.sub(r"[^a-zA-Z0-9\s]", "", prompt.lower()).split()
    skip = {"a", "the", "an", "me", "build", "create", "make", "for", "with", "and",
            "to", "of", "i", "want", "need", "new", "project", "directory", "called",
            "on", "desktop", "that", "application", "app", "full", "stack", "simple",
            "web", "page", "site", "named"}
    meaningful = [w for w in words if w not in skip and len(w) > 2][:4]
    return "-".join(meaningful) if meaningful else "jarvis-project"
