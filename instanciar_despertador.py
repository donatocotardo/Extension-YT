import os
import json
import winreg

EXTENSION_ID = input("Pega aquí el ID de tu extensión de Chrome: ").strip()

base_dir = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(base_dir, "launcher.bat")
manifest_path = os.path.join(base_dir, "native_host.json")
host_name = "com.ytdownloader.starter"

host_manifest = {
    "name": host_name,
    "description": "Despertador del servidor local YT",
    "path": bat_path,
    "type": "stdio",
    "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"]
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(host_manifest, f, indent=2)

reg_path = rf"Software\Google\Chrome\NativeMessagingHosts\{host_name}"
with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)

print("¡Despertador registrado con éxito en Windows!")