# 01: 前提条件・環境準備

## Python 環境

- **Python 3.12** 推奨（3.10〜3.12 で動作）
- 仮想環境の作成:
  ```bash
  python -m venv .venv
  source .venv/bin/activate      # Linux/macOS/WSL
  .venv\Scripts\activate         # Windows PowerShell
  ```

## Python パッケージ

**CPU / スモークテスト**:
```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-cpu.txt
```

**GPU (Azure ML T4 / cu126 対応の手元 GPU)**:
```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements-gpu.txt
```

> **NOTE**: `torch` のインストールは `requirements-*.txt` とは **別行** で行います。PyPI の `torch` は CPU 版なので、GPU 環境では明示的に cu126 wheel を選ぶ必要があります。

## HuggingFace アカウント（任意）

**Phi-4-mini-instruct と Qwen2.5-0.5B はゲートなし** — アカウント無しでダウンロード可能です。以下のモデルを使う場合のみ HF アカウント + アクセス申請が必要:

- `meta-llama/Llama-3.*`
- `mistralai/Mistral-*` (7B 以上の一部)

必要な場合:
```bash
pip install huggingface_hub
huggingface-cli login
# → https://huggingface.co/settings/tokens で "Read" 権限のトークンを生成し貼り付け
```

## Azure サブスクリプション（GPU パスのみ）

Azure ML T4 経路を使う場合、以下が必要です:

1. **Azure サブスクリプション**（従量課金、無料試用も可）
2. **NCasT4_v3 の GPU クォータ ≥ 4 vCPU**（新規サブスクリプションは既定 0）
   - Azure Portal → **Subscriptions → your subscription → Usage + quotas**
   - "Standard NCasT4v3 Family vCPUs" を検索 → Region "Japan East" → Request increase to **4**
   - 承認まで **1〜3 営業日**（新規サブスクの場合は追加審査あり）
3. **Azure ML ワークスペース**（Japan East 推奨）
   - Portal で "Azure Machine Learning" を検索 → Create
   - リソースグループを新規作成（`rg-spread1000-e1` など）
   - Workspace 名（`aml-llm-lora-jp` など）
4. **Compute cluster** — [docs/03-aml-gpu.md](03-aml-gpu.md) で作成手順

クォータ待機中は [docs/02-cpu-smoketest.md](02-cpu-smoketest.md) の CPU パスでパイプラインを検証できます。

## ディスク・メモリ

| パス | ディスク | RAM | GPU VRAM |
|---|---:|---:|---:|
| CPU スモークテスト (`Qwen2.5-0.5B`) | 3 GB | 8 GB | — |
| GPU (`Phi-4-mini`, QLoRA 4-bit) | 8 GB | 16 GB | 10 GB |
| GPU (`Phi-4-mini`, LoRA fp16) | 8 GB | 16 GB | 16 GB (T4 限界) |

## トラブル時

- `torch.cuda.is_available()` が `False` → NVIDIA ドライバ・CUDA バージョン確認（`nvidia-smi`）
- `ImportError: bitsandbytes` → CPU パスなら `--no-quant` を付けて呼び出す
- HuggingFace のダウンロードが遅い → `HF_HUB_ENABLE_HF_TRANSFER=1` を環境変数に設定

詳細は [`troubleshooting.md`](../troubleshooting.md) を参照。
