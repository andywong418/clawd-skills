#!/usr/bin/env python3
"""One-time YouTube OAuth2 setup.

Run this once to get a refresh token and save it to ~/.clawdbot/.env.
After that, youtube.py uses the refresh token automatically.

Requirements:
  1. Google Cloud project with YouTube Data API v3 enabled
  2. OAuth2 credentials (Desktop app type) — client_id + client_secret

Setup:
  1. Go to https://console.cloud.google.com
  2. Create a project → Enable "YouTube Data API v3"
  3. APIs & Services → Credentials → Create OAuth Client ID → Desktop app
  4. Download the JSON or note the client_id and client_secret
  5. Run this script
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
ENV_PATH = Path.home() / ".clawdbot" / ".env"


def save_to_env(key: str, value: str):
    """Upsert a key=value line in ~/.clawdbot/.env."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    found = False

    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)

    # Secure permissions
    os.chmod(ENV_PATH, 0o600)


def main():
    print("YouTube OAuth2 Setup")
    print("=" * 45)
    print()

    # Check if already configured
    existing = {}
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    if all(existing.get(k) for k in ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]):
        print("YouTube credentials already configured in ~/.clawdbot/.env")
        print("  YOUTUBE_CLIENT_ID: " + existing["YOUTUBE_CLIENT_ID"][:20] + "...")
        print("  YOUTUBE_REFRESH_TOKEN: " + existing["YOUTUBE_REFRESH_TOKEN"][:20] + "...")
        redo = input("\nRe-authorize? (y/N): ").strip().lower()
        if redo != "y":
            print("Keeping existing credentials.")
            return

    # Get client credentials
    print("Enter your Google OAuth2 credentials.")
    print("(From Google Cloud Console → APIs & Services → Credentials)\n")

    client_id = existing.get("YOUTUBE_CLIENT_ID", "")
    if client_id:
        print(f"Current YOUTUBE_CLIENT_ID: {client_id[:20]}...")
        use_existing = input("Use existing? (Y/n): ").strip().lower()
        if use_existing == "n":
            client_id = input("New YOUTUBE_CLIENT_ID: ").strip()
    else:
        client_id = input("YOUTUBE_CLIENT_ID: ").strip()

    client_secret = existing.get("YOUTUBE_CLIENT_SECRET", "")
    if client_secret:
        print(f"Current YOUTUBE_CLIENT_SECRET: {client_secret[:10]}...")
        use_existing = input("Use existing? (Y/n): ").strip().lower()
        if use_existing == "n":
            client_secret = input("New YOUTUBE_CLIENT_SECRET: ").strip()
    else:
        client_secret = input("YOUTUBE_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        print("Error: client_id and client_secret required", file=sys.stderr)
        sys.exit(1)

    # Save client credentials
    save_to_env("YOUTUBE_CLIENT_ID", client_id)
    save_to_env("YOUTUBE_CLIENT_SECRET", client_secret)

    # Build authorization URL
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPE,
        "access_type":   "offline",
        "prompt":        "consent",   # Force consent to always get refresh_token
    })
    auth_url = f"{AUTH_URL}?{params}"

    print()
    print("=" * 45)
    print("Open this URL in your browser:")
    print()
    print(auth_url)
    print()
    print("Sign in with the YouTube account you want to post from.")
    print("After authorizing, Google will show you an authorization code.")
    print("=" * 45)
    print()

    auth_code = input("Paste the authorization code here: ").strip()
    if not auth_code:
        print("Error: no auth code provided", file=sys.stderr)
        sys.exit(1)

    # Exchange auth code for tokens
    print("\nExchanging code for tokens...")
    data = urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "code":          auth_code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Token exchange failed {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    refresh_token = result.get("refresh_token")
    if not refresh_token:
        print(f"Error: no refresh_token in response: {result}", file=sys.stderr)
        print("Tip: try re-running with a fresh auth flow (the URL changes each time)", file=sys.stderr)
        sys.exit(1)

    save_to_env("YOUTUBE_REFRESH_TOKEN", refresh_token)

    print()
    print("=" * 45)
    print("YouTube credentials saved to ~/.clawdbot/.env")
    print(f"  YOUTUBE_CLIENT_ID:     {client_id[:20]}...")
    print(f"  YOUTUBE_CLIENT_SECRET: {client_secret[:10]}...")
    print(f"  YOUTUBE_REFRESH_TOKEN: {refresh_token[:20]}...")
    print()
    print("You can now upload to YouTube with:")
    print("  python3 skills/post-scheduler/scripts/queue.py add youtube video.mp4 \"Title\" --optimal")
    print("=" * 45)


if __name__ == "__main__":
    main()
