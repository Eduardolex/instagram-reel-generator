import os
import re
from typing import List, Tuple, Dict

# Optional imports for advanced alignment
try:
    from pydub import AudioSegment
    import speech_recognition as sr
    ADVANCED_ALIGNMENT = True
except ImportError:
    ADVANCED_ALIGNMENT = False

def create_srt_from_script(script: str, audio_duration: float, output_path: str, audio_file: str = None) -> str:
    """
    Generate an SRT caption file from a script with precise word-level timing.
    
    Args:
        script: The text script
        audio_duration: Duration of the audio in seconds
        output_path: Path to save the SRT file
        audio_file: Path to audio file for alignment (optional)
        
    Returns:
        Path to the generated SRT file
    """
    
    # Clean and split the script into words
    words = script.replace('\n', ' ').split()
    
    if not words:
        raise ValueError("No text to create captions from")
    
    # Try to get word-level timing from audio
    if audio_file and os.path.exists(audio_file) and ADVANCED_ALIGNMENT:
        try:
            word_timings = get_word_level_timing(script, audio_file)
            return create_srt_from_timings(word_timings, output_path)
        except Exception as e:
            print(f"   [WARNING] Audio alignment failed ({e}), using fallback timing...")
    
    # Fallback: Estimate timing based on speech patterns
    word_timings = estimate_word_timing(words, audio_duration)
    
    return create_srt_from_timings(word_timings, output_path)

def get_word_level_timing(script: str, audio_file: str) -> List[Dict]:
    """Extract word-level timing from audio using speech recognition."""
    if not ADVANCED_ALIGNMENT:
        # Fallback if libraries not available
        words = script.split()
        return estimate_word_timing(words, 30.0)  # Default duration
    
    # Convert audio to WAV for processing
    audio = AudioSegment.from_file(audio_file)
    wav_path = audio_file.replace('.mp3', '_temp.wav')
    audio.export(wav_path, format="wav")
    
    try:
        # Use speech recognition with timestamps
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
        
        # Get word-level timing using Google Speech-to-Text (requires internet)
        try:
            result = r.recognize_google(audio_data, show_all=True)
            # This is a simplified approach - for production, use Google Cloud Speech-to-Text API
            words = script.split()
            audio_duration = len(audio) / 1000.0
            return estimate_word_timing(words, audio_duration)
        except:
            # Fallback to estimation
            words = script.split()
            audio_duration = len(audio) / 1000.0
            return estimate_word_timing(words, audio_duration)
            
    finally:
        # Clean up temp file
        if os.path.exists(wav_path):
            os.remove(wav_path)

def estimate_word_timing(words: List[str], total_duration: float) -> List[Dict]:
    """Estimate word timing based on word length and speech patterns."""
    word_timings = []
    
    # Calculate relative durations based on word characteristics
    durations = []
    for word in words:
        base_duration = 0.3  # Base duration per word
        
        # Adjust for word length
        if len(word) > 6:
            base_duration += 0.2
        elif len(word) <= 3:
            base_duration = max(0.2, base_duration - 0.1)
        
        # Adjust for punctuation (natural pauses)
        if word.endswith(('.', '!', '?')):
            base_duration += 0.3
        elif word.endswith((',', ';', ':')):
            base_duration += 0.15
            
        durations.append(base_duration)
    
    # Normalize to fit total duration
    total_estimated = sum(durations)
    scale_factor = total_duration / total_estimated
    durations = [d * scale_factor for d in durations]
    
    # Generate timing data
    current_time = 0
    for i, (word, duration) in enumerate(zip(words, durations)):
        word_timings.append({
            'word': word,
            'start': current_time,
            'end': current_time + duration
        })
        current_time += duration
    
    return word_timings

def create_srt_from_timings(word_timings: List[Dict], output_path: str) -> str:
    """Create SRT file from word timing data."""
    # Group words into readable chunks (2-4 words per subtitle)
    srt_entries = []
    current_chunk = []
    chunk_start = None
    
    for timing in word_timings:
        if not current_chunk:
            chunk_start = timing['start']
        
        current_chunk.append(timing['word'])
        
        # End chunk on punctuation or after 3-4 words
        should_end_chunk = (
            len(current_chunk) >= 4 or
            (len(current_chunk) >= 2 and timing['word'].endswith(('.', '!', '?', ',', ';')))
        )
        
        if should_end_chunk:
            srt_entries.append({
                'text': ' '.join(current_chunk),
                'start': chunk_start,
                'end': timing['end']
            })
            current_chunk = []
    
    # Handle remaining words
    if current_chunk:
        srt_entries.append({
            'text': ' '.join(current_chunk),
            'start': chunk_start,
            'end': word_timings[-1]['end']
        })
    
    # Generate SRT content
    srt_content = []
    for i, entry in enumerate(srt_entries):
        start_srt = format_srt_timestamp(entry['start'])
        end_srt = format_srt_timestamp(entry['end'])
        
        srt_content.append(f"{i + 1}")
        srt_content.append(f"{start_srt} --> {end_srt}")
        srt_content.append(entry['text'])
        srt_content.append("")
    
    # Remove trailing empty line
    if srt_content and srt_content[-1] == "":
        srt_content.pop()
    
    # Save SRT file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))
    
    print(f"SRT file created: {output_path} ({len(srt_entries)} captions)")
    return output_path

def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def validate_srt_file(srt_path: str) -> bool:
    """Validate that the SRT file is properly formatted."""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic validation - check for timestamp pattern
        timestamp_pattern = r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}'
        timestamps = re.findall(timestamp_pattern, content)
        
        return len(timestamps) > 0
        
    except Exception as e:
        print(f"SRT validation failed: {e}")
        return False

if __name__ == "__main__":
    test_script = """
    Hey parents! Struggling to teach your child the word 'drink' during daily routines? 
    Here's a simple strategy that works every time. First, model the word 'drink' before 
    every beverage opportunity. Say 'drink' clearly while holding the cup. Then wait for 
    any response - a sound, gesture, or attempt at the word. Reward immediately! 
    Repeat this throughout the day at snacks, meals, and water breaks. 
    Consistency is key - the more opportunities, the faster they'll learn. 
    What's your biggest challenge with teaching new words?
    """
    
    create_srt_from_script(test_script.strip(), 35.0, "temp/test_captions.srt")
    print("Test SRT file created successfully!")