@echo off
setlocal
set "VSCODE_CLI=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"
if exist "%VSCODE_CLI%" (
  call "%VSCODE_CLI%" --reuse-window "%~dp0.."
) else (
  call code --reuse-window "%~dp0.."
)
