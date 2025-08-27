import os
import subprocess
import json
import shlex
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def calculate_optimal_subtitle_settings(srt_file: str, video_width: int = 1080, video_height: int = 1920) -> dict:
    """
    Calculate optimal font size and margins to fit text within screen bounds.
    
    Args:
        srt_file: Path to the SRT file
        video_width: Video width in pixels (default 1080 for Instagram)
        video_height: Video height in pixels (default 1920 for Instagram)
        
    Returns:
        Dict with optimal FontSize, MarginL, MarginR, MarginV
    """
    try:
        # Read SRT file to analyze text content
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse SRT to get individual subtitle blocks
        subtitle_blocks = []
        current_block = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line and current_block:
                # End of subtitle block
                text_lines = [l for l in current_block if not l.isdigit() and '-->' not in l]
                if text_lines:
                    subtitle_blocks.append('\n'.join(text_lines))
                current_block = []
            elif line:
                current_block.append(line)
        
        # Add last block if exists
        if current_block:
            text_lines = [l for l in current_block if not l.isdigit() and '-->' not in l]
            if text_lines:
                subtitle_blocks.append('\n'.join(text_lines))
        
        if not subtitle_blocks:
            # Fallback if no text found
            return {
                "FontSize": 32,
                "MarginL": 120,
                "MarginR": 120,
                "MarginV": 200
            }
        
        # Analyze all subtitle blocks
        max_line_length = 0
        max_lines_in_block = 0
        
        for block in subtitle_blocks:
            lines = block.split('\n')
            max_lines_in_block = max(max_lines_in_block, len(lines))
            for line in lines:
                max_line_length = max(max_line_length, len(line))
        
        # Set conservative margins (20% of width for mobile viewing)
        margin_horizontal = int(video_width * 0.20)
        available_width = video_width - (2 * margin_horizontal)
        
        # Calculate font size based on the longest line
        # More conservative character width estimation
        if max_line_length > 0:
            # Estimate pixels per character needed
            # Account for variable width fonts - use conservative estimate
            pixels_per_char = available_width / max_line_length
            
            # Font size calculation (characters are roughly 0.5-0.6 width of height for Arial)
            # Using 0.55 as a conservative middle ground
            estimated_font_size = int(pixels_per_char / 0.55)
            
            # Apply bounds suitable for mobile viewing
            # Instagram Reels are primarily viewed on phones
            font_size = max(28, min(estimated_font_size, 42))
            
            # If text is very long, force smaller size and rely on wrapping
            if max_line_length > 50:
                font_size = min(font_size, 32)
            elif max_line_length > 40:
                font_size = min(font_size, 36)
        else:
            font_size = 32  # Default
        
        # Calculate vertical margin based on number of lines
        # Each line needs roughly 1.3x font size in height
        line_height = int(font_size * 1.3)
        total_text_height = line_height * max_lines_in_block
        
        # Keep subtitles in lower third but not too close to bottom
        # Leave space for UI elements (Instagram interface)
        safe_zone_bottom = int(video_height * 0.08)  # 8% from bottom for Instagram UI
        margin_vertical = max(safe_zone_bottom, int(total_text_height * 1.2))
        
        # Fine-tune margins based on font size
        if font_size <= 30:
            margin_horizontal = int(video_width * 0.15)  # Can use less margin with smaller text
        elif font_size >= 40:
            margin_horizontal = int(video_width * 0.25)  # Need more margin with larger text
        
        settings = {
            "FontSize": font_size,
            "MarginL": margin_horizontal,
            "MarginR": margin_horizontal,
            "MarginV": margin_vertical,
            "BorderStyle": 3 if max_line_length > 35 else 1  # Box style for longer text
        }
        
        print(f"[SUBTITLE] Analysis complete:")
        print(f"   Max line length: {max_line_length} chars")
        print(f"   Max lines per block: {max_lines_in_block}")
        print(f"   Font size: {font_size}px")
        print(f"   Horizontal margins: {margin_horizontal}px")
        print(f"   Vertical margin: {margin_vertical}px")
        
        return settings
        
    except Exception as e:
        print(f"[WARNING] Could not calculate optimal settings: {e}")
        # Return safe fallback values
        return {
            "FontSize": 32,
            "MarginL": 150,
            "MarginR": 150,
            "MarginV": 200,
            "BorderStyle": 3
        }

def get_audio_duration(audio_file: str) -> float:
    """Get the duration of an audio file using ffprobe."""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
               '-of', 'csv=p=0', audio_file]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Warning: Could not get audio duration, using fallback: {e}")
        return 35.0  # Default fallback

