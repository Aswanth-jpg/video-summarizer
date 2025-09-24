import os
import tempfile
import warnings
from faster_whisper import WhisperModel

# Suppress warnings
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)

def test_whisper_with_sample():
    """Test Whisper with a sample audio file"""
    try:
        print("🎤 Testing Faster Whisper...")
        
        # Check if we have the model file - faster-whisper uses model names, not files
        model_name = "base"  # Use the base model
        print(f"📁 Using model: {model_name}")
        
        # Initialize Whisper model (it will download if not cached)
        print("⬇️  Loading model (may download if first time)...")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        print("✅ Whisper model loaded successfully!")
        
        # Check for existing audio file
        audio_file = None
        for ext in ['.mp3', '.wav', '.m4a', '.webm']:
            for filename in ['audio', 'test_audio', 'sample']:
                test_path = f"{filename}{ext}"
                if os.path.exists(test_path):
                    audio_file = test_path
                    break
            if audio_file:
                break
        
        if audio_file:
            print(f"🎵 Found audio file: {audio_file}")
            print("🔄 Transcribing...")
            
            # Transcribe
            segments, info = model.transcribe(audio_file, beam_size=5)
            
            print(f"🌍 Detected language: {info.language} (probability: {info.language_probability:.2f})")
            print("📝 Transcription:")
            print("-" * 50)
            
            for segment in segments:
                print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
                
        else:
            print("⚠️  No audio file found for testing")
            print("💡 To test with audio, place an audio file named:")
            print("   - audio.mp3, audio.wav, audio.m4a, or audio.webm")
            print("   - test_audio.mp3, etc.")
            print("   - sample.mp3, etc.")
            
        print("✅ Whisper test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing Whisper: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_whisper_with_sample()