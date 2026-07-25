from dataclasses import dataclass


@dataclass(frozen=True)
class QualityScore:
    score: float
    components: dict[str, float]


def calculate_quality_score(
    *,
    total_rows: int,
    valid_rows: int,
    passed_blocking_rules: int,
    total_blocking_rules: int,
    row_weight: float = 0.70,
    rule_weight: float = 0.30,
) -> QualityScore:
    if row_weight < 0 or rule_weight < 0 or abs(row_weight + rule_weight - 1.0) > 1e-9:
        raise ValueError("Quality-score weights must be non-negative and sum to 1.0.")
    row_score = valid_rows / total_rows * 100 if total_rows else 0.0
    rule_score = (
        passed_blocking_rules / total_blocking_rules * 100
        if total_blocking_rules
        else 100.0
    )
    score = 0.0 if total_rows == 0 else row_weight * row_score + rule_weight * rule_score
    return QualityScore(
        round(score, 2),
        {
            "row_validity_score": round(row_score, 2),
            "rule_pass_score": round(rule_score, 2),
            "row_weight": row_weight,
            "rule_weight": rule_weight,
        },
    )
