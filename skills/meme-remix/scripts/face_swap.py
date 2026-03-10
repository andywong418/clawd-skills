#!/usr/bin/env python3
"""
Face Swap Script for Meme Remixing

Supports:
- Single image face swap
- Video face swap with temporal consistency
- Multi-face detection and selective swapping

Dependencies:
    pip install insightface onnxruntime opencv-python pillow requests

Usage:
    python face_swap.py --source face.jpg --target video.mp4 --output output.mp4
    python face_swap.py --source face.jpg --target image.jpg --output swapped.jpg
"""

import argparse
import os
import sys
import tempfile
import subprocess
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("Warning: opencv-python not installed. Install with: pip install opencv-python")

try:
    import insightface
    from insightface.app import FaceAnalysis
    HAS_INSIGHTFACE = True
except ImportError:
    HAS_INSIGHTFACE = False
    print("Warning: insightface not installed. Install with: pip install insightface onnxruntime")


class FaceSwapper:
    def __init__(self, model_name='buffalo_l'):
        """Initialize face analysis and swapper models."""
        if not HAS_INSIGHTFACE:
            raise RuntimeError("insightface is required. Install with: pip install insightface onnxruntime")
        
        self.app = FaceAnalysis(name=model_name)
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
        # Load swapper model
        model_path = os.path.expanduser('~/.insightface/models/inswapper_128.onnx')
        if not os.path.exists(model_path):
            print(f"Swapper model not found at {model_path}")
            print("Download from: https://github.com/deepinsight/insightface/releases")
            print("Place inswapper_128.onnx in ~/.insightface/models/")
            self.swapper = None
        else:
            self.swapper = insightface.model_zoo.get_model(model_path)
    
    def get_face(self, img, index=0):
        """Extract face from image."""
        faces = self.app.get(img)
        if not faces:
            return None
        # Sort by face size (largest first)
        faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
        return faces[index] if index < len(faces) else None
    
    def swap_face(self, source_img, target_img, source_face_idx=0, target_face_idx=0):
        """Swap face from source onto target."""
        if self.swapper is None:
            raise RuntimeError("Swapper model not loaded")
        
        source_face = self.get_face(source_img, source_face_idx)
        target_face = self.get_face(target_img, target_face_idx)
        
        if source_face is None:
            raise ValueError("No face detected in source image")
        if target_face is None:
            raise ValueError("No face detected in target image")
        
        result = self.swapper.get(target_img, target_face, source_face, paste_back=True)
        return result
    
    def swap_image(self, source_path, target_path, output_path):
        """Swap face in a single image."""
        source_img = cv2.imread(source_path)
        target_img = cv2.imread(target_path)
        
        result = self.swap_face(source_img, target_img)
        cv2.imwrite(output_path, result)
        return output_path
    
    def swap_video(self, source_path, target_video, output_path, every_n_frames=1):
        """Swap face in video frames."""
        source_img = cv2.imread(source_path)
        source_face = self.get_face(source_img)
        
        if source_face is None:
            raise ValueError("No face detected in source image")
        
        cap = cv2.VideoCapture(target_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Create temp output without audio
        temp_output = tempfile.mktemp(suffix='.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
        
        frame_count = 0
        last_swapped = None
        
        print(f"Processing {total_frames} frames...")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % every_n_frames == 0:
                try:
                    target_face = self.get_face(frame)
                    if target_face is not None:
                        swapped = self.swapper.get(frame, target_face, source_face, paste_back=True)
                        last_swapped = swapped
                    else:
                        swapped = last_swapped if last_swapped is not None else frame
                except Exception as e:
                    print(f"Frame {frame_count}: {e}")
                    swapped = last_swapped if last_swapped is not None else frame
            else:
                swapped = last_swapped if last_swapped is not None else frame
            
            out.write(swapped)
            frame_count += 1
            
            if frame_count % 30 == 0:
                print(f"  Processed {frame_count}/{total_frames} frames")
        
        cap.release()
        out.release()
        
        # Add audio back using ffmpeg
        print("Adding audio track...")
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_output,
            '-i', target_video,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0?',
            '-shortest',
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        os.remove(temp_output)
        
        return output_path


def download_if_url(path):
    """Download file if path is URL, return local path."""
    if path.startswith(('http://', 'https://')):
        import requests
        ext = Path(path).suffix or '.tmp'
        temp_path = tempfile.mktemp(suffix=ext)
        response = requests.get(path, stream=True)
        response.raise_for_status()
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return temp_path, True
    return path, False


def main():
    parser = argparse.ArgumentParser(description='Face swap for images and videos')
    parser.add_argument('--source', '-s', required=True, help='Source face image')
    parser.add_argument('--target', '-t', required=True, help='Target image or video')
    parser.add_argument('--output', '-o', required=True, help='Output path')
    parser.add_argument('--every-n', type=int, default=1, help='Process every N frames (for speed)')
    args = parser.parse_args()
    
    if not HAS_CV2 or not HAS_INSIGHTFACE:
        print("\nMissing dependencies. Install with:")
        print("  pip install insightface onnxruntime opencv-python pillow requests")
        sys.exit(1)
    
    # Download if URLs
    source_path, source_is_temp = download_if_url(args.source)
    target_path, target_is_temp = download_if_url(args.target)
    
    try:
        swapper = FaceSwapper()
        
        # Detect if target is video or image
        target_ext = Path(target_path).suffix.lower()
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        
        if target_ext in video_exts:
            result = swapper.swap_video(source_path, target_path, args.output, args.every_n)
        else:
            result = swapper.swap_image(source_path, target_path, args.output)
        
        print(f"Output saved to: {result}")
        
    finally:
        # Cleanup temp files
        if source_is_temp:
            os.remove(source_path)
        if target_is_temp:
            os.remove(target_path)


if __name__ == '__main__':
    main()
