# Downloader YT

Extensión de Chrome para descargar vídeos de YouTube en formato **MP3** o
**MP4**. La extensión utiliza un servidor local escrito en Python y
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) para procesar las descargas.

> **Importante:** este proyecto funciona únicamente en local. El servidor debe
> ejecutarse en el mismo equipo donde está instalada la extensión.

## Características

- Descarga el vídeo de YouTube que está abierto en la pestaña activa.
- Conversión a MP3 con calidad de 192 kbps.
- Descarga en MP4 cuando el formato está disponible.
- Interfaz sencilla desde una extensión de Chrome.
- Servidor local sin timeout de inactividad.
- Los archivos se eliminan del directorio temporal después de enviarse al
  navegador.

## Requisitos

- Windows.
- Python 3.9 o una versión posterior compatible.
- Google Chrome o un navegador basado en Chromium.
- [FFmpeg](https://ffmpeg.org/download.html), incluyendo `ffmpeg` y
  `ffprobe`.

El servidor busca FFmpeg en el `PATH` del sistema y también en los paquetes
instalados mediante WinGet en Windows.

## Instalación

### 1. Preparar el servidor

Abre PowerShell en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell no permite activar el entorno virtual, se puede instalar las
dependencias directamente usando el ejecutable del entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Comprueba que FFmpeg está disponible:

```powershell
ffmpeg -version
ffprobe -version
```

### 2. Cargar la extensión

1. Abre `chrome://extensions/` en Chrome.
2. Activa **Modo desarrollador**.
3. Pulsa **Cargar descomprimida**.
4. Selecciona la carpeta `extension-yt` de este proyecto.

## Uso

1. Inicia el servidor haciendo doble clic en `launcher.bat`.
2. Abre un vídeo de YouTube.
3. Pulsa el icono de la extensión **Downloader YT**.
4. Elige **Descargar como MP3** o **Descargar como MP4**.
5. Selecciona la ubicación del archivo cuando Chrome lo solicite.

También se puede iniciar el servidor desde PowerShell:

```powershell
.\.venv\Scripts\python.exe server.py
```

El servidor queda disponible en `http://127.0.0.1:8000`.

La extensión intenta iniciar el servidor automáticamente mediante el host
nativo configurado en `native_host.json`. Si esa integración no está
configurada, inicia `launcher.bat` manualmente antes de descargar.

## API local

### Comprobar el estado del servidor

```http
GET http://localhost:8000/ping
```

Respuesta:

```json
{"status": "awake"}
```

### Descargar un vídeo

```http
POST http://localhost:8000/download
Content-Type: application/json
```

Cuerpo:

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "format": "mp3"
}
```

El campo `format` admite únicamente `mp3` y `mp4`. La respuesta contiene el
archivo descargado y utiliza el título del vídeo como nombre de archivo.

## Estructura del proyecto

```text
.
├── server.py              # API local con FastAPI
├── requirements.txt       # Dependencias de Python
├── launcher.bat           # Inicio silencioso del servidor
├── iniciar_servidor.vbs   # Alternativa de inicio sin ventana
├── native_host.json       # Configuración del host nativo de Chrome
└── extension-yt/
    ├── manifest.json      # Configuración de la extensión
    ├── popup.html         # Interfaz de usuario
    ├── popup.js           # Lógica de descarga
    └── icons/             # Iconos de la extensión
```

El directorio `downloads/` se crea automáticamente cuando arranca el servidor.
Los archivos generados son temporales y no se deben subir al repositorio.

## Limitación del despliegue en la nube

Inicialmente se intentó convertir el proyecto en un servidor desplegado en la
nube para que cualquier persona pudiera utilizarlo sin instalar nada. Sin
embargo, las descargas desde servidores remotos se encontraron con
restricciones de YouTube relacionadas con:

- La dirección IP del servidor y su reputación o ubicación.
- Bloqueos y verificaciones adicionales para tráfico procedente de centros de
  datos.
- La necesidad de cookies o de una sesión válida para poder utilizar la extensión.

Por estos motivos, el despliegue en la nube no ofrecía descargas fiables. La
arquitectura actual mantiene `yt-dlp` y FFmpeg en el equipo del usuario, de
modo que las peticiones salen desde su conexión local y se pueden utilizar las
cookies y permisos disponibles en ese entorno cuando sea necesario.

No se proporciona actualmente un endpoint público. Para utilizar el proyecto,
es necesario ejecutar el servidor localmente.

## Solución de problemas

### No se pudo iniciar el servidor local

- Comprueba que existe `.venv\Scripts\python.exe`.
- Instala las dependencias con `python -m pip install -r requirements.txt`.
- Ejecuta `launcher.bat` manualmente.
- Verifica que `http://localhost:8000/ping` responde.

### No se encontró FFmpeg

Instala FFmpeg y asegúrate de que tanto `ffmpeg` como `ffprobe` están en el
`PATH`. Reinicia la terminal o el servidor después de instalarlo.

### YouTube rechaza la descarga

El comportamiento depende del vídeo, de la disponibilidad regional y de las
medidas aplicadas por YouTube. Actualiza `yt-dlp` y comprueba que el vídeo se
puede reproducir normalmente en el navegador. Respeta siempre los derechos de
autor, los términos de uso de YouTube y las leyes aplicables.

## Licencia y uso responsable

Este proyecto es una herramienta local de uso personal. El usuario es
responsable de utilizarlo únicamente con contenido que tenga derecho a
descargar y transformar.
