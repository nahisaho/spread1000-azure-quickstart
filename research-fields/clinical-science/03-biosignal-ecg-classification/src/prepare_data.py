"""Prepare MIT-BIH records → (window, label) NPZ files.

Reads all *.dat / *.atr files in --data-dir (assumed to be the extracted
`mitdb-1.0.0/` folder). For each record:
  - detect the MLII (or fallback II) channel
  - centre a 180-sample window around each beat annotation
  - map MIT-BIH beat symbol → AAMI 5-class (N/S/V/F/Q)
  - drop non-beat annotations and boundary-crossing windows

Split records at the record level (not beat level) to keep beats from the same
recording out of multiple splits. The default split is the canonical de Chazal
et al. 2004 DS1/DS2 partition (44 records after excluding paced 102/104/107/217),
with an extra dev split carved out of DS1.

Known caveat: MIT-BIH records 201 and 202 come from the same subject
(Holter tape #201 was split into two files). The canonical DS1/DS2 protocol
places 201 in DS1 (train) and 202 in DS2 (test), so this quickstart preserves
that convention for comparability with published baselines but is therefore
not strictly patient-independent. If you need strict patient independence,
move 202 into DS_TRAIN (or drop it) and re-run.

Writes: <out-dir>/{train,val,test}.npz with arrays X (N, 1, 180) float32
and y (N,) int64. Also writes prep_manifest.json with counts and record IDs.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import wfdb

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# AAMI 5-class mapping (ANSI/AAMI EC57; de Chazal et al. 2004)
AAMI_MAP: dict[str, str] = {
    **dict.fromkeys(["N", "L", "R", "e", "j"], "N"),
    **dict.fromkeys(["A", "a", "J", "S"], "S"),
    **dict.fromkeys(["V", "E"], "V"),
    "F": "F",
    **dict.fromkeys(["/", "f", "Q"], "Q"),
}
CLASSES: list[str] = ["N", "S", "V", "F", "Q"]
CLASS_TO_INT: dict[str, int] = {c: i for i, c in enumerate(CLASSES)}

# Standard inter-patient split (de Chazal DS1/DS2, 44 records).
# Paced records (102, 104, 107, 217) are excluded from BOTH train and test per the
# original protocol — the pacemaker spike dominates morphology and biases evaluation.
# This means class Q has very few beats: expect Q F1 to be low / noisy.
DS_TRAIN = ["101", "106", "108", "109", "112", "114", "115", "116", "118",
            "119", "122", "124", "201", "203", "205", "207", "208", "209",
            "215", "220", "223", "230"]
DS_TEST = ["100", "103", "105", "111", "113", "117", "121", "123", "200",
           "202", "210", "212", "213", "214", "219", "221", "222", "228",
           "231", "232", "233", "234"]
PACED_RECORDS = ["102", "104", "107", "217"]  # excluded per de Chazal et al. 2004

# Half window = 90 samples ⇒ 180-sample window ≈ 500 ms at 360 Hz
HALF_WINDOW = 90

logger = logging.getLogger(__name__)


def pick_lead(record: wfdb.Record) -> int:
    """Return the channel index for MLII (fallback: II, then channel 0)."""
    for name in ("MLII", "II"):
        if name in record.sig_name:
            return record.sig_name.index(name)
    return 0


def extract_beats(record_dir: Path, record_id: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y) for one record. X shape (N, 180). y int class indices."""
    rec = wfdb.rdrecord(str(record_dir / record_id))
    ann = wfdb.rdann(str(record_dir / record_id), extension="atr")
    lead = pick_lead(rec)
    signal = rec.p_signal[:, lead].astype(np.float32)

    xs, ys = [], []
    for r_sample, symbol in zip(ann.sample, ann.symbol, strict=True):
        aami = AAMI_MAP.get(symbol)
        if aami is None:
            continue  # non-beat or unmapped
        start = r_sample - HALF_WINDOW
        end = r_sample + HALF_WINDOW
        if start < 0 or end > rec.sig_len:
            continue
        window = signal[start:end]
        # per-window standardisation (robust to inter-record amplitude drift)
        std = window.std()
        if std < 1e-6:
            continue
        window = (window - window.mean()) / std
        xs.append(window)
        ys.append(CLASS_TO_INT[aami])

    if not xs:
        return np.empty((0, 2 * HALF_WINDOW), dtype=np.float32), np.empty((0,), dtype=np.int64)
    return np.stack(xs).astype(np.float32), np.asarray(ys, dtype=np.int64)


def stack_records(record_dir: Path, record_ids: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    xs, ys, present = [], [], []
    for rid in record_ids:
        hea = record_dir / f"{rid}.hea"
        if not hea.exists():
            logger.warning("Record %s not found under %s, skipping.", rid, record_dir)
            continue
        x, y = extract_beats(record_dir, rid)
        if len(x) == 0:
            logger.warning("Record %s produced 0 valid beats, skipping.", rid)
            continue
        xs.append(x)
        ys.append(y)
        present.append(rid)
    if not xs:
        raise RuntimeError(f"No usable records found in {record_dir}")
    X = np.concatenate(xs, axis=0)[:, np.newaxis, :]  # (N, 1, 180)
    Y = np.concatenate(ys, axis=0)
    return X, Y, present


def _class_counts(y: np.ndarray) -> dict[str, int]:
    return {CLASSES[i]: int((y == i).sum()) for i in range(len(CLASSES))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Folder containing MIT-BIH *.dat/*.atr files")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--val-fraction", type=float, default=0.15,
                        help="Fraction of DS_TRAIN records reserved for validation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    record_dir = Path(args.data_dir)
    if not any(record_dir.glob("*.dat")):
        # data may live one level deep (extracted zip)
        candidates = [p.parent for p in record_dir.rglob("*.dat")]
        if not candidates:
            raise FileNotFoundError(f"No *.dat files under {record_dir}")
        record_dir = candidates[0]
        logger.info("Auto-detected record_dir=%s", record_dir)

    rng = np.random.default_rng(args.seed)
    ds_train_shuffled = list(DS_TRAIN)
    rng.shuffle(ds_train_shuffled)
    n_val = max(1, int(len(ds_train_shuffled) * args.val_fraction))
    val_ids = ds_train_shuffled[:n_val]
    train_ids = ds_train_shuffled[n_val:]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"seed": args.seed, "splits": {}, "records": {}, "class_counts": {}}
    for split_name, ids in [("train", train_ids), ("val", val_ids), ("test", DS_TEST)]:
        X, y, present = stack_records(record_dir, ids)
        np.savez_compressed(out_dir / f"{split_name}.npz", X=X, y=y)
        manifest["splits"][split_name] = present
        manifest["class_counts"][split_name] = _class_counts(y)
        manifest["records"][split_name] = len(present)
        logger.info(
            "%-5s N=%d records=%d classes=%s",
            split_name, len(y), len(present), manifest["class_counts"][split_name],
        )

    (out_dir / "prep_manifest.json").write_text(json.dumps(manifest, indent=2))
    logger.info("Wrote %s", out_dir / "prep_manifest.json")


if __name__ == "__main__":
    main()
