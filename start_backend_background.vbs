Set WshShell = CreateObject("WScript.Shell")
' Launch start_backend.bat with 0 = hidden window (runs silently in the background)
WshShell.Run chr(34) & "c:\Users\saiab\OneDrive\Desktop\GNN-Based Fraud Detection\Financial-Fraud-Detection\start_backend.bat" & chr(34), 0
Set WshShell = Nothing

