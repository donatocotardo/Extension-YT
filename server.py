import os
import glob
import shutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
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

SECRET_COOKIES_PATH = "/etc/secrets/cookies.txt"
WRITABLE_COOKIES_PATH = os.path.join(DOWNLOAD_DIR, "cookies_working.txt")


def get_writable_cookies() -> str | None:
    """Copia el archivo de cookies de solo lectura a una ruta escribible."""
    if os.path.exists(SECRET_COOKIES_PATH):
        shutil.copyfile(SECRET_COOKIES_PATH, WRITABLE_COOKIES_PATH)
        return WRITABLE_COOKIES_PATH
    if os.path.exists("cookies.txt"):
        shutil.copyfile("cookies.txt", WRITABLE_COOKIES_PATH)
        return WRITABLE_COOKIES_PATH
    return None


def get_ffmpeg_location() -> str:
    """Return the directory containing ffmpeg and ffprobe."""
    configured_location = os.environ.get("FFMPEG_LOCATION")
    if configured_location:
        candidate_locations = [os.path.abspath(configured_location)]
    else:
        candidate_locations = []

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return os.path.dirname(ffmpeg_path)

    if os.name == "nt":
        winget_packages = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"
        )
        candidate_locations.extend(
            os.path.join(package, "bin")
            for package in glob.glob(
                os.path.join(winget_packages, "Gyan.FFmpeg_*", "*")
            )
        )

    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    for location in candidate_locations:
        if os.path.isfile(os.path.join(location, ffmpeg_name)) and os.path.isfile(
            os.path.join(location, ffprobe_name)
        ):
            return location

    if configured_location:
        raise RuntimeError(
            f"FFMPEG_LOCATION no contiene ffmpeg y ffprobe: {configured_location}"
        )
    raise RuntimeError(
        "No se encontraron ffmpeg y ffprobe. Instala FFmpeg y agrega su carpeta "
        "bin al PATH, o define FFMPEG_LOCATION con esa carpeta."
    )


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"


def cleanup_file(path: str):
    """Elimina el archivo tras enviarlo para no saturar el disco."""
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

    # Usar el cliente 'web' para que yt-dlp lea y envíe las cookies
    common_extractor_args = {
        "youtube": {
            "player_client": ["web"]
        }
    }

    cookie_path = get_writable_cookies()
    print(f"Usando archivo de cookies en: {cookie_path}")

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
            "quiet": False,
        }
    else:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": out_template,
            "ffmpeg_location": ffmpeg_location,
            "extractor_args": common_extractor_args,
            "quiet": False,
        }

    if cookie_path:
        ydl_opts["cookiefile"] = cookie_path

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
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)