def render_reel(background_video: str, audio_file: str, srt_file: str, output_path: str) -> str:
    """
    Combine background video, audio, and captions into a final Instagram Reel.
    
    Args:
        background_video: Path to the 9:16 background video
        audio_file: Path to the voice audio file
        srt_file: Path to the SRT caption file
        output_path: Path for the final output video
        
    Returns:
        Path to the rendered video file
    """
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Validate input files
    if not os.path.exists(background_video):
        raise FileNotFoundError(f"Background video not found: {background_video}")
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    if not os.path.exists(srt_file):
        raise FileNotFoundError(f"SRT file not found: {srt_file}")
    
    # Get audio duration to match video length
    audio_duration = get_audio_duration(audio_file)
    
    # Calculate optimal subtitle settings based on content
    subtitle_settings = calculate_optimal_subtitle_settings(srt_file)
    
    # Use minimal, known-working subtitle styling
    force_style = (
        "FontSize=36,"
        "PrimaryColour=&H00ffffff,"
        "OutlineColour=&H00000000,"
        "Outline=3,"
        "MarginV=100,"
        "MarginL=50,"
        "MarginR=50"
    )
    
    # FFmpeg command to create the final reel
    cmd = [
        'ffmpeg', '-y',  # -y to overwrite output file
        '-stream_loop', '-1',    # Loop the background video indefinitely
        '-i', background_video,  # Input background video
        '-i', audio_file,        # Input audio file
        '-vf', 
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles={srt_file}:force_style='{force_style}'",
        '-c:v', 'libx264',      # Video codec
        '-preset', 'medium',    # Encoding preset
        '-crf', '23',          # Quality setting
        '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
        '-c:a', 'aac',         # Audio codec
        '-b:a', '128k',        # Audio bitrate
        '-ar', '44100',        # Audio sample rate
        '-t', str(audio_duration),  # Match audio duration
        '-movflags', '+faststart',  # Optimize for streaming
        output_path
    ]
    
    print(f"[RENDER] Starting FFmpeg render...")
    print(f"[RENDER] Output: {output_path}")
    print(f"[DEBUG] SRT file: {srt_file}")
    print(f"[DEBUG] Force style: {force_style}")
    print(f"[DEBUG] Full command: {' '.join(cmd)}")
    
    try:
        # Run ffmpeg command
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"[SUCCESS] Reel rendered successfully: {output_path}")
        
        # Verify output file
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"[INFO] Output file size: {size_mb:.2f} MB")
        
        return output_path
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg command failed:")
        print(f"STDERR: {e.stderr}")
        raise Exception(f"FFmpeg rendering failed: {e.stderr}")
    except FileNotFoundError:
        raise Exception(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
            "Download from: https://ffmpeg.org/download.html"
        )

def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available in the system PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_info(video_path: str) -> dict:
    """Get basic information about a video file using ffprobe."""
    if not check_ffmpeg_available():
        return {"error": "FFmpeg not available"}
    
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        info = json.loads(result.stdout)
        
        # Extract relevant info
        video_stream = next((s for s in info.get('streams', []) if s['codec_type'] == 'video'), None)
        
        if video_stream:
            return {
                "width": video_stream.get('width'),
                "height": video_stream.get('height'),
                "duration": float(info['format'].get('duration', 0)),
                "codec": video_stream.get('codec_name'),
                "fps": eval(video_stream.get('r_frame_rate', '0/1'))
            }
        
        return info
        
    except Exception as e:
        return {"error": str(e)}

def validate_instagram_reel(video_path: str) -> bool:
    """Validate that the video meets Instagram Reel requirements."""
    info = get_video_info(video_path)
    
    if 'error' in info:
        print(f"[WARNING] Could not validate video: {info['error']}")
        return False
    
    issues = []
    
    # Check aspect ratio (should be 9:16)
    if info.get('width') and info.get('height'):
        aspect_ratio = info['width'] / info['height']
        if abs(aspect_ratio - (9/16)) > 0.01:
            issues.append(f"Aspect ratio is {aspect_ratio:.2f}, should be 0.5625 (9:16)")
    
    # Check duration (max 90 seconds for Reels)
    if info.get('duration', 0) > 90:
        issues.append(f"Duration is {info['duration']:.1f}s, max is 90s")
    
    if issues:
        print("[VALIDATION] Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("[VALIDATION] Video meets Instagram Reel requirements")
    return True

if __name__ == "__main__":
    # Test the rendering function
    if check_ffmpeg_available():
        print("[OK] FFmpeg is available")
        
        output = render_reel(
            background_video="assets/bg.mp4",
            audio_file="temp/voice.mp3", 
            srt_file="temp/captions.srt",
            output_path="out/reel.mp4"
        )
        
        if output and os.path.exists(output):
            validate_instagram_reel(output)
    else:
        print("[ERROR] FFmpeg not found - please install FFmpeg")
        print("Download from: https://ffmpeg.org/download.html")