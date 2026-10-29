$ErrorActionPreference = 'Continue'
wsl -d Ubuntu-24.04 -- systemctl --user disable workbench-model.service workbench-gateway.service
wsl -d Ubuntu-24.04 -- systemctl --user kill --signal=SIGKILL workbench-model.service
wsl -d Ubuntu-24.04 -- systemctl --user stop workbench-gateway.service
wsl -d Ubuntu-24.04 -- systemctl --user reset-failed workbench-model.service
# Covers the older Windows local model as well, without affecting games or cloud workers.
Get-Process | Where-Object { $_.ProcessName -match '^(LM Studio|llmster|llama-server)$' } | Stop-Process -Force
