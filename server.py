import os
import glob
import shutil
import time
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="Local Media Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

TIMEOUT_SECONDS = 300 
last_activity_time = time.time()

@app.middleware("http")
async def update_activity_timer(request: Request, call_next):
    global last_activity_time
    last_activity_time = time.time()
    response = await call_next(request)
    last_activity_time = time.time()  # Reiniciar también al terminar la descarga
    return response

def inactivity_monitor():
    while True:
        time.sleep(10)
        if time.time() - last_activity_time > TIMEOUT_SECONDS:
            os._exit(0)  # Cierra el servidor limpiamente tras 5 min inactivo

threading.Thread(target=inactivity_monitor, daemon=True).start()

@app.get("/ping")
def ping():
    return {"status": "awake"}

def get_ffmpeg_location() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return os.path.dirname(ffmpeg_path)

    if os.name == "nt":
        winget_packages = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"
        )
        for package in glob.glob(os.path.join(winget_packages, "Gyan.FFmpeg_*", "*")):
            bin_dir = os.path.join(package, "bin")
            if os.path.isfile(os.path.join(bin_dir, "ffmpeg.exe")):
                return bin_dir

    raise RuntimeError("No se encontró FFmpeg.")

class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"

def cleanup_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@app.post("/download")
def download_media(req: DownloadRequest, background_tasks: BackgroundTasks):
    out_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    if req.format not in {"mp3", "mp4"}:
        raise HTTPException(status_code=400, detail="El formato debe ser mp3 o mp4.")

    try:
        ffmpeg_location = get_ffmpeg_location()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    common_extractor_args = {
        "youtube": {
            "player_client": ["android", "web"]
        }
    }

    if req.format == "mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "ffmpeg_location": ffmpeg_location,
            "extractor_args": common_extractor_args,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
        }
    else:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": out_template,
            "ffmpeg_location": ffmpeg_location,
            "extractor_args": common_extractor_args,
            "quiet": True,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            video_id = info.get("id")
            title = info.get("title", "audio")

        expected_ext = "mp3" if req.format == "mp3" else "mp4"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{expected_ext}")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Error al generar el archivo.")

        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
        filename = f"{clean_title}.{expected_ext}"

        background_tasks.add_task(cleanup_file, file_path)
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)