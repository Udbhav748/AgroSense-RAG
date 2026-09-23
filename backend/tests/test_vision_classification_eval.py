"""Tests for vision classification evaluation — Task 1 (Module 10 gap-closure)."""

from __future__ import annotations

import pytest
from eval.module10.runners.run_vision_classification_eval import (
    derive_per_class_binary_counts,
    compute_metrics,
)


def test_derive_per_class_binary_counts():
    classes = ["A", "B", "C"]
    # true: A, A, B, B, C
    # pred: A, B, B, C, C
    cm_array = [
        [1, 1, 0], # A
        [0, 1, 1], # B
        [0, 0, 1], # C
    ]
    
    counts = derive_per_class_binary_counts(cm_array, classes)
    
    # Class A: TP=1, FP=0, FN=1, TN=5-1-0-1=3
    assert counts["A"]["tp"] == 1
    assert counts["A"]["fp"] == 0
    assert counts["A"]["fn"] == 1
    assert counts["A"]["tn"] == 3
    
    # Class B: TP=1, FP=1, FN=1, TN=5-1-1-1=2
    assert counts["B"]["tp"] == 1
    assert counts["B"]["fp"] == 1
    assert counts["B"]["fn"] == 1
    assert counts["B"]["tn"] == 2
    
    # Class C: TP=1, FP=1, FN=0, TN=5-1-1-0=3
    assert counts["C"]["tp"] == 1
    assert counts["C"]["fp"] == 1
    assert counts["C"]["fn"] == 0
    assert counts["C"]["tn"] == 3


def test_compute_metrics():
    classes = ["A", "B", "C"]
    y_true = ["A", "A", "B", "B", "C"]
    y_pred = ["A", "B", "B", "C", "C"]
    
    metrics = compute_metrics(y_true, y_pred, classes)
    
    assert "overall" in metrics
    assert metrics["overall"]["n_samples"] == 5
    assert metrics["overall"]["accuracy"] == 0.6  # 3/5 correct
    
    assert "per_class_report" in metrics
    assert "A" in metrics["per_class_report"]
    assert "B" in metrics["per_class_report"]
    
    assert metrics["per_class_report"]["A"]["tp"] == 1
    assert metrics["per_class_report"]["B"]["fp"] == 1
    
    assert "confusion_matrix" in metrics
    assert len(metrics["confusion_matrix"]) == 3
