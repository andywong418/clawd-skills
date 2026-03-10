#!/usr/bin/env python3
"""
Meme Format Remixer

Apply a known meme format with new content (face, text, etc.)

Usage:
    python remix_format.py --format what-did-you-expect --face celebrity.jpg --text "a PhD?"
    python remix_format.py --format pov-format --face myface.jpg --text "POV: you just deployed on Friday"
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

FORMATS_PATH = Path(__file__).parent.parent / 'formats' / 'formats.json'
ASSETS_PATH = Path(__file__).parent.parent / 'assets'


def load_format(format_id):
    """Load a specific format definition."""
    with open(FORMATS_PATH) as f:
        formats = json.load(f)['formats']
    
    for fmt in formats:
        if fmt['id'] == format_id:
            return fmt
    return None


def add_text_overlay(video_path, text, position='bottom', output_path=None):
    """Add text overlay to video using ffmpeg."""
    if output_path is None:
        output_path = tempfile.mktemp(suffix='.mp4')
    
    # Escape special characters for ffmpeg drawtext
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")
    
    # Position presets
    positions = {
        'top': 'x=(w-text_w)/2:y=50',
        'center': 'x=(w-text_w)/2:y=(h-text_h)/2',
        'bottom': 'x=(w-text_w)/2:y=h-text_h-50',
    }
    pos = positions.get(position, positions['bottom'])
    
    filter_str = (
        f"drawtext=text='{escaped_text}':"
        f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
        f"{pos}"
    )
    
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vf', filter_str,
        '-c:a', 'copy',
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


def create_split_screen(left_path, right_path, output_path, labels=None):
    """Create side-by-side comparison video/image."""
    # Detect if inputs are videos or images
    left_ext = Path(left_path).suffix.lower()
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    is_video = left_ext in video_exts
    
    if is_video:
        # Video side by side
        filter_complex = (
            "[0:v]scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2[left];"
            "[1:v]scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2[right];"
            "[left][right]hstack=inputs=2[out]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', left_path,
            '-i', right_path,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-c:v', 'libx264',
            '-shortest',
            output_path
        ]
    else:
        # Image side by side
        filter_complex = (
            "[0:v]scale=540:-1[left];"
            "[1:v]scale=540:-1[right];"
            "[left][right]hstack=inputs=2[out]"
        )
        cmd = [
            'ffmpeg', '-y',
            '-i', left_path,
            '-i', right_path,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True)
    
    # Add labels if provided
    if labels and os.path.exists(output_path):
        temp_out = tempfile.mktemp(suffix=Path(output_path).suffix)
        left_label, right_label = labels
        
        filter_str = (
            f"drawtext=text='{left_label}':x=135:y=30:fontsize=36:fontcolor=white:borderw=2:bordercolor=black,"
            f"drawtext=text='{right_label}':x=675:y=30:fontsize=36:fontcolor=white:borderw=2:bordercolor=black"
        )
        
        if is_video:
            cmd = ['ffmpeg', '-y', '-i', output_path, '-vf', filter_str, '-c:a', 'copy', temp_out]
        else:
            cmd = ['ffmpeg', '-y', '-i', output_path, '-vf', filter_str, temp_out]
        
        subprocess.run(cmd, capture_output=True)
        os.rename(temp_out, output_path)
    
    return output_path


def remix_what_did_you_expect(source_clip, x_variable, output_path, face_path=None):
    """Create a 'What did you expect' format meme."""
    text = f"What did you expect, a {x_variable}?"
    
    # If face swap requested, do that first
    if face_path:
        from face_swap import FaceSwapper
        temp_swapped = tempfile.mktemp(suffix='.mp4')
        swapper = FaceSwapper()
        swapper.swap_video(face_path, source_clip, temp_swapped)
        source_clip = temp_swapped
    
    result = add_text_overlay(source_clip, text, position='bottom', output_path=output_path)
    return result


def remix_pov(background_clip, scenario_text, output_path, face_path=None):
    """Create a POV format meme."""
    text = f"POV: {scenario_text}"
    
    if face_path:
        from face_swap import FaceSwapper
        temp_swapped = tempfile.mktemp(suffix='.mp4')
        swapper = FaceSwapper()
        swapper.swap_video(face_path, background_clip, temp_swapped)
        background_clip = temp_swapped
    
    result = add_text_overlay(background_clip, text, position='top', output_path=output_path)
    return result


def main():
    parser = argparse.ArgumentParser(description='Remix a meme format')
    parser.add_argument('--format', '-f', required=True, help='Format ID to use')
    parser.add_argument('--source', '-s', help='Source clip/image')
    parser.add_argument('--face', help='Face image for face swap')
    parser.add_argument('--text', '-t', help='Text content (meaning depends on format)')
    parser.add_argument('--left', help='Left panel (for split formats)')
    parser.add_argument('--right', help='Right panel (for split formats)')
    parser.add_argument('--output', '-o', required=True, help='Output path')
    parser.add_argument('--list', '-l', action='store_true', help='List available formats')
    args = parser.parse_args()
    
    if args.list:
        with open(FORMATS_PATH) as f:
            formats = json.load(f)['formats']
        for fmt in formats:
            print(f"{fmt['id']}: {fmt['name']}")
        return
    
    fmt = load_format(args.format)
    if not fmt:
        print(f"Unknown format: {args.format}")
        print("Use --list to see available formats")
        return
    
    print(f"Remixing format: {fmt['name']}")
    print(f"Description: {fmt['description']}")
    
    # Route to appropriate remix function
    if args.format == 'what-did-you-expect':
        if not args.source or not args.text:
            print("This format requires --source (clip) and --text (the X variable)")
            return
        result = remix_what_did_you_expect(args.source, args.text, args.output, args.face)
        
    elif args.format == 'pov-format':
        if not args.source or not args.text:
            print("This format requires --source (clip) and --text (the scenario)")
            return
        result = remix_pov(args.source, args.text, args.output, args.face)
        
    elif args.format == 'side-by-side-comparison':
        if not args.left or not args.right:
            print("This format requires --left and --right panels")
            return
        labels = None
        if args.text:
            # Expect format: "left_label|right_label"
            if '|' in args.text:
                labels = args.text.split('|', 1)
        result = create_split_screen(args.left, args.right, args.output, labels)
    
    else:
        print(f"Remix function not implemented for {args.format}")
        print("Available remix functions: what-did-you-expect, pov-format, side-by-side-comparison")
        return
    
    print(f"Output: {result}")


if __name__ == '__main__':
    main()
