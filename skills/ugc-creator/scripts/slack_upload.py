#!/usr/bin/env python3
"""Upload a file to a Slack channel/thread using the v2 upload API."""

import os
import sys
import json
import requests
from pathlib import Path


def upload_to_slack(file_path: str, channel_id: str, thread_ts: str = None, comment: str = None) -> bool:
    """Upload a file to Slack using the getUploadURLExternal flow."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN not set")
        return False

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False

    file_size = file_path.stat().st_size
    filename = file_path.name

    # Step 1: Get upload URL
    resp = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers={"Authorization": f"Bearer {token}"},
        data={"filename": filename, "length": file_size},
    )
    data = resp.json()
    if not data.get("ok"):
        print(f"Error getting upload URL: {data}")
        return False

    upload_url = data["upload_url"]
    file_id = data["file_id"]

    # Step 2: Upload file content
    with open(file_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {token}"},
            data=f,
        )
    if "OK" not in upload_resp.text:
        print(f"Error uploading file: {upload_resp.text}")
        return False

    # Step 3: Complete upload and share to channel
    payload = {
        "files": [{"id": file_id}],
        "channel_id": channel_id,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if comment:
        payload["initial_comment"] = comment

    complete_resp = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    result = complete_resp.json()
    if not result.get("ok"):
        print(f"Error completing upload: {result}")
        return False

    print(f"✅ Uploaded {filename} to Slack channel {channel_id}")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload file to Slack")
    parser.add_argument("file", help="Path to file")
    parser.add_argument("channel", help="Slack channel ID")
    parser.add_argument("--thread", help="Thread timestamp (thread_ts)")
    parser.add_argument("--comment", help="Initial comment")
    args = parser.parse_args()

    # Load env
    env_file = Path.home() / ".clawdbot" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ.setdefault(key, value)

    success = upload_to_slack(args.file, args.channel, args.thread, args.comment)
    sys.exit(0 if success else 1)
