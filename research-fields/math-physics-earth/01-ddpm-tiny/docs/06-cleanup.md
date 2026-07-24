# 06 — 片付け

ローカル CPU のみ。Azure リソースなし。

```bash
rm -rf data/ outputs/*.pt outputs/*.png outputs/*.json
deactivate 2>/dev/null || true
rm -rf .venv
```

PowerShell (Windows):

```powershell
Remove-Item -Recurse -Force data, outputs\*.pt, outputs\*.png, outputs\*.json -ErrorAction SilentlyContinue
deactivate; Remove-Item -Recurse -Force .venv
```
