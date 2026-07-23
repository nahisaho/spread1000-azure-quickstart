# 06 — 片付け

このシナリオはローカル CPU のみで完結するため、Azure リソースはありません。

```bash
rm -rf outputs/*.zip outputs/*.png outputs/*.json outputs/*.gif tb_logs/
deactivate
rm -rf .venv
```

Windows PowerShell:
```powershell
Remove-Item -Recurse -Force outputs\*, tb_logs
deactivate
Remove-Item -Recurse -Force .venv
```
