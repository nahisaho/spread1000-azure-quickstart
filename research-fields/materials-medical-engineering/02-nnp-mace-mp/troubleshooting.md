# Troubleshooting

## インストール

### `RuntimeError: PyTorch 2.4.1 not supported`
mace-torch は PyTorch 2.4.1 を明示的に拒否します。
```bash
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121  # または cpu
```

### `_pickle.UnpicklingError: Weights only load failed`
PyTorch 2.6+ の `torch.load` デフォルト変更が原因。
- 対策 1: `torch==2.4.0` に固定（推奨）
- 対策 2: mace-torch を最新 (`>=0.3.16`) に更新

### `torch.cuda.is_available() == False` なのに `--device cuda` を使った
CPU 版 PyTorch がインストールされています。venv を作り直して CUDA 版を入れ直してください。
```bash
pip uninstall -y torch torchvision torchaudio
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
```

### `ImportError: cannot import name 'mace_mp'`
古い mace-torch (`<0.3.10`) の可能性:
```bash
pip install --upgrade "mace-torch>=0.3.16"
```

## モデルのロード

### `mace_mp()` が固まる / タイムアウト
初回は ~80 MB のチェックポイントを **GitHub Releases** (`ACEsuit/mace-foundations`) から自動ダウンロードします (**Hugging Face ではありません**)。ネットワーク・プロキシ設定を確認:
```bash
export HTTPS_PROXY=http://your-proxy:8080
export HTTP_PROXY=http://your-proxy:8080
```

事前ダウンロードして SHA-256 で検証したい場合:
```bash
mkdir -p ~/.cache/mace/
curl -L -o ~/.cache/mace/mace-mpa-0-medium.model \
  https://github.com/ACEsuit/mace-foundations/releases/download/mace_mpa_0/mace-mpa-0-medium.model
sha256sum ~/.cache/mace/mace-mpa-0-medium.model
# 期待値: 75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
python src/relax.py --system Si --model-path ~/.cache/mace/mace-mpa-0-medium.model \
  --model-sha256 75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
```

### `FileNotFoundError: mace-mpa-0-medium.model`
キャッシュディレクトリ（`~/.cache/mace/`）の書き込み権限を確認。または明示パス:
```python
calc = mace_mp(model="/absolute/path/to/mace-mpa-0-medium.model", device="cpu")
```

### `KeyError: 'element X not in model'`
入力構造に MACE-MPA-0 の学習分布外の元素が含まれています。対応元素は Materials Project 上でトラジェクトリが十分ある主要元素セットに限られ、超ウラン元素などは非対応です。厳密なリスト取得方法は `docs/07-ethics-and-limits.md` を参照。本 quickstart の `src/relax.py` は範囲外なら `--allow-elements-outside-domain` を要求します。

## 実行時エラー

### `RuntimeError: expected scalar type Float but found Double`
`default_dtype` が構造と食い違っています。**同一プロセス内で dtype を混在させない**でください:
```python
# NG
calc32 = mace_mp(dtype="float32")
calc64 = mace_mp(dtype="float64")   # ← ここで壊れる
```

### 緩和が 300 ステップで収束しない
- 初期構造が壊れている（`ase gui data/initial.extxyz` で確認）
- 対称性が急激に変化する系（金属間化合物など）
- 対策: `--fmax 0.1 --max-steps 500` で緩めるか、初期構造を対称化してから再挑戦

### MD で `NaN` が出る
- タイムステップが大きすぎる: `--timestep-fs 0.5` に
- 初速度が過剰: `--temperature` を下げる、または初速度シードを変える

## Azure ML 固有

### Compute Instance が起動しない
GPU クォータ未承認の可能性。「Portal → Subscriptions → Usage + Quotas」で `NCASv3_T4 Family vCPUs` の使用量を確認。承認待ちなら CPU (`E4s_v3`) で先に実行することも可能。

### CommandJob が `pip install` で失敗
curated 環境のインターネットアクセスが制限されている可能性。プライベート エンドポイント環境では、事前に mace-torch を含むカスタム Docker イメージを ACR に置いて `Environment(image=...)` で参照してください。

### 停止するのを忘れて課金が続いた
Azure Cost Management のアラートを $10 などに設定。次回からは Compute Instance 作成時に必ず `idleTimeBeforeShutdown="PT60M"` を有効化。

## 出力

### `md.traj` を Ovito で開くと 1 フレームしかない
`--save-every 10` かつ `--steps 100` などの短い実行では、記録フレーム数が少なくなります。`--steps` を増やすか `--save-every 1` に。

### `relaxed.cif` が正しく VESTA で開けない
セルが著しく歪んでいる場合、CIF の対称性判定に失敗することがあります。`relaxed.extxyz` を Ovito で確認するのが確実です。
