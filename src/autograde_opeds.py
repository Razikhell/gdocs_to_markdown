from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


DEFAULT_MIN_WORDS_FOR_AVERAGE = 150


AI_TERMS = {
    "ai",
    "artificial intelligence",
    "algorithm",
    "machine learning",
    "chatgpt",
    "copilot",
    "model",
    "neural",
    "recommendation",
}

TOOL_TERMS = {
    "app",
    "tool",
    "platform",
    "software",
    "website",
    "system",
    "assistant",
    "chatbot",
}

HOW_IT_WORKS_TERMS = {
    "works by",
    "uses data",
    "trained",
    "analyzes",
    "predicts",
    "recommends",
    "based on",
    "processes",
    "learns from",
}

METAPHOR_EXAMPLE_TERMS = {
    "for example",
    "for instance",
    "imagine",
    "it is like",
    "it's like",
    "as if",
    "similar to",
    "metaphor",
}

FUTURE_MARKERS = {
    "will",
    "may",
    "might",
    "could",
    "going to",
    "in the future",
    "in 10 years",
    "in 20 years",
}

IMPACT_TERMS = {
    "society",
    "people",
    "students",
    "schools",
    "community",
    "communities",
    "jobs",
    "economy",
    "culture",
    "privacy",
    "bias",
    "harm",
    "benefit",
    "health",
    "education",
}

EVIDENCE_MARKERS = {
    "according to",
    "research",
    "study",
    "report",
    "data",
    "survey",
    "statistic",
    "evidence",
    "%",
}

RECOMMENDATION_MARKERS = {
    "should",
    "must",
    "need to",
    "recommend",
    "i recommend",
    "i propose",
    "ought to",
    "regulate",
    "require",
    "ban",
    "limit",
}

HARM_REDUCTION_MARKERS = {
    "reduce harm",
    "safer",
    "safety",
    "protect",
    "privacy",
    "fair",
    "fairness",
    "bias",
    "prevent",
    "ethical",
    "harm",
}

COLLECTIVE_ACTION_MARKERS = {
    "we can",
    "let's",
    "students",
    "class",
    "teachers",
    "school",
    "district",
    "community",
    "policymakers",
    "government",
    "parents",
    "together",
    "share",
    "sign",
    "vote",
}

AMPLIFIES_HARM_MARKERS = {
    "no rules",
    "without limits",
    "ignore privacy",
    "monitor everyone",
    "replace all teachers",
    "ban human",
}

COUNTERARGUMENT_MARKERS = {
    "to be sure",
    "on the other hand",
    "however",
    "some would argue",
    "it is important to acknowledge",
    "although",
}

CALL_TO_ACTION_MARKERS = {
    "we should",
    "let's",
    "i urge",
    "take action",
    "join",
    "share",
    "start",
    "act now",
    "do it ourselves",
}


@dataclass
class CriterionScore:
    level: int
    reason: str


@dataclass
class AutogradeResult:
    file_path: str
    student_name: str
    word_count: int
    description: CriterionScore
    predictions: CriterionScore
    recommendations: CriterionScore
    prose_style: CriterionScore
    included_in_average: bool = True
    summary: str = ""

    @property
    def total_score(self) -> int:
        return (
            self.description.level
            + self.predictions.level
            + self.recommendations.level
            + self.prose_style.level
        )


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_rubric_csv(path: Path) -> Dict[str, Dict[int, str]]:
    rubric: Dict[str, Dict[int, str]] = {}
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            criterion_name = (row.get("") or "").strip()
            if not criterion_name:
                continue
            rubric[criterion_name] = {
                1: (row.get("Level 1") or "").strip(),
                2: (row.get("Level 2") or "").strip(),
                3: (row.get("Level 3") or "").strip(),
                4: (row.get("Level 4") or "").strip(),
            }
    return rubric


def strip_frontmatter(text: str) -> str:
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return text

    lines = stripped.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return text


def normalize_text(text: str) -> str:
    text = strip_frontmatter(text)
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\\!", "!", text)
    text = re.sub(r"\\-", "-", text)
    text = re.sub(r"\*{1,3}", "", text)
    return text.strip()


