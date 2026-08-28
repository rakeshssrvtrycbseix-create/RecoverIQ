import csv
import io
import random
from typing import Any

from app.ml.model import LogisticRegressionModel
from app.ml.schemas import EvaluationMetrics, RecoveryFeatures


def calculate_roc_auc(y_true: list[int], y_scores: list[float]) -> float:
    """
    Calculate ROC-AUC using the Wilcoxon-Mann-Whitney rank sum formulation.
    """
    n = len(y_true)
    if n == 0:
        return 0.5

    positives = [
        score for y, score in zip(y_true, y_scores, strict=False) if y == 1
    ]
    negatives = [
        score for y, score in zip(y_true, y_scores, strict=False) if y == 0
    ]

    n_pos = len(positives)
    n_neg = len(negatives)

    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Count how many positive pairs score higher than negative pairs
    pairs_won = 0.0
    for pos_score in positives:
        for neg_score in negatives:
            if pos_score > neg_score:
                pairs_won += 1.0
            elif pos_score == neg_score:
                pairs_won += 0.5

    return round(pairs_won / (n_pos * n_neg), 4)


def calculate_pr_auc(y_true: list[int], y_scores: list[float]) -> float:
    """
    Calculate PR-AUC (Area Under Precision-Recall Curve) via trapezoidal integration.
    """
    if not y_true or sum(y_true) == 0:
        return 0.0

    thresholds = sorted(set(y_scores), reverse=True)
    precisions = [1.0]
    recalls = [0.0]

    for th in thresholds:
        y_pred = [1 if s >= th else 0 for s in y_scores]
        tp = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=False)
            if yt == 1 and yp == 1
        )
        fp = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=False)
            if yt == 0 and yp == 1
        )
        fn = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=False)
            if yt == 1 and yp == 0
        )

        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precisions.append(prec)
        recalls.append(rec)

    # Trapezoidal approximation
    pr_auc = 0.0
    for i in range(1, len(recalls)):
        delta_recall = recalls[i] - recalls[i - 1]
        avg_precision = (precisions[i] + precisions[i - 1]) / 2.0
        pr_auc += delta_recall * avg_precision

    return max(0.0, min(1.0, round(abs(pr_auc), 4)))


def evaluate_model(
    y_true: list[int],
    y_scores: list[float],
    threshold: float = 0.5,
) -> EvaluationMetrics:
    """
    Compute comprehensive classification metrics for model validation.
    """
    n = len(y_true)
    if n == 0:
        raise ValueError("Cannot evaluate empty dataset")

    tp = 0
    fp = 0
    tn = 0
    fn = 0
    brier_sum = 0.0

    for yt, prob in zip(y_true, y_scores, strict=False):
        yp = 1 if prob >= threshold else 0
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 0 and yp == 1:
            fp += 1
        elif yt == 0 and yp == 0:
            tn += 1
        elif yt == 1 and yp == 0:
            fn += 1

        brier_sum += (prob - yt) ** 2

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    brier_score = brier_sum / n
    roc_auc = calculate_roc_auc(y_true, y_scores)
    pr_auc = calculate_pr_auc(y_true, y_scores)

    return EvaluationMetrics(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1_score, 4),
        roc_auc=round(roc_auc, 4),
        pr_auc=round(pr_auc, 4),
        brier_score=round(brier_score, 4),
        confusion_matrix={"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        sample_size=n,
    )


