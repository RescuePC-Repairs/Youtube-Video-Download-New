import os
import yt_dlp
import re
import time
import shutil
import subprocess
from datetime import datetime

def clean_url(url):
    """Remove list parameters from YouTube URL"""
    return re.sub(r'&list=.*', '', url)

def progress_hook(d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total > 0:
            percent = (downloaded / total) * 100
            print(f"⏬ Downloading: {percent:.1f}% complete", end='\r')
    elif d['status'] == 'finished':
        print("\n✅ Download complete! Merging streams with FFmpeg...")

def validate_ffmpeg():
    """Check if FFmpeg is properly installed and accessible"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if "ffmpeg version" in result.stdout:
            return True
        return False
    except Exception:
        return False

def safe_file_operation(src, dst, operation='rename', max_retries=5, delay=1):
    """Handle Windows file operations with retries"""
    for i in range(max_retries):
        try:
            if operation == 'rename':
                os.rename(src, dst)
            elif operation == 'delete':
                if os.path.isfile(src):
                    os.unlink(src)
                elif os.path.isdir(src):
                    shutil.rmtree(src)
            return True
        except (PermissionError, OSError) as e:
            if i < max_retries - 1:
                print(f"⚠️  File busy, retrying ({i+1}/{max_retries})...")
                time.sleep(delay)
            else:
                print(f"🔥 Failed file operation: {str(e)}")
                return False
    return False

def download_video(url):
    clean_url = re.sub(r'&list=.*', '', url)
    
    # Validate FFmpeg installation
    if not validate_ffmpeg():
        print("\n❌ FFmpeg not found! Please ensure FFmpeg is installed and in your PATH")
        print("   Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("   Add to PATH: C:\\ffmpeg\\bin")
        return False
    
    try:
        # Create directories
        os.makedirs('downloads', exist_ok=True)
        temp_dir = os.path.join('downloads', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Get FFmpeg path
        ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'ffmpeg_location': ffmpeg_path,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'verbose': False,
            'no_warnings': True,
            'ignoreerrors': False,
            'windowsfilenames': True,
            'keepvideo': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("🔍 Fetching video information...")
            start_time = time.time()
            info = ydl.extract_info(clean_url, download=False)
            fetch_time = time.time() - start_time
            print(f"✅ Video info fetched in {fetch_time:.1f} seconds\n")
            
            print(f"📺 Title: {info['title']}")
            duration = datetime.utcfromtimestamp(info['duration'])
            print(f"⏱️  Duration: {duration.strftime('%M:%S')}")
            print(f"📏 Resolution: {info.get('resolution', 'Unknown')}")
            print(f"👀 Views: {info.get('view_count', 'N/A')}")
            print(f"👍 Likes: {info.get('like_count', 'N/A')}")
            
            print("\n⬇️  Starting download... (press Ctrl+C to cancel)")
            ydl.download([clean_url])
            
            # Find the final merged file
            final_file = None
            for f in os.listdir(temp_dir):
                if f.endswith('.mp4') and not f.endswith('.temp.mp4'):
                    final_file = f
                    break
            
            if final_file:
                source_path = os.path.join(temp_dir, final_file)
                dest_path = os.path.join('downloads', final_file)
                
                # Move final file to main downloads folder
                if safe_file_operation(source_path, dest_path, 'rename'):
                    print(f"\n💾 Saved as: {final_file}")
                else:
                    # Fallback to copy if rename fails
                    shutil.copy2(source_path, dest_path)
                    print(f"\n⚠️  Used copy fallback: {final_file}")
                
                # Clean up temporary directory
                for f in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, f)
                    safe_file_operation(file_path, None, 'delete')
                
                # Remove temp directory itself
                safe_file_operation(temp_dir, None, 'delete')
            else:
                print("❌ Final merged file not found")
            
            return True

    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌ Download Error: {str(e)}")
    except KeyboardInterrupt:
        print("\n❌ Download canceled by user")
    except Exception as e:
        print(f"\n🔥 Unexpected error: {str(e)}")
    
    return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(f"{'🎬 YouTube Video Downloader':^60}")
    print("=" * 60)
    print("Enter a YouTube URL to download a video")
    print("Type 'exit' or press Ctrl+C to quit\n")
    
    # Verify FFmpeg at startup
    if not validate_ffmpeg():
        print("\n❌ CRITICAL: FFmpeg not found in PATH!")
        print("   Please install FFmpeg and add it to your system PATH")
        print("   Download: https://www.gyan.dev/ffmpeg/builds/")
        print("   Extract to: C:\\ffmpeg")
        print("   Add to PATH: C:\\ffmpeg\\bin")
        print("\n" + "=" * 60)
    
    while True:
        url = input("\n📋 Enter YouTube URL: ").strip()
        
        if url.lower() in ['exit', 'quit']:
            break
            
        if not url.startswith(('http://', 'https://')):
            print("❌ Invalid URL. Please enter a valid YouTube URL")
            continue
            
        print(f"\n🔄 Using clean URL: {clean_url(url)}")
        
        if download_video(url):
            print("\n" + "-" * 60)
            print("✅ Download completed successfully!")
            print("-" * 60)
        else:
            print("\n" + "-" * 60)
            print("❌ Download failed. See error above for details")
            print("-" * 60)