def split_paragraphs(text: str) -> List[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    return chunks


def split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def count_word_tokens(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def guess_student_name(file_path: Path) -> str:
    stem = file_path.stem
    if " - " in stem:
        return stem.split(" - ", 1)[0].strip()
    return stem


def score_description(text: str) -> CriterionScore:
    lowered = text.lower()
    has_ai = contains_any(lowered, AI_TERMS)
    has_tool = contains_any(lowered, TOOL_TERMS)
    has_non_ai_tool = has_tool and not has_ai
    has_how = contains_any(lowered, HOW_IT_WORKS_TERMS)
    has_metaphor_or_example = contains_any(lowered, METAPHOR_EXAMPLE_TERMS)

    if has_non_ai_tool and not has_ai:
        return CriterionScore(1, "Names a tool/app but does not clearly frame it as AI.")

    if not has_ai:
        return CriterionScore(1, "Does not clearly name an AI tool.")

    if has_ai and not has_how:
        return CriterionScore(2, "Names an AI tool but limited explanation of how it works.")

    if has_ai and has_how and not has_metaphor_or_example:
        return CriterionScore(3, "Explains how the AI tool works, but metaphor/example support is limited.")

    return CriterionScore(4, "Clearly names an AI tool, explains how it works, and includes helpful example/metaphor language.")


def is_prediction_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    has_future = any(marker in lowered for marker in FUTURE_MARKERS)
    has_impact = any(term in lowered for term in IMPACT_TERMS)
    if has_future and has_impact:
        return True
    # More forgiving: allow broad consequence statements even without an explicit society keyword.
    broad_impact_markers = {
        "impact",
        "affect",
        "change",
        "lead to",
        "result in",
        "cause",
        "future",
    }
    return has_future and any(marker in lowered for marker in broad_impact_markers)


def has_evidence(sentence: str) -> bool:
    lowered = sentence.lower()
    if any(marker in lowered for marker in EVIDENCE_MARKERS):
        return True
    if re.search(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", sentence):
        return True
    return False


def score_predictions(text: str) -> CriterionScore:
    sentences = split_sentences(text)
    prediction_sentences = [sentence for sentence in sentences if is_prediction_sentence(sentence)]
    prediction_count = len(prediction_sentences)
    evidence_count = sum(1 for sentence in prediction_sentences if has_evidence(sentence))

    # Also count explicit prediction framing as additional support.
    lowered_text = text.lower()
    explicit_prediction_count = len(
        re.findall(r"\b(predict|prediction|i think|i believe|in the future|will likely|is likely to)\b", lowered_text)
    )
    combined_prediction_count = max(prediction_count, explicit_prediction_count)

    if combined_prediction_count >= 3 and evidence_count >= 2:
        return CriterionScore(4, "Includes at least three societal-impact predictions supported with evidence markers.")
    if combined_prediction_count >= 3:
        return CriterionScore(3, "Includes three or more predictions, but evidence support is inconsistent.")
    if combined_prediction_count >= 2:
        return CriterionScore(2, "Includes two societal-impact predictions.")
    if combined_prediction_count >= 1:
        return CriterionScore(1, "Includes one societal-impact prediction.")
    return CriterionScore(1, "Prediction language is minimal or unclear.")


def score_recommendations(text: str) -> CriterionScore:
    sentences = split_sentences(text)
    recommendation_sentences = [
        sentence for sentence in sentences if contains_any(sentence.lower(), RECOMMENDATION_MARKERS)
    ]

    if not recommendation_sentences:
        return CriterionScore(1, "No clear recommendation detected.")

    joined_recommendations = " ".join(recommendation_sentences).lower()
    amplifies_harm = contains_any(joined_recommendations, AMPLIFIES_HARM_MARKERS)
    has_harm_reduction = contains_any(joined_recommendations, HARM_REDUCTION_MARKERS)
    has_collective_action = contains_any(joined_recommendations, COLLECTIVE_ACTION_MARKERS)

    if amplifies_harm:
        return CriterionScore(1, "Recommendation appears to increase harm or remove protections.")
    if has_harm_reduction and has_collective_action:
        return CriterionScore(4, "Recommends regulation to reduce harm and explains how others can help.")
    if has_harm_reduction:
        return CriterionScore(3, "Recommends regulation to reduce harm.")
    return CriterionScore(2, "Includes a recommendation, but harm-reduction pathway is unclear.")


def score_prose_style(text: str, example_word_count: int) -> CriterionScore:
    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text)

    if not paragraphs:
        return CriterionScore(1, "Document is empty or could not be parsed.")

    intro = paragraphs[0].lower()
    ending = paragraphs[-1].lower()

    has_hook = ("?" in paragraphs[0]) or bool(re.search(r"\b\d{2,}\b", paragraphs[0]))

    argument_window = " ".join(paragraphs[:2]).lower()
    has_argument = any(
        marker in argument_window
        for marker in ["i argue", "i believe", "i think", "should", "must", "need to", "my claim"]
    )
    if not has_argument:
        has_argument = any(
            marker in argument_window
            for marker in ["this shows", "this means", "this is why", "my opinion", "in my view"]
        )

    has_conclusion = any(
        marker in ending
        for marker in ["in conclusion", "to sum up", "overall", "ultimately", "therefore", "so what can we do"]
    ) or contains_any(ending, CALL_TO_ACTION_MARKERS)
    if not has_conclusion:
        has_conclusion = any(marker in ending for marker in ["in summary", "to conclude", "finally", "in the end"])

    has_to_be_sure = any(contains_any(paragraph.lower(), COUNTERARGUMENT_MARKERS) for paragraph in paragraphs)

    evidence_like_sentences = [
        sentence
        for sentence in sentences
        if has_evidence(sentence) or any(term in sentence.lower() for term in ["because", "for example", "for instance"])
    ]
    point_estimate = 0
    if len(paragraphs) >= 3:
        point_estimate = max(point_estimate, 1)
    if len(paragraphs) >= 5:
        point_estimate = max(point_estimate, 2)
    if len(paragraphs) >= 7:
        point_estimate = max(point_estimate, 3)
    point_estimate = max(point_estimate, min(5, len(evidence_like_sentences) // 2))

    has_call_to_action = contains_any(ending, CALL_TO_ACTION_MARKERS)

    # If writing is far shorter than the provided example, structural development is usually incomplete.
    if example_word_count > 0 and count_word_tokens(text) < int(example_word_count * 0.35):
        point_estimate = min(point_estimate, 2)

    if has_hook and has_argument and point_estimate >= 3 and has_to_be_sure and has_call_to_action:
        return CriterionScore(4, "Includes hook, argument, multiple evidence points, counterargument, and call to action.")
    if has_argument and point_estimate >= 2 and has_conclusion:
        return CriterionScore(3, "Includes clear argument, multiple points, and a conclusion.")
    if has_argument and point_estimate >= 2:
        return CriterionScore(3, "Includes clear argument with multiple points; conclusion signal is partial.")
    if (has_argument or has_conclusion) and point_estimate >= 1:
        return CriterionScore(2, "Includes argument, at least one point, and conclusion.")
    return CriterionScore(1, "Main argument and structural components are incomplete or weakly connected.")


def apply_forgiving_adjustments(result: AutogradeResult) -> None:
    """
    Apply a small, transparent adjustment to avoid harsh penalties on longer complete drafts.
    """
    if (
        result.word_count >= 700
        and result.prose_style.level == 1
        and result.description.level >= 3
        and result.recommendations.level >= 2
    ):
        result.prose_style = CriterionScore(
            2,
            "Forgiving adjustment: longer draft with clear argument signals; treated as argument + point + conclusion.",
        )

    if (
        result.word_count >= 1000
        and result.prose_style.level == 2
        and result.predictions.level >= 3
        and result.recommendations.level >= 3
    ):
        result.prose_style = CriterionScore(
            3,
            "Forgiving adjustment: sustained evidence/prediction/recommendation quality indicates multi-point structure.",
        )


def summarize_feedback(result: AutogradeResult, rubric: Dict[str, Dict[int, str]]) -> str:
    lines: List[str] = []

    criterion_map = [
        ("Description", result.description),
        ("Predictions", result.predictions),
        ("Recommendations", result.recommendations),
        ("Prose and Style", result.prose_style),
    ]

    for criterion_name, score in criterion_map:
        rubric_text = rubric.get(criterion_name, {}).get(score.level, "")
        if rubric_text:
            lines.append(f"{criterion_name} L{score.level}: {score.reason} Rubric: {rubric_text}")
        else:
            lines.append(f"{criterion_name} L{score.level}: {score.reason}")

    return " | ".join(lines)


def collect_student_files(docs_root: Path) -> List[Path]:
    files: List[Path] = []
    for file_path in docs_root.rglob("*.md"):
        if "rubric" in {part.lower() for part in file_path.parts}:
            continue
        files.append(file_path)
    return sorted(files)


def autograde_documents(
    docs_root: Path,
    rubric_csv: Path,
    guide_file: Path,
    example_file: Path,
    min_words_for_average: int,
) -> List[AutogradeResult]:
    _ = load_text(guide_file)
    example_text = normalize_text(load_text(example_file))
    example_word_count = count_word_tokens(example_text)

    rubric = parse_rubric_csv(rubric_csv)
    files = collect_student_files(docs_root)

    results: List[AutogradeResult] = []
    for file_path in files:
        raw_text = load_text(file_path)
        text = normalize_text(raw_text)
        result = AutogradeResult(
            file_path=str(file_path.relative_to(docs_root.parent)),
            student_name=guess_student_name(file_path),
            word_count=count_word_tokens(text),
            description=score_description(text),
            predictions=score_predictions(text),
            recommendations=score_recommendations(text),
            prose_style=score_prose_style(text, example_word_count=example_word_count),
            included_in_average=count_word_tokens(text) >= min_words_for_average,
        )
        apply_forgiving_adjustments(result)
        results.append(result)

    for result in results:
        summary = summarize_feedback(result, rubric)
        result.summary = summary

    return results


def write_outputs(results: List[AutogradeResult], output_csv: Path, output_json: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "file_path",
        "student_name",
        "word_count",
        "included_in_average",
        "description_level",
        "predictions_level",
        "recommendations_level",
        "prose_style_level",
        "total_score",
        "max_score",
        "percent",
        "feedback_summary",
    ]

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "file_path": result.file_path,
                    "student_name": result.student_name,
                    "word_count": result.word_count,
                    "included_in_average": result.included_in_average,
                    "description_level": result.description.level,
                    "predictions_level": result.predictions.level,
                    "recommendations_level": result.recommendations.level,
                    "prose_style_level": result.prose_style.level,
                    "total_score": result.total_score,
                    "max_score": 16,
                    "percent": round((result.total_score / 16) * 100, 1),
                    "feedback_summary": result.summary,
                }
            )

    json_payload = []
    for result in results:
        json_payload.append(
            {
                "file_path": result.file_path,
                "student_name": result.student_name,
                "word_count": result.word_count,
                "included_in_average": result.included_in_average,
                "scores": {
                    "Description": {
                        "level": result.description.level,
                        "reason": result.description.reason,
                    },
                    "Predictions": {
                        "level": result.predictions.level,
                        "reason": result.predictions.reason,
                    },
                    "Recommendations": {
                        "level": result.recommendations.level,
                        "reason": result.recommendations.reason,
                    },
                    "Prose and Style": {
                        "level": result.prose_style.level,
                        "reason": result.prose_style.reason,
                    },
                },
                "total_score": result.total_score,
                "max_score": 16,
                "percent": round((result.total_score / 16) * 100, 1),
                "feedback_summary": result.summary,
            }
        )

    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(json_payload, handle, indent=2)


def print_console_summary(results: List[AutogradeResult], output_csv: Path, output_json: Path) -> None:
    print(f"Autograded {len(results)} files")
    print(f"CSV report: {output_csv}")
    print(f"JSON report: {output_json}")

    if not results:
        return

    avg_score = sum(result.total_score for result in results) / len(results)
    avg_percent = (avg_score / 16) * 100
    print(f"Average score (all files): {avg_score:.2f} / 16 ({avg_percent:.1f}%)")

    included_results = [result for result in results if result.included_in_average]
    if included_results:
        included_avg_score = sum(result.total_score for result in included_results) / len(included_results)
        included_avg_percent = (included_avg_score / 16) * 100
        print(
            "Average score (submitted work only): "
            f"{included_avg_score:.2f} / 16 ({included_avg_percent:.1f}%) "
            f"from {len(included_results)} of {len(results)} files"
        )


def build_parser() -> argparse.ArgumentParser:
    src_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Autograde student op-ed markdown files based on rubric levels 1-4."
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=src_dir / "docs",
        help="Root folder containing student markdown files.",
    )
    parser.add_argument(
        "--rubric-csv",
        type=Path,
        default=src_dir / "docs" / "rubric" / "Op_Ed Rubric - Sheet1.csv",
        help="Rubric CSV path.",
    )
    parser.add_argument(
        "--guide-file",
        type=Path,
        default=src_dir / "docs" / "rubric" / "2026 How to Write an Op_Ed.md",
        help="Teacher guide/reference markdown path.",
    )
    parser.add_argument(
        "--example-file",
        type=Path,
        default=src_dir / "docs" / "rubric" / "2026 Example Op_Ed - Spotify's Discover Weekly.md",
        help="Example op-ed markdown path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=src_dir / "docs" / "autograde_results.csv",
        help="Path for CSV results.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=src_dir / "docs" / "autograde_results.json",
        help="Path for JSON results.",
    )
    parser.add_argument(
        "--min-words-for-average",
        type=int,
        default=DEFAULT_MIN_WORDS_FOR_AVERAGE,
        help="Exclude files shorter than this from the submitted-work class average.",
    )
    return parser


def validate_inputs(args: argparse.Namespace) -> None:
    required_paths = [
        args.docs_root,
        args.rubric_csv,
        args.guide_file,
        args.example_file,
    ]
    for required_path in required_paths:
        if not required_path.exists():
            raise FileNotFoundError(f"Required path not found: {required_path}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    validate_inputs(args)

    results = autograde_documents(
        docs_root=args.docs_root,
        rubric_csv=args.rubric_csv,
        guide_file=args.guide_file,
        example_file=args.example_file,
        min_words_for_average=args.min_words_for_average,
    )
    write_outputs(results, output_csv=args.output_csv, output_json=args.output_json)
    print_console_summary(results, args.output_csv, args.output_json)


if __name__ == "__main__":
    main()
