#!/usr/bin/env python3
"""Animate a UGC creator image to video via the ViralFarm API.

NOTE: The ViralFarm API does not expose a standalone animate endpoint.
Use create.py with --animate or call the /ugc endpoint with animate: true.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Animate UGC creator image to video (deprecated — use create.py --animate)"
    )
    parser.add_argument("image_url", help="URL or path to the source image")
    parser.add_argument("--prompt", default="", help="Motion description")
    parser.add_argument("--duration", type=int, choices=[5, 10], default=5, help="Video duration in seconds")
    parser.add_argument("--output", default="./output", help="Output directory")

    parser.parse_args()  # parse so --help still works

    print(
        "Standalone animation is not available through the ViralFarm API.\n"
        "\n"
        "To generate an animated UGC video, use one of the following:\n"
        "\n"
        "  python create.py \"your prompt\" --animate --duration 5\n"
        "\n"
        "Or call the API directly:\n"
        "\n"
        "  POST {VIRALFARM_API_URL}/ugc\n"
        '  { "prompt": "...", "gender": "female", "setting": "cafe", "animate": true, "duration": 5 }',
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
