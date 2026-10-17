const statusEl = document.getElementById("status");
const btnMp3 = document.getElementById("btn-mp3");
const btnMp4 = document.getElementById("btn-mp4");
const BASE_URL = "http://localhost:8000";

async function getCurrentTabUrl() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.url || "";
}

function setButtonsState(disabled) {
  btnMp3.disabled = disabled;
  btnMp4.disabled = disabled;
}

async function ensureServerRunning() {
  try {
    if ((await fetch(`${BASE_URL}/ping`)).ok) return true;
  } catch {}

  statusEl.textContent = "Iniciando servidor local...";
  let startError;
  try {
    chrome.runtime.sendNativeMessage(
      "com.ytdownloader.starter",
      {},
      () => {
        if (chrome.runtime.lastError) {
          startError = chrome.runtime.lastError.message;
        }
      },
    );
  } catch (error) {
    startError = error.message;
  }

  // Dar tiempo al host nativo para iniciar el servidor.
  for (let i = 0; i < 12; i++) {
    await new Promise((r) => setTimeout(r, 500));
    try {
      if ((await fetch(`${BASE_URL}/ping`)).ok) return true;
    } catch {}
  }

  const detail = startError ? ` (${startError})` : "";
  throw new Error(
    `No se pudo iniciar el servidor local${detail}. Haz doble clic en launcher.bat y vuelve a intentarlo.`,
  );
}

async function triggerDownload(format) {
  let url = await getCurrentTabUrl();

  if (!url.includes("youtube.com/watch") && !url.includes("youtu.be/")) {
    statusEl.textContent = "No estás en un vídeo de YouTube.";
    return;
  }

  try {
    const parsedUrl = new URL(url);
    const videoId = parsedUrl.searchParams.get("v");
    if (videoId) {
      url = `https://www.youtube.com/watch?v=${videoId}`;
    }
  } catch (e) {}

  setButtonsState(true);

  try {
    await ensureServerRunning();
    statusEl.textContent = `Procesando ${format.toUpperCase()}...`;

    const response = await fetch(`${BASE_URL}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, format: format }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Error en el servidor");
    }

    const contentDisposition = response.headers.get("Content-Disposition");
    let filename = `descarga.${format}`;
    if (contentDisposition && contentDisposition.includes("filename=")) {
      filename = contentDisposition.split("filename=")[1].replace(/["']/g, "");
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    await chrome.downloads.download({
      url: blobUrl,
      filename: filename,
      saveAs: true,
    });

    statusEl.textContent = "¡Descarga iniciada!";
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    setButtonsState(false);
  }
}

btnMp3.addEventListener("click", () => triggerDownload("mp3"));
btnMp4.addEventListener("click", () => triggerDownload("mp4"));