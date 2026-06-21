#!/usr/bin/env python3
"""
Claude Code Hook Handler
Cross-platform sound notification system for Claude Code events.
Plays audio feedback for various hook events (PreToolUse, PostToolUse, Stop, etc.)

Usage: Called automatically by Claude Code via settings.json hooks configuration.
Environment variables are provided by Claude Code:
  - CLAUDE_HOOK_EVENT: The hook event type
  - CLAUDE_TOOL_NAME: The tool being used (for PreToolUse/PostToolUse)
  - CLAUDE_PROJECT_DIR: The project directory
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def get_hooks_dir() -> Path:
    """Get the hooks directory path."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    return Path(project_dir) / ".claude" / "hooks"


def load_config() -> dict:
    """Load hooks configuration with local overrides."""
    hooks_dir = get_hooks_dir()
    config_dir = hooks_dir / "config"

    # Load base config
    config_file = config_dir / "hooks-config.json"
    config = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

    # Load local overrides (git-ignored)
    local_config_file = config_dir / "hooks-config.local.json"
    if local_config_file.exists():
        with open(local_config_file, "r", encoding="utf-8") as f:
            local_config = json.load(f)
            config.update(local_config)

    return config


def play_sound(sound_file: Path) -> None:
    """Play a sound file cross-platform."""
    if not sound_file.exists():
        return

    system = platform.system()
    try:
        if system == "Windows":
            # Use PowerShell to play sound on Windows
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f'(New-Object Media.SoundPlayer "{sound_file}").PlaySync()',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Darwin":
            # macOS
            subprocess.Popen(
                ["afplay", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Linux":
            # Linux - try aplay first, then paplay
            try:
                subprocess.Popen(
                    ["aplay", "-q", str(sound_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                subprocess.Popen(
                    ["paplay", str(sound_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass  # Silently fail if sound cannot be played


def get_sound_file(event: str, tool_name: str = "") -> Path | None:
    """Get the appropriate sound file for an event."""
    hooks_dir = get_hooks_dir()
    sounds_dir = hooks_dir / "sounds"

    # Special handling for git commits
    if event == "PreToolUse" and tool_name and "git" in tool_name.lower():
        git_sound = sounds_dir / "pretooluse" / "pretooluse-git-committing.mp3"
        if git_sound.exists():
            return git_sound
        git_wav = sounds_dir / "pretooluse" / "pretooluse-git-committing.wav"
        if git_wav.exists():
            return git_wav

    # Map event to directory
    event_dir = event.lower()
    sound_dir = sounds_dir / event_dir

    if not sound_dir.exists():
        return None

    # Try mp3 first, then wav
    for ext in [".mp3", ".wav"]:
        sound_file = sound_dir / f"{event_dir}{ext}"
        if sound_file.exists():
            return sound_file

    return None


def main():
    """Main hook handler entry point."""
    # Get hook event from environment
    event = os.environ.get("CLAUDE_HOOK_EVENT", "")
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")

    if not event:
        return

    # Load configuration
    config = load_config()

    # Check if hooks are globally disabled
    if config.get("disabled", False):
        return

    # Check if this specific event is disabled
    event_config = config.get("events", {})
    if not event_config.get(event, {}).get("enabled", True):
        return

    # Check if sound is enabled for this event
    if not event_config.get(event, {}).get("sound", True):
        return

    # Find and play sound
    sound_file = get_sound_file(event, tool_name)
    if sound_file:
        play_sound(sound_file)


if __name__ == "__main__":
    main()
