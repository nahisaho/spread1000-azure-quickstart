# 06 — 片付け

このシナリオはローカル CPU のみで完結するため、Azure リソースはありません。

## ローカル

```bash
# outputs 削除
rm -rf outputs/*.pt outputs/*.png outputs/*.json

# 仮想環境
deactivate
rm -rf .venv
```

Windows PowerShell:
```powershell
Remove-Item -Recurse -Force outputs\*
deactivate
Remove-Item -Recurse -Force .venv
```
