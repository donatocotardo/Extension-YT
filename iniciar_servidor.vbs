Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Detecta automáticamente la ruta de la carpeta
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' Ejecuta el servidor en completo silencio con pythonw
WshShell.Run chr(34) & currentDir & "\.venv\Scripts\pythonw.exe" & chr(34) & " server.py", 0, False