"""Tests for per_class_binary_counts — Task 3 (Module 10 gap-closure).

Derives TP/FP/TN/FN for each class from the existing confusion matrix using
the one-vs-rest (OvR) formula. Exercises the new
eval.module10.metrics.classification.per_class_binary_counts() function on
small synthetic fixtures — no live model or LLM calls needed.
"""

from __future__ import annotations

import pytest

from eval.module10.metrics.classification import per_class_binary_counts


class TestPerClassBinaryCountsKnownFixture:
    """Tests on a small known fixture where manual verification is feasible."""

    def _counts(self):
        # 5 samples: A,A,B,B,C
        # predicted: A,B,B,C,C
        # confusion matrix (actual \ predicted):
        #        A  B  C
        #   A  [ 1  1  0 ]   (true A predicted B is FN for A, FP for B)
        #   B  [ 0  2  0 ]
        #   C  [ 0  0  1 ]
        y_true = ["conversational", "conversational", "retrieve", "retrieve", "summarize"]
        y_pred = ["conversational", "retrieve",       "retrieve", "summarize","summarize"]
        return per_class_binary_counts(y_true, y_pred)

    def test_class_a_tp(self):
        counts = self._counts()
        # conversational: TP=1 (predicted conversational and truly conversational)
        assert counts["conversational"]["tp"] == 1

    def test_class_a_fn(self):
        counts = self._counts()
        # conversational: FN=1 (truly conversational predicted as retrieve)
        assert counts["conversational"]["fn"] == 1

    def test_class_a_fp(self):
        counts = self._counts()
        # conversational: FP=0 (nothing else was predicted as conversational)
        assert counts["conversational"]["fp"] == 0

    def test_class_a_tn(self):
        counts = self._counts()
        # conversational: TN = 5 - TP(1) - FP(0) - FN(1) = 3
        assert counts["conversational"]["tn"] == 3

    def test_class_b_retrieve_tp(self):
        counts = self._counts()
        # retrieve: TP=1 (one true retrieve predicted correctly)
        assert counts["retrieve"]["tp"] == 1

    def test_class_b_retrieve_fp(self):
        counts = self._counts()
        # retrieve: FP=1 (true conversational predicted as retrieve)
        assert counts["retrieve"]["fp"] == 1

    def test_class_b_retrieve_fn(self):
        counts = self._counts()
        # retrieve: FN=1 (true retrieve predicted as summarize)
        assert counts["retrieve"]["fn"] == 1

    def test_class_c_summarize_tp(self):
        counts = self._counts()
        # summarize: TP=1 (the one true summarize predicted correctly)
        assert counts["summarize"]["tp"] == 1

    def test_class_c_summarize_fp(self):
        counts = self._counts()
        # summarize: FP=1 (true retrieve predicted as summarize)
        assert counts["summarize"]["fp"] == 1

    def test_class_c_summarize_fn(self):
        counts = self._counts()
        # summarize: FN=0 (no true summarize predicted as something else)
        assert counts["summarize"]["fn"] == 0


class TestPerClassBinaryCountsPerfectPrediction:
    """All correct — TP = support, FP = FN = 0, TN = total - support."""

    def _counts(self):
        y_true = ["conversational", "retrieve", "retrieve", "summarize", "conversational"]
        y_pred = ["conversational", "retrieve", "retrieve", "summarize", "conversational"]
        return per_class_binary_counts(y_true, y_pred)

    def test_no_false_positives(self):
        counts = self._counts()
        for cls in counts:
            assert counts[cls]["fp"] == 0, f"Expected 0 FP for {cls}, got {counts[cls]['fp']}"

    def test_no_false_negatives(self):
        counts = self._counts()
        for cls in counts:
            assert counts[cls]["fn"] == 0, f"Expected 0 FN for {cls}, got {counts[cls]['fn']}"

    def test_tp_equals_support(self):
        counts = self._counts()
        # conversational: 2 samples → TP=2
        assert counts["conversational"]["tp"] == 2
        # retrieve: 2 samples → TP=2
        assert counts["retrieve"]["tp"] == 2
        # summarize: 1 sample → TP=1
        assert counts["summarize"]["tp"] == 1

    def test_tn_equals_total_minus_support(self):
        counts = self._counts()
        total = 5
        # conversational: TN = 5 - 2(TP) - 0(FP) - 0(FN) = 3
        assert counts["conversational"]["tn"] == total - 2

    def test_counts_sum_to_total(self):
        counts = self._counts()
        total = 5
        for cls, c in counts.items():
            assert c["tp"] + c["fp"] + c["fn"] + c["tn"] == total, (
                f"TP+FP+FN+TN != total for class {cls}"
            )


class TestPerClassBinaryCountsAllWrong:
    """All predictions wrong — TP = 0 for all classes."""

    def _counts(self):
        # 6 samples, 2 of each class, all mis-predicted cyclically
        y_true = ["conversational", "conversational", "retrieve", "retrieve", "summarize", "summarize"]
        y_pred = ["retrieve",       "summarize",      "summarize","conversational","conversational","retrieve"]
        return per_class_binary_counts(y_true, y_pred)

    def test_no_true_positives(self):
        counts = self._counts()
        for cls in counts:
            assert counts[cls]["tp"] == 0, f"Expected 0 TP for {cls}, got {counts[cls]['tp']}"

    def test_counts_sum_to_total(self):
        counts = self._counts()
        total = 6
        for cls, c in counts.items():
            assert c["tp"] + c["fp"] + c["fn"] + c["tn"] == total, (
                f"TP+FP+FN+TN != {total} for class {cls}"
            )


class TestPerClassBinaryCountsReturnStructure:
    def test_all_four_action_classes_present(self):
        """All four planner action classes must be present in the output,
        even if one has zero samples in the batch."""
        from eval.module10.metrics.classification import ACTIONS
        y_true = ["conversational", "retrieve"]
        y_pred = ["conversational", "retrieve"]
        counts = per_class_binary_counts(y_true, y_pred)
        for action in ACTIONS:
            assert action in counts, f"Class {action!r} missing from output"

    def test_each_class_has_four_keys(self):
        y_true = ["retrieve"]
        y_pred = ["retrieve"]
        counts = per_class_binary_counts(y_true, y_pred)
        for cls, c in counts.items():
            assert set(c.keys()) == {"tp", "fp", "fn", "tn"}, (
                f"Unexpected keys for class {cls}: {set(c.keys())}"
            )