def generate_synthetic_development_dataset(
    n_samples: int = 500,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """
    Generate synthetic development dataset for local testing and calibration.

    NOTE: Metrics generated on this synthetic dataset reflect development
    behavior and do NOT represent production empirical performance.
    """
    rng = random.Random(seed)
    dataset = []

    error_reasons = [
        ("insufficient_funds", 0.70),
        ("network_timeout", 0.85),
        ("bank_technical_error", 0.80),
        ("payment_authentication", 0.55),
        ("card_inactive", 0.10),
        ("expired_card", 0.15),
        ("card_blocked", 0.05),
    ]

    for _ in range(n_samples):
        reason, base_recovery_prob = rng.choice(error_reasons)
        amount = rng.randint(50000, 500000)  # ₹500 to ₹5000
        attempt = rng.randint(1, 4)
        customer_total = rng.randint(0, 15)
        success_rate = rng.uniform(0.3, 1.0) if customer_total > 0 else 0.50
        failed_count = int(customer_total * (1.0 - success_rate))
        success_count = customer_total - failed_count
        hours = rng.uniform(0.5, 48.0)

        # Ground truth label generator based on latent probability
        adjusted_prob = base_recovery_prob + (success_rate * 0.2) - (attempt * 0.1)
        clamped_prob = max(0.02, min(0.98, adjusted_prob))
        label = 1 if rng.random() < clamped_prob else 0

        features = RecoveryFeatures(
            payment_amount=amount,
            currency="INR",
            attempt_number=attempt,
            customer_total_payments=customer_total,
            customer_successful_payments=success_count,
            customer_failed_payments=failed_count,
            customer_success_rate=round(success_rate, 4),
            error_code="BAD_REQUEST_ERROR" if "card" in reason else "GATEWAY_ERROR",
            error_source="bank",
            error_step="payment_authorization",
            error_reason=reason,
            hours_since_failure=round(hours, 2),
            subscription_age_days=rng.randint(0, 180),
            total_attempts_count=attempt,
        )

        dataset.append({"features": features, "label": label})

    return dataset


def load_dataset_from_csv(csv_content: str) -> list[dict[str, Any]]:
    """
    Parse development training data from a CSV formatted string.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    dataset = []
    for row in reader:
        features = RecoveryFeatures(
            payment_amount=int(row["payment_amount"]),
            currency=row.get("currency", "INR"),
            attempt_number=int(row["attempt_number"]),
            customer_total_payments=int(row["customer_total_payments"]),
            customer_successful_payments=int(row["customer_successful_payments"]),
            customer_failed_payments=int(row["customer_failed_payments"]),
            customer_success_rate=float(row["customer_success_rate"]),
            error_code=row.get("error_code", "UNKNOWN"),
            error_source=row.get("error_source", "UNKNOWN"),
            error_step=row.get("error_step", "UNKNOWN"),
            error_reason=row.get("error_reason", "unknown"),
            hours_since_failure=float(row["hours_since_failure"]),
            subscription_age_days=int(row.get("subscription_age_days", 0)),
            total_attempts_count=int(row.get("total_attempts_count", 1)),
        )
        label = int(row["label"])
        dataset.append({"features": features, "label": label})
    return dataset


def train_development_model(
    dataset: list[dict[str, Any]],
    learning_rate: float = 0.05,
    epochs: int = 50,
) -> tuple[LogisticRegressionModel, EvaluationMetrics]:
    """
    Train a LogisticRegressionModel using gradient descent on development data.
    """
    model = LogisticRegressionModel()

    # Gradient descent update over calibration weights
    for _ in range(epochs):
        for item in dataset:
            feat = item["features"]
            y = item["label"]
            pred = model.predict_proba(feat)
            err = pred - y

            # Numerical gradient updates
            model.intercept -= learning_rate * err * 0.1
            model.coef_success_rate -= (
                learning_rate * err * (feat.customer_success_rate - 0.5)
            )
            model.coef_failed_payments -= (
                learning_rate * err * (min(10, feat.customer_failed_payments) / 10.0)
            )
            model.coef_attempt_number -= (
                learning_rate * err * (feat.attempt_number - 1.0)
            )

    # Evaluate trained model
    y_true = [item["label"] for item in dataset]
    y_pred = [model.predict_proba(item["features"]) for item in dataset]
    metrics = evaluate_model(y_true, y_pred)

    return model, metrics
