#!/usr/bin/env python
"""Module 10 vision classification evaluation runner (Task 1).

Usage:
    python eval/module10/runners/run_vision_classification_eval.py [--leafsense-already-running]

Calls the LeafSense API to evaluate its actual image classification
accuracy against a sampled validation set.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from eval.module10 import config

VALIDATION_SET_PATH = Path(r"D:\AI-ML-FullStack\02-Projects\Portfolio-Projects\LeafSense\data\split_dataset\valid")
LEAFSENSE_SERVER_CWD = Path(r"D:\AI-ML-FullStack\02-Projects\Portfolio-Projects\LeafSense\backend")
LEAFSENSE_ENDPOINT = "http://127.0.0.1:8001/predict/hybrid"


def derive_per_class_binary_counts(cm_array, classes: list[str]) -> dict[str, dict[str, int]]:
    """Derive TP, FP, TN, FN per class from an sklearn confusion matrix."""
    counts = {}
    total = sum(sum(row) for row in cm_array)
    for i, cls in enumerate(classes):
        tp = cm_array[i][i]
        row_sum = sum(cm_array[i])
        col_sum = sum(cm_array[r][i] for r in range(len(classes)))
        fp = col_sum - tp
        fn = row_sum - tp
        tn = total - tp - fp - fn
        counts[cls] = {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)}
    return counts


def compute_metrics(y_true: list[str], y_pred: list[str], classes: list[str]) -> dict:
    """Compute all required metrics from true and predicted labels."""
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    cr = classification_report(y_true, y_pred, labels=classes, output_dict=True, zero_division=0)

    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    binary_counts = derive_per_class_binary_counts(cm, classes)

    per_class_report = {}
    for cls in classes:
        cls_cr = cr.get(cls, {})
        cls_bin = binary_counts.get(cls, {})
        per_class_report[cls] = {
            "precision": cls_cr.get("precision", 0.0),
            "recall": cls_cr.get("recall", 0.0),
            "f1": cls_cr.get("f1-score", 0.0),
            "support": cls_cr.get("support", 0),
            **cls_bin
        }

    return {
        "overall": {
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "n_samples": len(y_true),
        },
        "per_class_report": per_class_report,
        "confusion_matrix": cm.tolist(),
    }


def _get_validation_sample(sample_per_class: int = 5) -> list[tuple[str, str]]:
    """Return a list of (image_path, true_label) by sampling deterministically."""
    if not VALIDATION_SET_PATH.exists():
        raise FileNotFoundError(f"Validation set not found at {VALIDATION_SET_PATH}")

    classes = sorted(os.listdir(VALIDATION_SET_PATH))
    samples = []

    for cls in classes:
        cls_path = VALIDATION_SET_PATH / cls
        if not cls_path.is_dir():
            continue

        # Deterministic sort
        images = sorted(os.listdir(cls_path))
        for img in images[:sample_per_class]:
            samples.append((str(cls_path / img), cls))

    return samples, classes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leafsense-already-running", action="store_true")
    args = parser.parse_args()

    server_proc = None
    if not args.leafsense_already_running:
        print("Starting LeafSense server...")
        try:
            # Note: We must use LeafSense's python if possible, but sys.executable is the runner's python.
            # Assuming LeafSense is compatible or has its own venv.
            leafsense_python = LEAFSENSE_SERVER_CWD / ".venv" / "Scripts" / "python.exe"
            if not leafsense_python.exists():
                leafsense_python = sys.executable  # fallback

            server_proc = subprocess.Popen(
                [str(leafsense_python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
                cwd=str(LEAFSENSE_SERVER_CWD),
            )
            print(f"Waiting for LeafSense to start (PID {server_proc.pid})...")
            # Wait for it to accept connections
            for _ in range(15):
                try:
                    httpx.get("http://127.0.0.1:8001/docs")
                    break
                except httpx.RequestError:
                    time.sleep(1.0)
            else:
                print("Failed to start LeafSense server (timeout).")
                server_proc.terminate()
                sys.exit(1)
        except Exception as e:
            print(f"Error starting LeafSense: {e}")
            sys.exit(1)

    try:
        samples, classes = _get_validation_sample(5)
        print(f"Evaluating {len(samples)} images across {len(classes)} classes...")

        y_true = []
        y_pred = []
        per_case = []

        with httpx.Client(timeout=30.0) as client:
            for img_path, true_label in samples:
                try:
                    with open(img_path, "rb") as f:
                        files = {"file": (os.path.basename(img_path), f, "image/jpeg")}
                        resp = client.post(LEAFSENSE_ENDPOINT, files=files)
                        resp.raise_for_status()

                        result = resp.json()
                        pred_label = result.get("class", "Unknown")
                        confidence = result.get("confidence", 0.0)

                        y_true.append(true_label)
                        y_pred.append(pred_label)
                        per_case.append({
                            "image_path": img_path,
                            "true_label": true_label,
                            "predicted_label": pred_label,
                            "correct": true_label == pred_label,
                            "confidence": confidence,
                        })
                except Exception as e:
                    print(f"Error classifying {img_path}: {e}")
                    # Count errors as incorrect/unknown to avoid cherrypicking
                    y_true.append(true_label)
                    y_pred.append("Error")
                    per_case.append({
                        "image_path": img_path,
                        "true_label": true_label,
                        "predicted_label": "Error",
                        "correct": False,
                        "confidence": 0.0,
                    })

        # Compute metrics
        metrics = compute_metrics(y_true, y_pred, classes)

        report = {
            "metadata": {
                **config.run_metadata(
                    sample_count=len(samples),
                    dataset_version="leafsense_valid_v1"
                ),
                "source": "LeafSense/data/split_dataset/valid/",
                "test_set_source": "LeafSense real validation split (PlantVillage-derived, used during model training)",
                "test_set_size": len(samples),
                "classes_evaluated": len(classes),
                "sample_per_class": 5,
                "model_id": "hybrid",
                "leafsense_endpoint": "POST http://127.0.0.1:8001/predict/{model_id}",
                "disclosure": "Sample of 5 images per class (190 total) from the real LeafSense validation split. Full validation split has 10529 images. Numbers reported honestly regardless of quality."
            },
            "overall": metrics["overall"],
            "per_class_report": metrics["per_class_report"],
            "confusion_matrix": metrics["confusion_matrix"],
            "class_labels": classes,
            "per_case": per_case
        }

        path = config.save_report(report, name="vision_classification")
        print(f"Saved: {path}")
        print(f"Accuracy: {metrics['overall']['accuracy']:.2%} | Macro F1: {metrics['overall']['macro_f1']:.4f}")

    finally:
        if server_proc is not None:
            print("Stopping LeafSense server...")
            server_proc.terminate()
            server_proc.wait()


if __name__ == "__main__":
    main()
