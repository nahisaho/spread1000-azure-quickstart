# トラブルシューティング

## `AttributeError: module 'numpy' has no attribute 'bool8'` (or similar)

- SB3 2.9 と最新 numpy (2.x) の組み合わせで一部警告が出るが、実行には支障なし。
- 気になる場合: `pip install "numpy<2"`

## Windows で `SubprocVecEnv` がハング

- Windows の spawn 方式では `if __name__ == "__main__":` guard が必須。
- 本教材の `src/train.py` は guard 済み。**必ず `python src/train.py` で直接実行**してください (notebook からは推奨しません)。

## 学習が全く進まない (rew_mean が 20 付近から動かない)

- `--seed` を 0, 1, 2 と変えて試す (乱数の初期化運)
- `--n-steps 2048` に増やす
- `--n-envs 8` に増やす (CPU コア数以下で)

## `gymnasium.error.NamespaceNotFound` for LunarLander

- `pip install "gymnasium[box2d]==1.3.0"` を追加してください
- LunarLander の正しい ID は **`LunarLander-v3`** (Gymnasium 1.x 系; v2 は廃止)
- Windows では swig が必要な場合あり: `pip install swig` を先に

## TensorBoard が起動しない

- 別ターミナルで: `tensorboard --logdir tb_logs --port 6006`
- ポートが埋まっている場合: `--port 6007`

## macOS で `Segmentation fault`

- Apple Silicon で稀に SubprocVecEnv がクラッシュ。`--n-envs 1` で直列実行 (DummyVecEnv) に切り替えて回避。
