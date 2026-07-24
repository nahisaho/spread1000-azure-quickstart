# 01 — 前提条件

## 環境

- Python 3.10 以上 (3.12 推奨)
- Windows / macOS / Linux
- CPU のみで OK (おおむね 7〜12 分)

## インストール

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip

# --- torch のインストール (プラットフォームごとに異なる) ---
# Windows/Linux (CPU):
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
# macOS (universal2, native pytorch install):
python -m pip install torch==2.7.1
# Linux + CUDA 12.x (optional, for --device cuda):
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu121

# --- その他の依存関係 ---
python -m pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt
# macOS の場合: requirements-lock/macos-cpu-py312.txt
# Windows の場合: requirements-lock/windows-cpu-py312.txt
```

## 動作確認

```bash
python -c "
import torch, numpy, matplotlib
v = torch.__version__.split('+')[0]
assert v == '2.7.1', f'torch version mismatch: {torch.__version__}'
print('torch', torch.__version__, '| cuda:', torch.cuda.is_available())
print('numpy', numpy.__version__)
print('matplotlib', matplotlib.__version__)
"
```

`torch 2.7.1+cpu | cuda: False` と出れば OK (macOS は `2.7.1`)。
