#!/usr/bin/env python3
"""
Discord webhook sender for triggering GitHub Actions workflows.
This script can be used to send commands to the bucket system via Discord webhooks.
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
GITHUB_REPO = "yourusername/bucket"  # Update this with your actual repo
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this as an environment variable

def send_discord_command(command, args=None, user="Discord User", channel="Discord Channel"):
    """Send a Discord command to trigger a GitHub workflow."""
    
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        return False
    
    if not args:
        args = []
    
    payload = {
        "event_type": "discord_command",
        "client_payload": {
            "command": command,
            "args": args,
            "user": user,
            "channel": channel,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully triggered {command} command")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending command: {e}")
        return False

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python discord-webhook-sender.py <command> [args...]")
        print("Examples:")
        print("  python discord-webhook-sender.py add https://example.com")
        print("  python discord-webhook-sender.py feeds list")
        print("  python discord-webhook-sender.py status")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    success = send_discord_command(command, args)
    if success:
        print(f"Command '{command}' sent successfully!")
    else:
        print(f"Failed to send command '{command}'")

if __name__ == "__main__":
    main()
