# 06 — 片付け

Azure リソースなし、CPU ローカルのみ。

```bash
rm -f data/pathmnist.npz
rm -rf outputs/*
deactivate && rm -rf .venv
```

PathMNIST データ (~205MB) は `data/pathmnist.npz` に保存されるので、再学習しないなら削除して OK (`data/README.md` は残ります)。
