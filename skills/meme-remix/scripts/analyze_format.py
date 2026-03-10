#!/usr/bin/env python3
"""
Meme Format Analyzer

Analyzes images/videos to identify meme format patterns and remix opportunities.

Usage:
    python analyze_format.py <image_or_video_path_or_url>
    python analyze_format.py --list  # List known formats
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

FORMATS_PATH = Path(__file__).parent.parent / 'formats' / 'formats.json'


def load_formats():
    """Load known meme formats from database."""
    if FORMATS_PATH.exists():
        with open(FORMATS_PATH) as f:
            return json.load(f)['formats']
    return []


def list_formats():
    """Print all known formats."""
    formats = load_formats()
    print(f"\n{'='*60}")
    print("KNOWN MEME FORMATS")
    print(f"{'='*60}\n")
    
    for fmt in formats:
        print(f"📌 {fmt['name']} ({fmt['id']})")
        print(f"   {fmt['description']}")
        print(f"   Remix points: {', '.join(fmt['remix_points'].keys())}")
        print()
    
    print(f"Total: {len(formats)} formats")


def extract_frames(video_path, num_frames=5):
    """Extract key frames from video for analysis."""
    import subprocess
    
    temp_dir = tempfile.mkdtemp()
    duration_cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(duration_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 10
    
    frames = []
    for i in range(num_frames):
        timestamp = (duration / (num_frames + 1)) * (i + 1)
        output_path = os.path.join(temp_dir, f'frame_{i:03d}.jpg')
        cmd = [
            'ffmpeg', '-y', '-ss', str(timestamp), '-i', video_path,
            '-frames:v', '1', '-q:v', '2', output_path
        ]
        subprocess.run(cmd, capture_output=True)
        if os.path.exists(output_path):
            frames.append(output_path)
    
    return frames, temp_dir


def analyze_visual_structure(image_path):
    """Analyze visual structure of an image."""
    try:
        import cv2
        import numpy as np
        
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        height, width = img.shape[:2]
        
        # Detect text regions (simplified - look for high contrast areas)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Check for split screen (vertical or horizontal)
        left_half = gray[:, :width//2]
        right_half = gray[:, width//2:]
        top_half = gray[:height//2, :]
        bottom_half = gray[height//2:, :]
        
        # Compare histograms
        left_hist = cv2.calcHist([left_half], [0], None, [256], [0, 256])
        right_hist = cv2.calcHist([right_half], [0], None, [256], [0, 256])
        top_hist = cv2.calcHist([top_half], [0], None, [256], [0, 256])
        bottom_hist = cv2.calcHist([bottom_half], [0], None, [256], [0, 256])
        
        v_split_diff = cv2.compareHist(left_hist, right_hist, cv2.HISTCMP_CORREL)
        h_split_diff = cv2.compareHist(top_hist, bottom_hist, cv2.HISTCMP_CORREL)
        
        # Detect faces
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        return {
            'dimensions': f'{width}x{height}',
            'aspect_ratio': round(width / height, 2),
            'vertical_split_likely': v_split_diff < 0.7,
            'horizontal_split_likely': h_split_diff < 0.7,
            'num_faces': len(faces),
            'face_positions': [{'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)} for (x, y, w, h) in faces]
        }
    except ImportError:
        return {'error': 'opencv not installed'}


def match_format(analysis_results):
    """Match analysis results to known formats."""
    formats = load_formats()
    matches = []
    
    for fmt in formats:
        score = 0
        reasons = []
        
        # Check for split screen formats
        if fmt['id'] == 'side-by-side-comparison':
            if analysis_results.get('vertical_split_likely'):
                score += 50
                reasons.append('vertical split detected')
        
        # Check for reaction format (usually has faces)
        if fmt['id'] == 'reaction-format':
            if analysis_results.get('num_faces', 0) >= 1:
                score += 30
                reasons.append('face detected')
        
        # Check for POV format (face looking at camera)
        if fmt['id'] == 'pov-format':
            if analysis_results.get('num_faces', 0) == 1:
                faces = analysis_results.get('face_positions', [])
                if faces:
                    # Check if face is centered
                    face = faces[0]
                    center_x = face['x'] + face['w'] / 2
                    width = int(analysis_results['dimensions'].split('x')[0])
                    if abs(center_x - width/2) < width * 0.2:
                        score += 40
                        reasons.append('centered face (POV style)')
        
        if score > 0:
            matches.append({
                'format': fmt['name'],
                'id': fmt['id'],
                'score': score,
                'reasons': reasons,
                'remix_points': list(fmt['remix_points'].keys())
            })
    
    return sorted(matches, key=lambda x: x['score'], reverse=True)


def analyze(path_or_url):
    """Main analysis function."""
    # Download if URL
    path = path_or_url
    is_temp = False
    
    if path.startswith(('http://', 'https://')):
        import requests
        ext = Path(path).suffix or '.tmp'
        if not ext or len(ext) > 5:
            ext = '.mp4'  # Default to video
        temp_path = tempfile.mktemp(suffix=ext)
        print(f"Downloading {path}...")
        response = requests.get(path, stream=True)
        response.raise_for_status()
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        path = temp_path
        is_temp = True
    
    try:
        ext = Path(path).suffix.lower()
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        
        results = {
            'input': path_or_url,
            'type': 'video' if ext in video_exts else 'image',
            'frames_analyzed': [],
            'visual_analysis': None,
            'format_matches': []
        }
        
        if ext in video_exts:
            print("Extracting key frames...")
            frames, temp_dir = extract_frames(path)
            results['frames_analyzed'] = len(frames)
            
            # Analyze middle frame as representative
            if frames:
                mid_frame = frames[len(frames) // 2]
                results['visual_analysis'] = analyze_visual_structure(mid_frame)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
        else:
            results['visual_analysis'] = analyze_visual_structure(path)
        
        if results['visual_analysis']:
            results['format_matches'] = match_format(results['visual_analysis'])
        
        return results
        
    finally:
        if is_temp and os.path.exists(path):
            os.remove(path)


def main():
    parser = argparse.ArgumentParser(description='Analyze meme format')
    parser.add_argument('input', nargs='?', help='Image or video path/URL')
    parser.add_argument('--list', '-l', action='store_true', help='List known formats')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    if args.list:
        list_formats()
        return
    
    if not args.input:
        parser.print_help()
        return
    
    results = analyze(args.input)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*60}")
        print("MEME FORMAT ANALYSIS")
        print(f"{'='*60}\n")
        
        print(f"Type: {results['type']}")
        if results['visual_analysis']:
            va = results['visual_analysis']
            print(f"Dimensions: {va.get('dimensions', 'unknown')}")
            print(f"Faces detected: {va.get('num_faces', 0)}")
            if va.get('vertical_split_likely'):
                print("📊 Split screen (vertical) detected")
            if va.get('horizontal_split_likely'):
                print("📊 Split screen (horizontal) detected")
        
        print("\n📌 POSSIBLE FORMATS:")
        if results['format_matches']:
            for match in results['format_matches'][:3]:
                print(f"  • {match['format']} (score: {match['score']})")
                print(f"    Reasons: {', '.join(match['reasons'])}")
                print(f"    Remix points: {', '.join(match['remix_points'])}")
        else:
            print("  No strong matches found")
            print("  This might be a new format worth documenting!")


if __name__ == '__main__':
    main()
