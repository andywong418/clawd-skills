#!/usr/bin/env python3
"""Brand voice trainer — manages structured config (API) and fuzzy style memories (local)."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

API_URL = os.environ.get("VIRALFARM_API_URL", "http://localhost:3000")
API_KEY = os.environ.get("VIRALFARM_API_KEY", "")
MEMORY_DIR = Path(__file__).resolve().parents[3] / "memory" / "brand"
STYLE_FILE = MEMORY_DIR / "style.md"


def api_request(method: str, path: str, data: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode()
        print(f"API error ({e.code}): {err_body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def get_config() -> dict:
    return api_request("GET", "/brand-voice")


def update_config(brand_voice: dict | None = None, brand_formats: dict | None = None) -> dict:
    payload = {}
    if brand_voice is not None:
        payload["brandVoice"] = brand_voice
    if brand_formats is not None:
        payload["brandFormats"] = brand_formats
    return api_request("PUT", "/brand-voice", payload)


def cmd_show(args):
    config = get_config()
    if args.json:
        print(json.dumps(config, indent=2))
        return

    bv = config.get("brandVoice") or {}
    bf = config.get("brandFormats") or {}

    print("═══ Brand Voice ═══")
    if not bv:
        print("  (not configured)")
    else:
        for key in ["name", "description", "tone", "targetAudience", "productInfo"]:
            if bv.get(key):
                label = key.replace("targetAudience", "audience").replace("productInfo", "product info")
                print(f"  {label}: {bv[key]}")
        if bv.get("vocabulary"):
            print(f"  vocabulary: {', '.join(bv['vocabulary'])}")
        if bv.get("avoidWords"):
            print(f"  avoid: {', '.join(bv['avoidWords'])}")
        if bv.get("samplePosts"):
            print(f"  samples ({len(bv['samplePosts'])}):")
            for s in bv["samplePosts"]:
                print(f"    - {s}")

    if bf:
        print("\n═══ Format Rules ═══")
        for platform, rules in bf.items():
            print(f"\n  [{platform}]")
            if rules.get("style"):
                print(f"    style: {rules['style']}")
            if rules.get("rules"):
                for r in rules["rules"]:
                    print(f"    • {r}")
            if rules.get("examples"):
                for e in rules["examples"]:
                    print(f"    ex: {e}")

    # Show style memories if they exist
    if STYLE_FILE.exists():
        memories = STYLE_FILE.read_text().strip()
        if memories:
            print("\n═══ Style Memories ═══")
            print(memories)


def cmd_set(args):
    bv = {}
    if args.name:
        bv["name"] = args.name
    if args.tone:
        bv["tone"] = args.tone
    if args.description:
        bv["description"] = args.description
    if args.audience:
        bv["targetAudience"] = args.audience
    if args.product_info:
        bv["productInfo"] = args.product_info

    if not bv:
        print("No fields specified. Use --name, --tone, --description, --audience, --product-info")
        sys.exit(1)

    result = update_config(brand_voice=bv)
    print("Updated brand voice:")
    print(json.dumps(result.get("brandVoice", {}), indent=2))


def cmd_vocabulary(args):
    config = get_config()
    bv = config.get("brandVoice") or {}

    vocab = list(bv.get("vocabulary") or [])
    avoid = list(bv.get("avoidWords") or [])

    if args.add:
        new_words = [w.strip() for w in args.add.split(",") if w.strip()]
        vocab = list(set(vocab + new_words))
    if args.remove:
        rm_words = {w.strip() for w in args.remove.split(",")}
        vocab = [w for w in vocab if w not in rm_words]
    if args.avoid:
        new_avoid = [w.strip() for w in args.avoid.split(",") if w.strip()]
        avoid = list(set(avoid + new_avoid))
    if args.unavoid:
        rm_avoid = {w.strip() for w in args.unavoid.split(",")}
        avoid = [w for w in avoid if w not in rm_avoid]

    result = update_config(brand_voice={"vocabulary": vocab, "avoidWords": avoid})
    bv = result.get("brandVoice", {})
    print(f"Vocabulary: {', '.join(bv.get('vocabulary', []))}")
    print(f"Avoid: {', '.join(bv.get('avoidWords', []))}")


def cmd_samples(args):
    config = get_config()
    bv = config.get("brandVoice") or {}
    samples = list(bv.get("samplePosts") or [])

    if args.add:
        samples.append(args.add)
    if args.clear:
        samples = []

    result = update_config(brand_voice={"samplePosts": samples})
    updated = result.get("brandVoice", {}).get("samplePosts", [])
    print(f"Sample posts ({len(updated)}):")
    for s in updated:
        print(f"  - {s}")


def cmd_format(args):
    fmt: dict = {}
    if args.style:
        fmt["style"] = args.style
    if args.rules:
        fmt["rules"] = args.rules
    if args.examples:
        fmt["examples"] = args.examples

    if not fmt:
        # Show current format config
        config = get_config()
        bf = config.get("brandFormats") or {}
        pf = bf.get(args.platform)
        if pf:
            print(f"[{args.platform}]")
            print(json.dumps(pf, indent=2))
        else:
            print(f"No format rules set for {args.platform}")
        return

    result = update_config(brand_formats={args.platform: fmt})
    pf = (result.get("brandFormats") or {}).get(args.platform, {})
    print(f"Updated [{args.platform}]:")
    print(json.dumps(pf, indent=2))


def cmd_remember(args):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    text = args.text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{timestamp}] {text}\n"

    with open(STYLE_FILE, "a") as f:
        f.write(entry)

    print(f"Saved style memory: {text}")


def cmd_memories(args):
    if not STYLE_FILE.exists():
        print("No style memories yet. Use 'remember' to add some.")
        return

    content = STYLE_FILE.read_text().strip()
    if not content:
        print("No style memories yet.")
        return

    print("═══ Style Memories ═══")
    print(content)


def main():
    parser = argparse.ArgumentParser(description="Brand voice trainer")
    sub = parser.add_subparsers(dest="command")

    # show
    p_show = sub.add_parser("show", help="Display current brand voice config")
    p_show.add_argument("--json", action="store_true", help="Output raw JSON")

    # set
    p_set = sub.add_parser("set", help="Set brand voice fields")
    p_set.add_argument("--name", help="Brand name")
    p_set.add_argument("--tone", help="Brand tone/voice description")
    p_set.add_argument("--description", help="Brand description")
    p_set.add_argument("--audience", help="Target audience")
    p_set.add_argument("--product-info", help="Product information")

    # vocabulary
    p_vocab = sub.add_parser("vocabulary", help="Manage vocabulary and avoid words")
    p_vocab.add_argument("--add", help="Comma-separated words to add to vocabulary")
    p_vocab.add_argument("--remove", help="Comma-separated words to remove from vocabulary")
    p_vocab.add_argument("--avoid", help="Comma-separated words to add to avoid list")
    p_vocab.add_argument("--unavoid", help="Comma-separated words to remove from avoid list")

    # samples
    p_samples = sub.add_parser("samples", help="Manage sample posts")
    p_samples.add_argument("--add", help="Add a sample post")
    p_samples.add_argument("--clear", action="store_true", help="Clear all samples")

    # format
    p_format = sub.add_parser("format", help="Set format-specific rules")
    p_format.add_argument("platform", help="Platform name (instagram, tiktok, twitter, youtube)")
    p_format.add_argument("--style", help="Format style description")
    p_format.add_argument("--rules", nargs="+", help="Format rules")
    p_format.add_argument("--examples", nargs="+", help="Example posts for this format")

    # remember
    p_remember = sub.add_parser("remember", help="Save a style memory")
    p_remember.add_argument("text", help="Style preference to remember")

    # memories
    sub.add_parser("memories", help="List style memories")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "show": cmd_show,
        "set": cmd_set,
        "vocabulary": cmd_vocabulary,
        "samples": cmd_samples,
        "format": cmd_format,
        "remember": cmd_remember,
        "memories": cmd_memories,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
