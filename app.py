import sys
import subprocess
import threading
import time
import os
import streamlit.components.v1 as components
from urllib.parse import urlparse, parse_qs
import requests

# Install streamlit jika belum ada
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# Install gdown untuk download dari Google Drive
try:
    import gdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
    import gdown

def extract_drive_id(url):
    """Ekstrak ID file dari URL Google Drive"""
    parsed = urlparse(url)
    if "drive.google.com" in parsed.netloc:
        if "/file/d/" in url:
            return url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            return parse_qs(parsed.query)['id'][0]
    return None

def download_from_drive(drive_url, output_path="temp_video.mp4"):
    """Download video dari Google Drive"""
    try:
        file_id = extract_drive_id(drive_url)
        if not file_id:
            raise ValueError("URL Google Drive tidak valid")
        
        # Format URL untuk download
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        # Download file
        gdown.download(download_url, output_path, quiet=False)
        return output_path
    except Exception as e:
        raise Exception(f"Gagal download dari Google Drive: {str(e)}")

def run_ffmpeg(video_path, stream_key, is_shorts, log_callback):
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = "-vf scale=720:1280" if is_shorts else ""
    cmd = [
        "ffmpeg", "-re", "-stream_loop", "-1", "-i", video_path,
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2500k",
        "-maxrate", "2500k", "-bufsize", "5000k",
        "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv"
    ]
    if scale:
        cmd += scale.split()
    cmd.append(output_url)
    log_callback(f"Menjalankan: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_callback(line.strip())
        process.wait()
    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback("Streaming selesai atau dihentikan.")

def main():
    # Page configuration must be the first Streamlit command
    st.set_page_config(
        page_title="Streaming YT by didinchy",
        page_icon="📈",
        layout="wide"
    )
    st.title("Live Streaming Loss Doll")
    
    # Bagian iklan baru
    show_ads = st.checkbox("Tampilkan Iklan", value=True)
    if show_ads:
        st.subheader("Iklan Sponsor")
        components.html(
            """
            <div style="background:#f0f2f6;padding:20px;border-radius:10px;text-align:center">
                <script type='text/javascript' 
                        src='//pl26562103.profitableratecpm.com/28/f9/95/28f9954a1d5bbf4924abe123c76a68d2.js'>
                </script>
                <p style="color:#888">Iklan akan muncul di sini</p>
            </div>
            """,
            height=300
        )

    # Opsi input video
    video_source = st.radio("Pilih sumber video:", ["File lokal", "Upload baru", "Google Drive"])

    video_path = None
    
    if video_source == "File lokal":
        # List available video files
        video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv'))]
        st.write("Video yang tersedia:")
        selected_video = st.selectbox("Pilih video", video_files) if video_files else None
        if selected_video:
            video_path = selected_video
            
    elif video_source == "Upload baru":
        uploaded_file = st.file_uploader("Upload video (mp4/flv - codec H264/AAC)", type=['mp4', 'flv'])
        if uploaded_file:
            # Save uploaded file
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.read())
            st.success("Video berhasil diupload!")
            video_path = uploaded_file.name
            
    elif video_source == "Google Drive":
        drive_url = st.text_input("URL Google Drive (pastikan file dibagikan)")
        if drive_url:
            try:
                with st.spinner("Mendownload video dari Google Drive..."):
                    video_path = download_from_drive(drive_url)
                st.success("Video berhasil didownload!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                video_path = None

    stream_key = st.text_input("Stream Key", type="password")
    date = st.date_input("Tanggal Tayang")
    time_val = st.timeInput("Jam Tayang")
    is_shorts = st.checkbox("Mode Shorts (720x1280)")

    log_placeholder = st.empty()
    logs = []
    streaming = st.session_state.get('streaming', False)

    def log_callback(msg):
        logs.append(msg)
        try:
            log_placeholder.text("\n".join(logs[-20:]))
        except:
            print(msg)  # Fallback to console logging

    if 'ffmpeg_thread' not in st.session_state:
        st.session_state['ffmpeg_thread'] = None

    if st.button("Jalankan Streaming"):
        if not video_path or not stream_key:
            st.error("Video dan stream key harus diisi!")
        else:
            st.session_state['streaming'] = True
            st.session_state['ffmpeg_thread'] = threading.Thread(
                target=run_ffmpeg, args=(video_path, stream_key, is_shorts, log_callback), daemon=True)
            st.session_state['ffmpeg_thread'].start()
            st.success("Streaming dimulai!")

    if st.button("Stop Streaming"):
        st.session_state['streaming'] = False
        os.system("pkill ffmpeg")
        # Bersihkan file temporary
        temp_files = ["temp_video.mp4"]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        st.warning("Streaming dihentikan!")

    log_placeholder.text("\n".join(logs[-20:]))

if __name__ == '__main__':
    main()
