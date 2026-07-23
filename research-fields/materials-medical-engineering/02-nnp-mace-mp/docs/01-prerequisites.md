# 01 — 前提条件と環境準備

## 対象読者

- Python プログラミングの基礎はある（`pip install`、venv、for ループ）
- 結晶構造・分子動力学（MD）の概念は既知
- Azure は初めて（ローカル/WSL2 でも実行できるので、Azure 未使用でも OK）

## 必須ソフトウェア

| ソフト | バージョン | 備考 |
|---|---|---|
| **Python** | **3.10 / 3.11 / 3.12** | ⚠️ 3.13 は mace-torch 未対応 |
| **PyTorch** | **2.4.0**（推奨） | 2.4.1 は blacklisted、2.6+ は `weights_only` 問題あり |
| pip | 24.x 以降 | |
| Git | 任意 | 本リポジトリを clone する場合 |

## OS 別の推奨環境

| OS | 推奨実行環境 |
|---|---|
| **Windows** | **WSL2 + Ubuntu 22.04**（Windows ネイティブより pip の互換性が高い） |
| macOS (M1/M2/M3) | ネイティブ Python 3.12 (`brew install python@3.12`) |
| Linux | ネイティブ Python 3.10〜3.12 |

Windows ネイティブでも動作しますが、`torch` の CUDA 版インストールで詰まりやすいため WSL2 推奨です。

## インストール手順

### 1. Python 3.12 の仮想環境を作成

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -V   # Python 3.12.x であることを確認
```

### 2. PyTorch を先に固定インストール（重要）

**CPU のみで使う場合**:
```bash
pip install --upgrade pip
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu
```

**NVIDIA GPU (CUDA 12.1) を使う場合**:
```bash
pip install --upgrade pip
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
```

**GPU 動作確認**:
```python
import torch
print(torch.cuda.is_available())   # True であれば GPU 使用可
print(torch.version.cuda)          # "12.1"
```

> ⚠️ **なぜ PyTorch を先にインストールするのか**
> mace-torch は `torch` を依存関係として持ちますが、pip はそのままだと CPU 版を引いてくる可能性があります。GPU 版を確実に使うには、`torch` を先に手動インストールしてから mace-torch を入れてください。

### 3. mace-torch とその他

```bash
pip install -r requirements.txt
```

- `mace-torch>=0.3.16` — MACE 実装（MACE-MPA-0 モデルを含む）
- `ase>=3.23` — 構造構築・オプティマイザ・MD ドライバ
- `numpy>=1.26`

インストール後、モデルの初回ロードで **~80 MB のチェックポイント** を `~/.cache/mace/` に自動ダウンロードします（次回以降キャッシュされます）。

### 4. 動作確認

```bash
python -c "from mace.calculators import mace_mp; c = mace_mp(model='medium-mpa-0', device='cpu', default_dtype='float32'); print('OK')"
```

初回は数十秒〜数分（ダウンロード）、2 回目以降は数秒で "OK" が出れば準備完了です。

## 既知の互換性の落とし穴

| 症状 | 原因 | 対処 |
|---|---|---|
| `_pickle.UnpicklingError: Weights only load failed` | PyTorch 2.6+ の `torch.load` デフォルト変更 | `torch==2.4.0` に固定 |
| `RuntimeError: Not supported: PyTorch 2.4.1` | mace-torch が 2.4.1 を明示的に拒否 | `torch==2.4.0` に |
| `torch.cuda.is_available()` が False | CPU 版 torch がインストールされている | GPU 版 wheel を再インストール |
| `mace_mp()` が hang | 初回のチェックポイント ダウンロード中 | プロキシ設定・ネットワーク確認 |
| `RuntimeError: Both float32 and float64 in same session` | 同一プロセスで dtype を混在させた | 1 スクリプト内では `dtype` を統一 |

より詳しくは [../troubleshooting.md](../troubleshooting.md) を参照してください。

## Azure ML GPU で実行する場合

Azure ML の Compute Instance で GPU 実行したい場合は、[03-aml-gpu.md](03-aml-gpu.md) を参照。ローカル CPU で十分デモができるため、まずはローカル実行を推奨します。
