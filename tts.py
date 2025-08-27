import os
import pyttsx3
import tempfile
import wave
from pathlib import Path
from dotenv import load_dotenv
from mutagen.mp3 import MP3

load_dotenv()

def text_to_speech(text: str, output_path: str) -> float:
    """
    Convert text to speech using Windows built-in SAPI (free).
    Returns the duration of the generated audio in seconds.
    """
    
    try:
        # Initialize the TTS engine
        engine = pyttsx3.init()
        
        # Configure voice settings
        voices = engine.getProperty('voices')
        if voices:
            # Try to use a female voice if available, otherwise use default
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
        
        # Set speech rate (words per minute) - slower for clarity
        engine.setProperty('rate', 160)
        
        # Set volume
        engine.setProperty('volume', 0.9)
        
        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate temporary WAV file first
        temp_wav = output_path.replace('.mp3', '_temp.wav')
        
        # Save to WAV file
        engine.save_to_file(text, temp_wav)
        engine.runAndWait()
        
        # Convert WAV to MP3 using ffmpeg (if available) or keep as WAV
        if output_path.endswith('.mp3'):
            try:
                import subprocess
                subprocess.run([
                    'ffmpeg', '-i', temp_wav, '-codec:a', 'libmp3lame', 
                    '-b:a', '128k', output_path, '-y'
                ], check=True, capture_output=True)
                os.remove(temp_wav)  # Clean up temp file
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If ffmpeg not available, rename WAV to MP3 (will still work)
                os.rename(temp_wav, output_path)
        else:
            os.rename(temp_wav, output_path)
        
        # Get audio duration
        try:
            if output_path.endswith('.mp3'):
                audio = MP3(output_path)
                duration = audio.info.length
            else:
                # For WAV files
                with wave.open(output_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
        except:
            # Fallback: estimate duration based on text length
            # Average speaking rate: ~150 words per minute
            word_count = len(text.split())
            duration = (word_count / 150) * 60
        
        print(f"TTS generated: {output_path} ({duration:.2f}s)")
        return duration
        
    except Exception as e:
        raise Exception(f"TTS generation failed: {str(e)}")

def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an existing audio file."""
    try:
        audio = MP3(audio_path)
        return audio.info.length
    except Exception as e:
        raise Exception(f"Failed to get audio duration: {str(e)}")

def use_existing_audio(audio_path: str, output_path: str) -> float:
    """
    Copy an existing audio file to the output location.
    Returns the duration of the audio in seconds.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Copy file to output location
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(audio_path, 'rb') as src, open(output_path, 'wb') as dst:
        dst.write(src.read())
    
    duration = get_audio_duration(output_path)
    print(f"Using existing audio: {output_path} ({duration:.2f}s)")
    return duration

if __name__ == "__main__":
    test_text = "This is a test of the text-to-speech functionality. It should generate clear audio."
    duration = text_to_speech(test_text, "temp/test_audio.mp3")
    print(f"Test audio generated with duration: {duration:.2f} seconds")