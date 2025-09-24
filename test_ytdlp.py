#!/usr/bin/env python3
"""
Test script to verify yt-dlp functionality
"""
import yt_dlp
import os
import tempfile

def test_yt_dlp():
    """Test downloading a short YouTube video audio"""
    print(f"Using yt-dlp version: {yt_dlp.version.__version__}")
    
    # Use a short, popular video for testing
    test_url = "https://youtu.be/gG7uCskUOrA?si=RBV-cF2z_BJmshYT"  # Rick Roll - short and reliable
    
    temp_dir = tempfile.mkdtemp()
    print(f"Testing download to: {temp_dir}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'extractaudio': True,
        'audioformat': 'mp3',
        'audioquality': '192',
        'quiet': False,  # Show output for testing
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("Extracting video info...")
            info = ydl.extract_info(test_url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            print(f"Title: {title}")
            print(f"Duration: {duration} seconds")
            
            print("Downloading audio...")
            ydl.download([test_url])
            
            # Check if file was downloaded
            files = os.listdir(temp_dir)
            audio_files = [f for f in files if f.endswith(('.mp3', '.m4a', '.webm', '.opus'))]
            
            if audio_files:
                print(f"✅ Success! Downloaded: {audio_files[0]}")
                file_path = os.path.join(temp_dir, audio_files[0])
                file_size = os.path.getsize(file_path)
                print(f"File size: {file_size / 1024:.1f} KB")
                return True
            else:
                print("❌ No audio file found")
                return False
                
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ DownloadError: {e}")
        print("\nThis can happen for several reasons:")
        print("- The video might be region-restricted, age-restricted, or private.")
        print("- YouTube may have updated its protection mechanisms.")
        print("- Your version of yt-dlp might be outdated.")
        print("\nI have attempted to upgrade it, but if the problem persists, you can try updating it manually:")
        print("pip install --upgrade yt-dlp")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False
    
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    print("Testing yt-dlp functionality...")
    success = test_yt_dlp()
    
    if success:
        print("\n🎉 yt-dlp is working correctly!")
        print("Your YouTube Summarizer app should now work without HTTP 400 errors.")
    else:
        print("\n⚠️ yt-dlp test failed. Check your internet connection.")