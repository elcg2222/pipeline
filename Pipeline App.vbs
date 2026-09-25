' Pipeline App — double-click de chay, khong hien cua so cmd den
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Dung Python 3.13 (da cai cac thu vien can thiet)
py = "C:\Users\cuongle\AppData\Local\Programs\Python\Python313\python.exe"
If Not fso.FileExists(py) Then py = "python"

WshShell.CurrentDirectory = scriptDir
WshShell.Run """" & py & """ """ & scriptDir & "\desktop_app.py""", 0, False
