#!/usr/bin/env python3
"""
Main orchestration script for automated Instagram Reel generation.

Usage:
    python main.py --topic "AAC boards"
    or modify TOPIC variable below and run: python main.py
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import our custom modules
from generate_script import generate_script
from tts import text_to_speech, use_existing_audio
from make_srt import create_srt_from_script
from render_reel import render_reel, check_ffmpeg_available

# Load environment variables
load_dotenv()

# Default topic - modify this or use command line argument
TOPIC = "Parent FAQ: How do I model the word 'Drink' during daily routines?"

def main():
    """Main function to orchestrate the entire reel generation pipeline."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate Instagram Reels automatically')
    parser.add_argument('--topic', type=str, help='Topic for the reel')
    parser.add_argument('--audio', type=str, help='Path to existing audio file (optional)')
    parser.add_argument('--output', type=str, default='out/reel.mp4', help='Output video path')
    
    args = parser.parse_args()
    
    # Use command line topic if provided, otherwise use default
    topic = args.topic or TOPIC
    output_path = args.output
    
    print(f"[REEL] Starting Instagram Reel generation...")
    print(f"[TOPIC] Topic: {topic}")
    print(f"[OUTPUT] Output: {output_path}")
    print("-" * 50)
    
    try:
        # Step 1: Generate script
        print("[1] Generating script...")
        try:
            script = generate_script(topic)
            print(f"   Generated script ({len(script.split())} words)")
            print(f"   Preview: {script[:100]}...")
        except Exception as e:
            print(f"   [WARNING] OpenAI API issue: {e}")
            print("   [FALLBACK] Using fallback script for testing...")
            script = """Hey parents! Struggling with teaching your child the word 'drink'? Here's the game-changer. First, model the word before every drinking opportunity. Say 'drink' clearly while holding their cup. Wait for any response - a sound, gesture, or word attempt. Immediately reward their effort! Do this during snacks, meals, and water breaks throughout the day. The key? Consistency and patience. More practice means faster learning. What's your biggest challenge with new words?"""
            print(f"   Generated script ({len(script.split())} words)")
            print(f"   Preview: {script[:100]}...")
        
        # Step 2: Generate or use audio
        audio_path = "temp/voice.mp3"
        
        if args.audio and os.path.exists(args.audio):
            print("[2] Using provided audio file...")
            audio_duration = use_existing_audio(args.audio, audio_path)
        else:
            print("[2] Generating audio with TTS...")
            audio_duration = text_to_speech(script, audio_path)
        
        print(f"   Audio duration: {audio_duration:.2f} seconds")
        
        # Step 3: Generate SRT captions
        print("[3] Creating captions with improved alignment...")
        srt_path = "temp/captions.srt"
        create_srt_from_script(script, audio_duration, srt_path, audio_path)
        
        # Step 4: Check prerequisites for rendering
        print("[4] Checking prerequisites...")
        
        # Check FFmpeg
        if not check_ffmpeg_available():
            raise Exception(
                "FFmpeg not found! Please install FFmpeg and add it to your PATH.\n"
                "Download from: https://ffmpeg.org/download.html"
            )
        print("   [OK] FFmpeg available")
        
        # Check background video
        background_video = os.getenv("BACKGROUND_VIDEO", "assets/bg.mp4")
        if not os.path.exists(background_video):
            raise Exception(
                f"Background video not found: {background_video}\n"
                "Please add a 9:16 background video to assets/bg.mp4"
            )
        print(f"   [OK] Background video found: {background_video}")
        
        # Step 5: Render final video
        print("[5] Rendering final reel...")
        final_video = render_reel(
            background_video=background_video,
            audio_file=audio_path,
            srt_file=srt_path,
            output_path=output_path
        )
        
        # Success!
        print("-" * 50)
        print("[SUCCESS] Reel generated successfully!")
        print(f"[OUTPUT] Video: {final_video}")
        print(f"[DURATION] Duration: {audio_duration:.2f} seconds")
        
        # Show file sizes
        if os.path.exists(final_video):
            size_mb = os.path.getsize(final_video) / (1024 * 1024)
            print(f"[SIZE] File size: {size_mb:.2f} MB")
        
        return final_video
        
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        sys.exit(1)

def cleanup_temp_files():
    """Clean up temporary files."""
    temp_files = ['temp/voice.mp3', 'temp/captions.srt']
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[CLEANUP] Cleaned up: {file_path}")
            except Exception as e:
                print(f"[WARNING] Could not remove {file_path}: {e}")

def setup_directories():
    """Ensure required directories exist."""
    dirs = ['temp', 'out', 'assets']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)

if __name__ == "__main__":
    # Setup
    setup_directories()
    
    try:
        # Run main pipeline
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Process interrupted by user")
        sys.exit(1)
    finally:
        # Optional cleanup (uncomment to auto-cleanup temp files)
        # cleanup_temp_files()
        pass