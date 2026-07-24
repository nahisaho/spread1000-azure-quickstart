"""Predict products for a reactions CSV using ReactionT5v2-forward.

Input CSV columns:
  reactants           (required): SMILES, dot-separated for multi-component
  reagents            (optional): SMILES for reagents/catalysts/solvents (may be empty)
  reference_product   (optional): reference SMILES for top-1 accuracy metric

Outputs (to --output-dir):
  predictions.csv     — one row per input with pred_smiles, canon_pred, canon_ref, match

Logs to MLflow:
  num_reactions, valid_ratio, top1_accuracy (only if references present)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import mlflow
import pandas as pd
import torch
from huggingface_hub import snapshot_download
from rdkit import Chem, RDLogger
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

RDLogger.DisableLog("rdApp.*")

REPO_ID = "sagawa/ReactionT5v2-forward"


def canonicalize(smiles: str) -> str | None:
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def build_input(reactants: str, reagents: str) -> str:
    reactants = (reactants or "").strip()
    reagents = (reagents or "").strip()
    return f"REACTANT:{reactants}REAGENT:{reagents}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reactions", required=True, help="Input CSV path (uri_file mount).")
    ap.add_argument("--output-dir", required=True, help="Output folder (uri_folder mount).")
    ap.add_argument("--num-beams", type=int, default=5)
    ap.add_argument("--max-new-tokens", type=int, default=100)
    ap.add_argument("--max-input-length", type=int, default=150)
    ap.add_argument(
        "--model-revision",
        default="933114058cb2604dc1bf536dbebdfcefbe83d4fc",
        help="Pinned HF revision for reproducibility.",
    )
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.reactions)
    if "reactants" not in df.columns:
        raise SystemExit("Input CSV must have a 'reactants' column.")
    if "reagents" not in df.columns:
        df["reagents"] = ""
    if "reference_product" not in df.columns:
        df["reference_product"] = ""
    df = df.fillna("")

    print(f"[predict] Downloading model {REPO_ID}@{args.model_revision[:8]} ...", flush=True)
    local_model_dir = snapshot_download(
        repo_id=REPO_ID,
        revision=args.model_revision,
        cache_dir="/tmp/hf_cache",
        allow_patterns=["*.json", "*.safetensors", "*.model", "README.md"],
    )

    if not torch.cuda.is_available():
        # This job is templated on a T4 GPU compute (aml/job-predict.yml
        # requests Standard_NC4as_T4_v3). A CUDA-less fallback to CPU would
        # still bill the GPU VM at ~$0.53/hr while running 10-50x slower.
        # Fail fast so the user diagnoses the driver/runtime issue.
        raise RuntimeError(
            "CUDA is not available on this compute. The ReactionT5 predict job "
            "is templated for a T4 GPU (Standard_NC4as_T4_v3); running on CPU "
            "would still incur GPU VM billing. Check compute image (should be "
            "openmpi-cuda), verify torch was installed with CUDA wheels, and "
            "confirm 'nvidia-smi' works inside the container."
        )
    device = torch.device("cuda")
    print(
        f"[predict] device={device} name={torch.cuda.get_device_name(0)} "
        f"torch={torch.__version__} cuda={torch.version.cuda}",
        flush=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(local_model_dir)
    model = (
        AutoModelForSeq2SeqLM.from_pretrained(local_model_dir, use_safetensors=True)
        .to(device)
        .eval()
    )

    preds: list[str] = []
    canon_preds: list[str | None] = []
    canon_refs: list[str | None] = []
    matches: list[bool | None] = []
    truncated_rows: list[int] = []

    for i, row in df.iterrows():
        text = build_input(str(row["reactants"]), str(row["reagents"]))
        # Detect and warn about truncation before we invoke the model, so a
        # silently truncated reaction can't masquerade as a successful
        # prediction. `.encode(...)` returns the un-truncated token count.
        full_len = len(tokenizer.encode(text, add_special_tokens=True))
        if full_len > args.max_input_length:
            truncated_rows.append(int(i))
            print(
                f"  WARN row {i}: input has {full_len} tokens > "
                f"max_input_length={args.max_input_length}; will be truncated. "
                "Prediction may not reflect the full reaction.",
                flush=True,
            )
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_input_length,
        ).to(device)
        with torch.inference_mode():
            tokens = model.generate(
                **inputs,
                num_beams=args.num_beams,
                max_new_tokens=args.max_new_tokens,
                early_stopping=True,
            )
        pred = tokenizer.decode(tokens[0], skip_special_tokens=True).replace(" ", "").rstrip(".")
        preds.append(pred)

        cp = canonicalize(pred)
        canon_preds.append(cp)

        cr_raw: str | None = None
        cr: str | None = None
        ref = str(row["reference_product"]).strip()
        if ref:
            # Non-empty reference must be a parseable SMILES; otherwise the
            # accuracy denominator becomes silently biased. Fail fast so the
            # user fixes their data instead of trusting an inflated metric.
            cr = canonicalize(ref)
            if cr is None:
                raise ValueError(
                    f"row {i}: reference_product '{ref}' is not a valid SMILES "
                    "(RDKit could not parse). Either remove the value to mark the "
                    "row as unscored, or fix the SMILES. Rows are 0-indexed."
                )
            cr_raw = ref
        canon_refs.append(cr)

        # Reference present and valid ⇒ True/False. Reference absent ⇒ None (unscored).
        # Reference invalid was rejected above.
        if cr is not None:
            matches.append(cp == cr)
        else:
            matches.append(None)

        print(f"  [{i+1}/{len(df)}] pred={cp} ref={cr} match={matches[-1]}", flush=True)

    out_df = df.copy()
    out_df["pred_smiles"] = preds
    out_df["canon_pred"] = canon_preds
    out_df["canon_ref"] = canon_refs
    out_df["match"] = matches
    predictions_csv = out_dir / "predictions.csv"
    out_df.to_csv(predictions_csv, index=False)
    print(f"[predict] Wrote {predictions_csv}", flush=True)

    n_valid = sum(1 for cp in canon_preds if cp is not None)
    scored = [m for m in matches if m is not None]
    num_scored = len(scored)
    num_unscored = len(matches) - num_scored
    top1 = (sum(1 for m in scored if m) / num_scored) if scored else float("nan")
    valid_ratio = n_valid / len(canon_preds) if canon_preds else 0.0

    mlflow.log_metric("num_reactions", len(df))
    mlflow.log_metric("num_scored", num_scored)
    mlflow.log_metric("num_unscored", num_unscored)
    mlflow.log_metric("num_truncated", len(truncated_rows))
    mlflow.log_metric("valid_ratio", valid_ratio)
    if scored:
        mlflow.log_metric("top1_accuracy", top1)
    mlflow.log_artifact(str(predictions_csv))

    if truncated_rows:
        print(
            f"[predict] WARNING: {len(truncated_rows)} row(s) exceeded "
            f"max_input_length={args.max_input_length} tokens and were "
            f"truncated: {truncated_rows}",
            flush=True,
        )
    print(
        f"[predict] SUMMARY: num_reactions={len(df)} "
        f"valid_ratio={valid_ratio:.3f} top1_accuracy={top1:.3f} "
        f"(scored={num_scored}, unscored={num_unscored})",
        flush=True,
    )


if __name__ == "__main__":
    main()
