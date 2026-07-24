"""QLoRA supervised fine-tuning (SFT) with `trl.SFTTrainer` and `peft`.

Primary path: Azure ML T4 (NCasT4_v3) + Phi-4-mini-instruct + QLoRA 4-bit + fp16.
Smoke-test path: CPU + Qwen2.5-0.5B-Instruct + LoRA (no quantization).

Usage — GPU (T4):
    python src/train_lora.py \
        --model microsoft/Phi-4-mini-instruct \
        --model-revision cfbefacb99257ffa30c83adab238a50856ac3083 \
        --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb \
        --data data/train.jsonl --output data/adapter/

Usage — CPU smoke test (Qwen2.5-0.5B, 100 samples, 1 epoch):
    python src/train_lora.py \
        --model Qwen/Qwen2.5-0.5B-Instruct \
        --model-revision 7ae557604adf67be50417f59c2c2f167def9a775 \
        --dataset-revision 6391034b0126850543299cda071dc6281c31a6fb \
        --data data/train.jsonl \
        --epochs 1 --device cpu --no-quant \
        --output data/adapter/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

from _argtypes import nonnegative_float, positive_float, positive_int

# ── License allowlist ────────────────────────────────────────────────────────
_LICENSE_ALLOWLIST: dict[str, tuple[str, str]] = {
    "microsoft/phi-4-mini-instruct":  ("MIT",        "https://huggingface.co/microsoft/Phi-4-mini-instruct"),
    "qwen/qwen2.5-0.5b-instruct":     ("Apache-2.0", "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct"),
}


def _check_license(model_id: str, model_license: str | None, accept: bool) -> tuple[str, str]:
    """Return (license_spdx, license_url). Raise on policy violation."""
    key = model_id.lower()
    if key in _LICENSE_ALLOWLIST:
        spdx, url = _LICENSE_ALLOWLIST[key]
        print(f"[license] {model_id} — {spdx} (pre-approved) — {url}")
        return spdx, url
    # Outside allowlist
    if not model_license or not accept:
        raise SystemExit(
            f"[error] Model {model_id!r} is not in the pre-approved allowlist.\n"
            "Provide both --model-license <SPDX> and --accept-model-license to acknowledge "
            "you have read and accepted the model license before using it."
        )
    url = f"https://huggingface.co/{model_id}"
    print(f"[license] {model_id} — {model_license} (user-accepted) — {url}")
    return model_license, url


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Model / data
    p.add_argument("--model", default="microsoft/Phi-4-mini-instruct",
                   help="HuggingFace model ID.")
    p.add_argument("--model-revision", required=True,
                   help="Pinned model commit SHA (required for reproducibility).")
    p.add_argument("--dataset-revision", required=True,
                   help="Pinned dataset commit SHA (required for reproducibility).")
    p.add_argument("--trust-remote-code", action="store_true",
                   help="Allow remote code execution from the model repo (off by default).")
    p.add_argument("--data", type=Path, default=Path("data/train.jsonl"),
                   help="Chat-formatted JSONL from prepare_data.py")
    p.add_argument("--output", type=Path, default=Path("data/adapter/"))
    # License
    p.add_argument("--model-license", default=None,
                   help="SPDX license identifier for models outside the pre-approved allowlist.")
    p.add_argument("--accept-model-license", action="store_true",
                   help="Confirm you have read and accepted the model license.")
    # Hyperparameters
    p.add_argument("--epochs", type=positive_int, default=3)
    p.add_argument("--max-steps", type=int, default=-1,
                   help="Override epochs with a fixed step count (-1 = off).")
    p.add_argument("--batch-size", type=positive_int, default=2,
                   help="Per-device batch size; keep 1-2 on T4 16GB")
    p.add_argument("--grad-accum", type=positive_int, default=4,
                   help="Gradient accumulation steps (effective batch = batch-size * grad-accum)")
    p.add_argument("--lr", type=positive_float, default=2e-4)
    p.add_argument("--warmup-ratio", type=nonnegative_float, default=0.03,
                   help="Warmup fraction of total steps [0, 1).")
    p.add_argument("--max-seq-length", type=positive_int, default=512)
    p.add_argument("--lora-r", type=positive_int, default=16)
    p.add_argument("--lora-alpha", type=positive_int, default=32)
    p.add_argument("--lora-dropout", type=nonnegative_float, default=0.05,
                   help="LoRA dropout rate [0, 1).")
    p.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    p.add_argument("--no-quant", action="store_true",
                   help="Disable 4-bit quantization (required for CPU or non-CUDA GPU)")
    p.add_argument("--seed", type=int, default=42)
    # Safety limits
    p.add_argument("--max-gpu-hours", type=positive_float, default=1.0,
                   help="Hard wall-clock limit in hours (GPU only). Default 1.0 h.")
    p.add_argument("--allow-long-run", action="store_true",
                   help="Required when estimated or actual run time exceeds 2 hours.")
    # Checkpoint
    p.add_argument("--resume-from-checkpoint", default=None,
                   help="Path to a checkpoint directory to resume from (e.g. for spot preemption).")
    return p.parse_args()


def _validate_warmup(args: argparse.Namespace) -> None:
    if not (0 <= args.warmup_ratio < 1):
        raise SystemExit(f"[error] --warmup-ratio must be in [0, 1), got {args.warmup_ratio}")
    if not (0 <= args.lora_dropout < 1):
        raise SystemExit(f"[error] --lora-dropout must be in [0, 1), got {args.lora_dropout}")


def resolve_device(pref: str) -> str:
    import torch
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit(
                "[error] --device cuda requested but torch.cuda.is_available() is False. "
                "Check your CUDA installation. Use --device auto or --device cpu."
            )
        return "cuda"
    return "cuda" if torch.cuda.is_available() else "cpu"


def _set_seed(seed: int) -> None:
    """Full determinism setup for reproducible runs."""
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    import torch
    import transformers
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    transformers.set_seed(seed)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class FiniteLossCallback:
    """Raise immediately if training loss or eval_loss becomes non-finite."""

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is None:
            return
        for key in ("loss", "eval_loss"):
            val = logs.get(key)
            if val is not None and not math.isfinite(float(val)):
                raise RuntimeError(
                    f"[FiniteLossCallback] Training halted: {key}={val} is non-finite. "
                    "Check learning rate, data quality, and fp16/bf16 settings."
                )


def main() -> int:
    args = parse_args()
    _validate_warmup(args)

    if not args.data.exists():
        print(f"[error] Data file not found: {args.data}. Run src/prepare_data.py first.",
              file=sys.stderr)
        return 1

    # Wall-clock limit check
    MAX_HOURS_ALLOW_LONG = 2.0
    if args.max_gpu_hours > MAX_HOURS_ALLOW_LONG and not args.allow_long_run:
        raise SystemExit(
            f"[error] --max-gpu-hours {args.max_gpu_hours} > {MAX_HOURS_ALLOW_LONG} hours. "
            "Pass --allow-long-run to confirm this is intentional."
        )

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        EarlyStoppingCallback,
        TrainerCallback,
    )
    from trl import SFTConfig, SFTTrainer

    device = resolve_device(args.device)
    use_quant = (not args.no_quant) and device == "cuda"

    _set_seed(args.seed)

    # ── License check ─────────────────────────────────────────────
    license_spdx, license_url = _check_license(
        args.model, args.model_license, args.accept_model_license
    )

    # ── 1. Tokenizer ───────────────────────────────────────────────
    print(f"[model] loading tokenizer for {args.model} @ {args.model_revision}")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        revision=args.model_revision,
        trust_remote_code=args.trust_remote_code,
    )
    added = 0
    if tokenizer.pad_token_id is None:
        added = tokenizer.add_special_tokens({"pad_token": "[PAD]"})
    tokenizer.padding_side = "right"

    # ── 2. Model ───────────────────────────────────────────────────
    model_kwargs: dict = {
        "revision": args.model_revision,
        "trust_remote_code": args.trust_remote_code,
    }
    if use_quant:
        from transformers import BitsAndBytesConfig
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        model_kwargs["device_map"] = "auto"
        model_kwargs["torch_dtype"] = torch.float16
    elif device == "cuda":
        model_kwargs["torch_dtype"] = torch.float16
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = torch.float32

    print(f"[model] loading {args.model} (device={device}, 4-bit={use_quant})")
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)

    if added:
        model.resize_token_embeddings(len(tokenizer))
    model.config.pad_token_id = tokenizer.pad_token_id
    model.generation_config.pad_token_id = tokenizer.pad_token_id

    if not use_quant and device == "cpu":
        model.to("cpu")

    # ── 3. QLoRA prep ─────────────────────────────────────────────
    if use_quant:
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        )
        model.config.use_cache = False

    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] total parameters: {n_params:,}")

    # ── 4. Dataset ─────────────────────────────────────────────────
    print(f"[data] loading {args.data}")
    full_ds = load_dataset("json", data_files=str(args.data), split="train")
    split = full_ds.train_test_split(test_size=0.1, seed=args.seed)
    train_ds = split["train"]
    eval_ds = split["test"]
    print(f"[data] train={len(train_ds)}, eval={len(eval_ds)} samples")

    # ── 5. LoRA config ─────────────────────────────────────────────
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules="all-linear",
    )

    # ── 6. Training config ─────────────────────────────────────────
    args.output.mkdir(parents=True, exist_ok=True)
    training_config = SFTConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=args.warmup_ratio,
        fp16=(device == "cuda"),
        bf16=False,
        gradient_checkpointing=(device == "cuda" and not use_quant),
        logging_steps=25,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        max_length=args.max_seq_length,
        report_to="none",
        seed=args.seed,
    )

    finite_cb = FiniteLossCallback()

    # Wrap FiniteLossCallback as a proper TrainerCallback
    class _FiniteCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            finite_cb.on_log(args, state, control, logs=logs, **kwargs)

    print(f"[train] starting: epochs={args.epochs}, batch={args.batch_size}x{args.grad_accum}, "
          f"lr={args.lr}, LoRA r={args.lora_r}")

    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_config,
        processing_class=tokenizer,
    )
    trainer.add_callback(EarlyStoppingCallback(early_stopping_patience=1))
    trainer.add_callback(_FiniteCallback())

    # Log matched/trainable modules
    trainable = [n for n, p in trainer.model.named_parameters() if p.requires_grad]
    print(f"[lora] trainable modules ({len(trainable)}): {trainable[:6]}{'...' if len(trainable) > 6 else ''}")

    if device == "cuda":
        for _n, p in trainer.model.named_parameters():
            if p.requires_grad and p.dtype != torch.float32:
                p.data = p.data.to(torch.float32)
        bad = [n for n, p in trainer.model.named_parameters()
               if p.requires_grad and p.dtype != torch.float32]
        assert not bad, f"non-fp32 trainable params remain: {bad[:3]}"

    start_time = time.time()
    train_result = trainer.train(
        resume_from_checkpoint=args.resume_from_checkpoint
    )
    elapsed_hours = (time.time() - start_time) / 3600

    # Wall-clock limit enforcement
    if device == "cuda" and elapsed_hours > args.max_gpu_hours:
        print(f"[warn] training exceeded --max-gpu-hours {args.max_gpu_hours:.2f}h "
              f"(actual: {elapsed_hours:.2f}h)", file=sys.stderr)

    # Post-training finite loss check
    train_loss = train_result.metrics.get("train_loss")
    if train_loss is None or not math.isfinite(float(train_loss)):
        print(f"[error] train_loss is non-finite: {train_loss}", file=sys.stderr)
        return 1

    # ── 7. Save adapter + tokenizer ───────────────────────────────
    final_dir = args.output / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(final_dir)
    print(f"[train] saved LoRA adapter → {final_dir}")

    # ── 8. Metrics ────────────────────────────────────────────────
    metrics = {
        "train_runtime_sec": train_result.metrics.get("train_runtime"),
        "train_samples_per_second": train_result.metrics.get("train_samples_per_second"),
        "train_loss": train_result.metrics.get("train_loss"),
        "eval_loss": train_result.metrics.get("eval_loss"),
        "epochs": args.epochs,
        "n_train_samples": len(train_ds),
        "n_eval_samples": len(eval_ds),
        "model": args.model,
        "model_revision": args.model_revision,
        "device": device,
        "quantized_4bit": use_quant,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
    }
    metrics_path = final_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"[train] metrics: {metrics}")

    # ── 9. Manifest ───────────────────────────────────────────────
    manifest: dict = {
        "model": args.model,
        "model_revision": args.model_revision,
        "dataset_revision": args.dataset_revision,
        "license_spdx": license_spdx,
        "license_url": license_url,
        "license_accepted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trust_remote_code": args.trust_remote_code,
        "seed": args.seed,
        "determinism_note": (
            "bitsandbytes QLoRA is not bitwise deterministic across versions. "
            "CPU/fp16 runs with torch.use_deterministic_algorithms(True) are reproducible."
        ),
        "files": {},
    }
    # Record SHA-256 for saved adapter files
    for f in sorted(final_dir.rglob("*")):
        if f.is_file() and f.name != "manifest.json":
            manifest["files"][str(f.relative_to(final_dir))] = sha256_file(f)

    # Record dataset SHA if available
    if args.data.exists():
        manifest["dataset_path"] = str(args.data)
        manifest["dataset_sha256"] = sha256_file(args.data)

    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"[train] manifest → {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
