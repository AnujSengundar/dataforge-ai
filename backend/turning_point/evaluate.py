"""Run a small live Ollama evaluation and emit JSON suitable for comparing runs."""

import json

from backend.turning_point.cases import CASES
from backend.turning_point.investigator import investigate


def main() -> int:
    cricket = CASES["eden-gardens-2016"]
    monaco = CASES["monaco-2021"]
    adaptation = CASES["liore-reveal"]
    scenarios = [
        ("final-over", cricket, cricket.claim, "supported"),
        (
            "faster-stop",
            monaco,
            "Vettel's pit-lane transit was faster than Hamilton's.",
            "contradicted",
        ),
        ("missing-gap", monaco, "What was the exact gap to Gasly on rejoin?", "insufficient"),
        ("private-intent", monaco, "Did Vettel secretly plan to stop on lap 31?", "insufficient"),
        ("audience-effect", adaptation, adaptation.claim, "insufficient"),
    ]
    report = []
    for name, case, claim, expected in scenarios:
        initial = investigate(case, claim, 1)
        review = investigate(case, claim, 1, initial)
        visible = {event.id for event in case.visible(1)}
        valid = all(
            set(fact.refs).issubset(visible)
            for result in (initial, review)
            for fact in result.supporting + result.conflicting
        )
        passed = (
            valid
            and initial.model != "evidence-only"
            and review.model != "evidence-only"
            and review.verdict == expected
        )
        report.append(
            {
                "scenario": name,
                "expected_review": expected,
                "passed": passed,
                "source_version": case.version,
                "citations_in_scope": valid,
                "initial": initial.model_dump(),
                "review": review.model_dump(),
            }
        )
    print(json.dumps(report, indent=2))
    return 0 if all(item["passed"] for item in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
