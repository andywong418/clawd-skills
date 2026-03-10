#!/usr/bin/env python3
"""Generate images using Google's Imagen API."""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

def load_api_key():
    """Load API key from environment or .env file."""
    key = os.environ.get("GOOGLE_AI_API_KEY")
    if key:
        return key
    
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GOOGLE_AI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    
    return None

def generate_images(prompt: str, count: int = 1, model: str = "imagen-3.0-generate-002", 
                   aspect_ratio: str = "1:1") -> list[bytes]:
    """Generate images using Google's Imagen API."""
    api_key = load_api_key()
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY not found in environment or ~/.clawdbot/.env")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"
    
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": count,
            "aspectRatio": aspect_ratio,
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"API error {e.code}: {error_body}")
    
    images = []
    predictions = result.get("predictions", [])
    for pred in predictions:
        if "bytesBase64Encoded" in pred:
            images.append(base64.b64decode(pred["bytesBase64Encoded"]))
        elif "image" in pred and "bytesBase64Encoded" in pred["image"]:
            images.append(base64.b64decode(pred["image"]["bytesBase64Encoded"]))
    
    return images

def main():
    parser = argparse.ArgumentParser(description="Generate images with Google Imagen")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--count", type=int, default=1, choices=[1, 2, 3, 4],
                       help="Number of images to generate (1-4)")
    parser.add_argument("--output", type=str, default="./output",
                       help="Output directory for images")
    parser.add_argument("--model", type=str, default="imagen-4.0-generate-001",
                       help="Model: imagen-4.0-generate-001, imagen-4.0-ultra-generate-001, imagen-4.0-fast-generate-001")
    parser.add_argument("--aspect", type=str, default="1:1",
                       choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
                       help="Aspect ratio")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {args.count} image(s) with prompt: {args.prompt[:50]}...")
    
    try:
        images = generate_images(
            prompt=args.prompt,
            count=args.count,
            model=args.model,
            aspect_ratio=args.aspect
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not images:
        print("No images generated", file=sys.stderr)
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []
    
    for i, img_data in enumerate(images):
        filename = f"{timestamp}_{i}.png"
        filepath = output_dir / filename
        with open(filepath, "wb") as f:
            f.write(img_data)
        saved_paths.append(str(filepath))
        print(f"Saved: {filepath}")
    
    print(f"\nGenerated {len(saved_paths)} image(s)")

if __name__ == "__main__":
    main()
