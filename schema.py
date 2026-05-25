"""
JSON schema enforcement and result normalization.
"""
from config import PARAMETERS


def coerce_int_score(value):
    try:
        value = int(value)
    except Exception:
        return 0
    return max(0, min(4, value))


def normalize_parameter_list(value):
    if isinstance(value, list):
        items = value
    elif isinstance(value, str) and value.strip():
        items = [value.strip()]
    else:
        items = []
    cleaned = []
    for item in items:
        item = str(item).strip().lower()
        if item in PARAMETERS and item not in cleaned:
            cleaned.append(item)
    return cleaned


def make_overview_fallback():
    return {
        "summary": "Failed to automatically parse the structured model response. Check model configuration, JSON schema, or repeat the request.",
        "overall_score": 0,
        "scale_max": 4,
        "parameters": {p: {"score": 0, "comment": "Analysis not performed."} for p in PARAMETERS}
    }


def make_detailed_fallback():
    return {
        "summary": "Failed to automatically parse the structured model response. Check model configuration, JSON schema, or repeat the request.",
        "overall_score": 0,
        "scale_max": 4,
        "coverage": {"text_processed_whole": False, "relevant_passages_count": 0, "uncertain_count": 0},
        "cases": [],
        "category_results": {p: {"score": 0, "observations": []} for p in PARAMETERS},
        "uncertain_items": [],
        "ambiguous_cases": [],
        "unresolved_passages": [],
        "notes_on_missing_categories": []
    }


def enforce_schema(result, analysis_mode):
    if not isinstance(result, dict):
        return make_overview_fallback() if analysis_mode == "overview" else make_detailed_fallback()

    if analysis_mode == "overview":
        normalized = make_overview_fallback()
        normalized["summary"] = str(result.get("summary") or normalized["summary"]).strip()
        normalized["overall_score"] = coerce_int_score(result.get("overall_score", 0))
        params = result.get("parameters") or {}
        for p in PARAMETERS:
            src = params.get(p) if isinstance(params, dict) else {}
            if not isinstance(src, dict):
                src = {}
            normalized["parameters"][p] = {
                "score": coerce_int_score(src.get("score", 0)),
                "comment": str(src.get("comment") or "").strip()
            }
        return normalized

    normalized = make_detailed_fallback()
    normalized["summary"] = str(result.get("summary") or normalized["summary"]).strip()
    normalized["overall_score"] = coerce_int_score(result.get("overall_score", 0))
    coverage = result.get("coverage") if isinstance(result.get("coverage"), dict) else {}
    normalized["coverage"] = {
        "text_processed_whole": bool(coverage.get("text_processed_whole", False)),
        "relevant_passages_count": int(coverage.get("relevant_passages_count", 0) or 0),
        "uncertain_count": int(coverage.get("uncertain_count", 0) or 0)
    }

    cases = result.get("cases") if isinstance(result.get("cases"), list) else []
    cleaned_cases = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        cleaned_case = {
            "source_fragment": str(case.get("source_fragment") or "").strip(),
            "target_fragment": str(case.get("target_fragment") or "").strip(),
            "observation": str(case.get("observation") or "").strip(),
            "parameter": normalize_parameter_list(case.get("parameter")),
            "intervention_degree": coerce_int_score(case.get("intervention_degree", 0)),
            "evidence": str(case.get("evidence") or "").strip(),
            "confidence": str(case.get("confidence") or "low").strip().lower()
        }
        if cleaned_case["confidence"] not in {"high", "medium", "low"}:
            cleaned_case["confidence"] = "low"
        if cleaned_case["source_fragment"] or cleaned_case["target_fragment"] or cleaned_case["observation"]:
            cleaned_cases.append(cleaned_case)
    normalized["cases"] = cleaned_cases

    category_results = result.get("category_results") if isinstance(result.get("category_results"), dict) else {}
    for p in PARAMETERS:
        src = category_results.get(p) if isinstance(category_results, dict) else {}
        if not isinstance(src, dict):
            src = {}
        observations = src.get("observations") if isinstance(src.get("observations"), list) else []
        normalized["category_results"][p] = {
            "score": coerce_int_score(src.get("score", 0)),
            "observations": [str(x).strip() for x in observations if str(x).strip()]
        }

    for key in ["uncertain_items", "ambiguous_cases", "unresolved_passages", "notes_on_missing_categories"]:
        val = result.get(key)
        normalized[key] = val if isinstance(val, list) else []

    normalized["coverage"]["relevant_passages_count"] = len(normalized["cases"])
    normalized["coverage"]["uncertain_count"] = sum(1 for c in normalized["cases"] if c["confidence"] != "high")
    if normalized["cases"]:
        normalized["coverage"]["text_processed_whole"] = bool(coverage.get("text_processed_whole", True))
    return normalized
