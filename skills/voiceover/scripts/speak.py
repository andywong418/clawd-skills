#!/usr/bin/env python3
"""Voiceover — convert text to speech via the ViralFarm API.

Models:
  kokoro      Fast, free, 50+ voices across English/Spanish/French/Japanese/etc.
  minimax     Higher quality, emotional control, $0.10/1k chars

Usage:
    # Basic
    python3 speak.py "Welcome to the future of AI."

    # From file
    python3 speak.py --file script.txt

    # Pick voice/model
    python3 speak.py "Let's go!" --voice am_michael --model kokoro
    python3 speak.py "Breaking news." --voice Deep_Voice_Man --model minimax

    # With emotion (minimax only)
    python3 speak.py "I can't believe it!" --voice Lively_Girl --emotion surprised

    # Pipe into video-editor
    python3 speak.py "Subscribe for more." --output ./audio/cta.mp3

    # Submit without waiting
    python3 speak.py "Hello world" --no-wait

    # Check job status
    python3 speak.py --status <job-id>

    # Check credits
    python3 speak.py --credits
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ---------------------------------------------------------------------------
# Voice reference
# ---------------------------------------------------------------------------

KOKORO_VOICES = {
    # American English
    "af_heart":   "Female, warm (default)",
    "af_bella":   "Female, expressive",
    "af_nova":    "Female, professional",
    "af_sarah":   "Female, friendly",
    "af_sky":     "Female, bright",
    "am_michael": "Male, authoritative",
    "am_liam":    "Male, casual",
    "am_echo":    "Male, smooth",
    "am_eric":    "Male, conversational",
    # British English
    "bf_emma":    "Female British, polished",
    "bf_alice":   "Female British, warm",
    "bm_george":  "Male British, deep",
    "bm_daniel":  "Male British, crisp",
}

MINIMAX_VOICES = {
    "Friendly_Person":    "Upbeat, approachable",
    "Wise_Woman":         "Calm, authoritative (default)",
    "Inspirational_girl": "Energetic, motivating",
    "Deep_Voice_Man":     "Deep, powerful",
    "Calm_Woman":         "Soothing, measured",
    "Casual_Guy":         "Relaxed, conversational",
    "Lively_Girl":        "Bright, enthusiastic",
}

MINIMAX_EMOTIONS = ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]

# Defaults per model
DEFAULTS = {
    "kokoro":  {"voice": "af_heart"},
    "minimax": {"voice": "Friendly_Person"},
}


# ---------------------------------------------------------------------------
# Config / API helpers
# ---------------------------------------------------------------------------

def load_config():
    """Load API URL and key from environment or .env file."""
    url = os.environ.get("VIRALFARM_API_URL")
    key = os.environ.get("VIRALFARM_API_KEY")

    if url and key:
        return url, key

    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("VIRALFARM_API_URL=") and not url:
                    url = line.split("=", 1)[1].strip()
                elif line.startswith("VIRALFARM_API_KEY=") and not key:
                    key = line.split("=", 1)[1].strip()

    return url, key


def api_request(url: str, api_key: str, method: str = "GET", data: dict = None) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode()
        try:
            err = json.loads(err_body)
            msg = err.get("error", err_body)
        except json.JSONDecodeError:
            msg = err_body
        print(f"API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_file(url: str, dest: Path):
    """Download a file from URL to local path."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def poll_job(api_url: str, api_key: str, job_id: str) -> dict:
    """Poll GET /jobs/{id} until the job reaches a terminal state."""
    url = f"{api_url}/jobs/{job_id}"
    while True:
        result = api_request(url, api_key)
        status = result.get("status", "unknown")

        if status == "completed":
            return result
        elif status in ("failed", "error"):
            err = result.get("error", "Unknown error")
            print(f"Job failed: {err}", file=sys.stderr)
            sys.exit(1)
        elif status == "cancelled":
            print("Job was cancelled.", file=sys.stderr)
            sys.exit(1)

        print(f"[voiceover] Status: {status} — waiting...")
        time.sleep(2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def list_voices():
    print("\nKokoro voices (--model kokoro):")
    for name, desc in KOKORO_VOICES.items():
        print(f"  {name:<20} {desc}")
    print("\nMiniMax voices (--model minimax):")
    for name, desc in MINIMAX_VOICES.items():
        print(f"  {name:<22} {desc}")
    print(f"\nMiniMax emotions: {', '.join(MINIMAX_EMOTIONS)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover audio from text")
    parser.add_argument("text", nargs="?", help="Text to speak")
    parser.add_argument("--file", "-f", help="Read text from file instead")
    parser.add_argument("--model", default="kokoro", choices=["kokoro", "minimax"],
                        help="TTS model (default: kokoro)")
    parser.add_argument("--voice", "-v", help="Voice ID (see --list-voices for options)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speaking speed 0.5-2.0 (default: 1.0)")
    parser.add_argument("--emotion", choices=MINIMAX_EMOTIONS,
                        help="Emotion (minimax only)")
    parser.add_argument("--output", "-o", default="./output/voiceover.mp3",
                        help="Output MP3 path (default: ./output/voiceover.mp3)")
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit the job and exit without waiting")
    parser.add_argument("--status", metavar="JOB_ID",
                        help="Check status of an existing job")
    parser.add_argument("--credits", action="store_true",
                        help="Show remaining API credits and exit")
    parser.add_argument("--list-voices", action="store_true",
                        help="Print all available voices and exit")
    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        return

    # --- Load API config ---
    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("ERROR: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
              "in environment or ~/.clawdbot/.env", file=sys.stderr)
        sys.exit(1)

    api_url = api_url.rstrip("/")

    # --- Credits ---
    if args.credits:
        result = api_request(f"{api_url}/credits", api_key)
        print(json.dumps(result, indent=2))
        return

    # --- Status check ---
    if args.status:
        result = api_request(f"{api_url}/jobs/{args.status}", api_key)
        print(json.dumps(result, indent=2))
        return

    # --- Get text ---
    if args.file:
        text = Path(args.file).read_text().strip()
    elif args.text:
        text = args.text.strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not text:
        print("ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    # Voice default
    voice = args.voice or DEFAULTS[args.model]["voice"]

    # Validate voice for model
    if args.model == "kokoro" and voice not in KOKORO_VOICES:
        print(f"WARNING: '{voice}' not in known Kokoro voices — proceeding anyway")
    if args.model == "minimax" and voice not in MINIMAX_VOICES:
        print(f"WARNING: '{voice}' not in known MiniMax voices — proceeding anyway")

    # Output path
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[voiceover] Text: {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"[voiceover] Model: {args.model}, Voice: {voice}, Speed: {args.speed}x"
          + (f", Emotion: {args.emotion}" if args.emotion else ""))
    print(f"[voiceover] Output: {out_path}")

    # --- Submit job ---
    payload = {
        "text": text,
        "model": args.model,
        "voice": voice,
        "speed": args.speed,
    }
    if args.emotion:
        payload["emotion"] = args.emotion

    start = time.time()
    result = api_request(f"{api_url}/voiceover", api_key, method="POST", data=payload)
    job_id = result.get("id") or result.get("jobId")

    if not job_id:
        print(f"ERROR: no job ID in response: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"[voiceover] Job submitted: {job_id}")

    # --- No-wait mode ---
    if args.no_wait:
        print(json.dumps(result, indent=2))
        return

    # --- Poll until complete ---
    result = poll_job(api_url, api_key, job_id)

    # --- Download audio ---
    output = result.get("output", {})
    audio_url = output.get("audioUrl")
    if not audio_url:
        print(f"ERROR: no audioUrl in job output: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"[voiceover] Downloading audio...")
    download_file(audio_url, out_path)

    elapsed = time.time() - start
    size_kb = out_path.stat().st_size // 1024
    print(f"[voiceover] Done in {elapsed:.1f}s — {out_path} ({size_kb}KB)")
    print(out_path)


if __name__ == "__main__":
    main()
