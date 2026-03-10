# Meme Remix Skill

Recognize viral meme formats and remix them with face swaps, text changes, and style transfers.

## Capabilities

### 1. Format Recognition
Identify meme format from image/video:
- Analyze visual structure (text placement, character positions, timing)
- Match against known format database
- Extract remix-able elements (faces, text, audio)

### 2. Face Swapping
Two options available:

**Magic Hour API (Recommended)** - Cloud-based, no setup required:
- High quality face swaps
- Handles video automatically
- Requires `MAGICHOUR_API_KEY` in environment

**Local insightface** - For offline/privacy:
- Requires model download
- Good for quick testing

### 3. Format Remixing
Recreate trending formats with new content:
- Text overlay replacement
- Face/character substitution
- Audio swap (keep visuals, change soundtrack)
- Style transfer

### 4. AI Video Generation
Integrates with seedance-2 providers:
- **Seedance** (ByteDance) - Image/video to video
- **Sora 2** (OpenAI) - Text/image to video
- **Runway** - Gen4, VEO3

## Dependencies

```bash
# Core (always needed)
pip install opencv-python pillow requests

# For Magic Hour face swap (API-based, recommended)
# Just set MAGICHOUR_API_KEY environment variable

# For local face swap (optional)
pip install insightface onnxruntime-gpu
# Download inswapper_128.onnx to ~/.insightface/models/
```

## Usage

### Analyze a meme format
```bash
python scripts/analyze_format.py <image_or_video_url>
python scripts/analyze_format.py --list  # Show known formats
```

### Face swap (Magic Hour API)
```bash
export MAGICHOUR_API_KEY=your_key
python scripts/magichour_faceswap.py --source face.jpg --target video.mp4 --output out.mp4
python scripts/magichour_faceswap.py -s https://url/face.jpg -t https://url/video.mp4 -o out.mp4
```

### Face swap (Local)
```bash
python scripts/face_swap.py --source <source_face> --target <target_media> --output <output_path>
```

### Remix a format
```bash
python scripts/remix_format.py --format <format_name> --face <new_face> --text <new_text>
python scripts/remix_format.py --list  # Show available formats
```

## Format Database

Formats are stored in `formats/formats.json` with:
- `id`: URL-safe identifier (auto-generated from name)
- `name`: Human-readable name
- `description`: What makes this format
- `structure`: Visual/text/timing breakdown
- `remix_points`: What can be swapped
- `examples`: Reference URLs
- `tags`: Categorization
- `humor_mechanic`: Why it's funny/engaging
- `viral_score`: Popularity metric
- `use_count`: Times used
- `created_at`/`updated_at`: Timestamps

### Managing Formats

```bash
# Add a new format
python scripts/format_manager.py add \
  --name "Format Name" \
  --desc "What it is" \
  --tag trending --tag caption \
  --example https://example.com/video

# List all formats
python scripts/format_manager.py list
python scripts/format_manager.py list --json

# Get trending
python scripts/format_manager.py trending

# Record usage (for analytics)
python scripts/format_manager.py use <format-id>

# Export for webapp
python scripts/format_manager.py export --output formats-api.json
```

### Webapp Integration

Export formats for the webapp:
```bash
python scripts/format_manager.py export
```

Returns JSON with:
- `formats`: Full format list with metadata
- `trending`: Top format IDs by viral score
- `total_count`: Number of formats
- `last_updated`: Timestamp

## Workflow

1. **Spot trending format** → analyze structure
2. **Add to database** if new
3. **Remix** with new faces/text/context
4. **Export** for posting

## Integration with seedance-2

This skill is designed to work with [seedance-2](https://github.com/jefftangx/seedance-2):

```bash
# Clone the repo (requires SSH access)
git clone git@github.com:jefftangx/seedance-2.git

# The magichour_faceswap.py script mirrors the MagicHourProvider from seedance-2
# You can use either directly
```

Key providers from seedance-2:
- `packages/shared/src/magichour-provider.ts` - Face swap API
- `packages/bot/src/providers/sora.ts` - Sora 2 video gen
- `packages/bot/src/providers/runway.ts` - Runway video gen

## Notes

- Face swaps work best with clear, front-facing shots
- Video swaps need consistent lighting
- Magic Hour detects multiple faces - use `--single-face` to only swap primary face
- Always credit original creators when appropriate
