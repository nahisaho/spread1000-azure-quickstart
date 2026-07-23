# 06 — 片付け

このシナリオはローカル CPU のみで完結するため、Azure リソースはありません。

```bash
rm -rf data/*.npz outputs/*.pt outputs/*.png outputs/*.json
deactivate
rm -rf .venv
```

Windows PowerShell:
```powershell
Remove-Item -Recurse -Force data\*, outputs\*
deactivate
Remove-Item -Recurse -Force .venv
```
