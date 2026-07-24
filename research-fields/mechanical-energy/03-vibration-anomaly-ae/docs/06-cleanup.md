# 06 — 片付け

このシナリオはローカル CPU のみで完結するため、Azure リソースはありません。

```bash
rm -rf data/*.npz data/*.png outputs/*.pt outputs/*.png outputs/*.json
deactivate
rm -rf .venv
```

Windows PowerShell:
```powershell
Remove-Item -Force data\*.npz, data\*.png
Remove-Item -Force outputs\*.pt, outputs\*.png, outputs\*.json
deactivate
Remove-Item -Recurse -Force .venv
```
