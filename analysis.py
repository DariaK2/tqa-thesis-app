"""
Core analysis logic: text chunking, LLM interaction, result merging.
"""
import json
import re
import logging
import concurrent.futures
from config import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS, VALID_PROMPT_VERSIONS, VALID_ANALYSIS_MODES, PARAMETERS
from llm_client import call_llm
from prompts import build_analysis_prompt, build_retry_prompt, SYSTEM_ROLE
from schema import enforce_schema, make_overview_fallback, make_detailed_fallback, coerce_int_score

logger = logging.getLogger(__name__)


def normalize_json_text(text):
    """Extract JSON from possibly markdown-wrapped text."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def safe_parse_json(text):
    """Safely parse JSON from potentially malformed text."""
    cleaned = normalize_json_text(text)
    return json.loads(cleaned)


def chunk_text(text, chunk_size=CHUNK_SIZE_CHARS, overlap=CHUNK_OVERLAP_CHARS):
    """Split text into overlapping chunks for processing."""
    text = (text or "").strip()
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            newline_pos = text.rfind("\n", start, end)
            sentence_pos = max(
                text.rfind(". ", start, end),
                text.rfind("! ", start, end),
                text.rfind("? ", start, end)
            )
            best_split = max(newline_pos, sentence_pos)
            if best_split > start + int(chunk_size * 0.6):
                end = best_split + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunk_pairs(source_text, target_text):
    """Create paired chunks from source and target texts."""
    source_chunks = chunk_text(source_text)
    target_chunks = chunk_text(target_text)
    count = max(len(source_chunks), len(target_chunks))
    if count == 1:
        return [(source_text, target_text)]
    
    pairs = []
    for i in range(count):
        s = source_chunks[min(i, len(source_chunks) - 1)] if source_chunks else ""
        t = target_chunks[min(i, len(target_chunks) - 1)] if target_chunks else ""
        pairs.append((s, t))
    return pairs


def needs_retry(result, analysis_mode):
    """Check if the result needs retry (empty cases with non-empty summary)."""
    if analysis_mode not in {"detail", "research"}:
        return False
    if not isinstance(result, dict):
        return True
    cases = result.get("cases")
    summary = str(result.get("summary") or "").strip()
    if not isinstance(cases, list):
        return True
    if len(cases) == 0 and summary:
        return True
    return False


def run_llm_analysis(prompt):
    """Run LLM analysis with the given prompt."""
    messages = [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user", "content": prompt}
    ]

    try:
        content = call_llm(
            messages,
            temperature=0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        logger.error(f"Primary LLM call failed: {e}")
        try:
            content = call_llm(messages, temperature=0, max_tokens=4000)
        except Exception as inner_e:
            logger.error(f"Fallback LLM call failed: {inner_e}")
            return json.dumps({
                "error": "model_call_failed",
                "message": str(inner_e)
            }, ensure_ascii=False)

    if not content:
        return json.dumps({
            "error": "empty_model_response",
            "message": "Model returned empty content."
        }, ensure_ascii=False)

    return content


def run_single_analysis(source_text, target_text, source_lang, target_lang, prompt_version, analysis_mode):
    """Run analysis for a single mode."""
    use_chunking = analysis_mode in {"detail", "research"}
    pairs = build_chunk_pairs(source_text, target_text) if use_chunking else [(source_text, target_text)]
    chunk_results = []

    for idx, (src_chunk, tgt_chunk) in enumerate(pairs, start=1):
        prompt = build_analysis_prompt(src_chunk, tgt_chunk, source_lang, target_lang, prompt_version, analysis_mode)
        if len(pairs) > 1:
            prompt += (
                f"\n\nThis is chunk {idx} of {len(pairs)}. "
                "Analyze only this fragment, but fully capture local differences within it."
            )

        raw_content = run_llm_analysis(prompt)
        logger.debug(f"LLM response preview: {raw_content[:500]}")

        try:
            parsed = safe_parse_json(raw_content)
            result = enforce_schema(parsed, analysis_mode)
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")
            logger.debug(f"Raw content: {raw_content[:1000]}")
            result = make_detailed_fallback() if analysis_mode != "overview" else make_overview_fallback()
            result["_parse_error"] = str(e)

        if needs_retry(result, analysis_mode):
            retry_prompt = build_retry_prompt(prompt)
            retry_raw = run_llm_analysis(retry_prompt)
            logger.debug(f"Retry response preview: {retry_raw[:500]}")
            try:
                retry_parsed = safe_parse_json(retry_raw)
                retry_result = enforce_schema(retry_parsed, analysis_mode)
                if not needs_retry(retry_result, analysis_mode):
                    result = retry_result
                    result["_retry_used"] = True
            except Exception as e:
                logger.warning(f"Retry JSON parse failed: {e}")

        chunk_results.append(result)

    return merge_chunk_results(chunk_results, analysis_mode, len(pairs))


def merge_chunk_results(results, analysis_mode, chunk_count):
    """Merge results from multiple chunks."""
    if analysis_mode == "overview":
        merged = make_overview_fallback()
        valid = [r for r in results if isinstance(r, dict)]
        if not valid:
            return merged
        
        merged["summary"] = "\n\n".join(
            [str(r.get("summary") or "").strip() for r in valid if str(r.get("summary") or "").strip()]
        ) or merged["summary"]
        
        merged["overall_score"] = round(
            sum(coerce_int_score(r.get("overall_score", 0)) for r in valid) / max(len(valid), 1)
        )
        
        for p in PARAMETERS:
            scores = [coerce_int_score((r.get("parameters") or {}).get(p, {}).get("score", 0)) for r in valid]
            comments = [str((r.get("parameters") or {}).get(p, {}).get("comment") or "").strip() for r in valid]
            merged["parameters"][p] = {
                "score": round(sum(scores) / max(len(scores), 1)),
                "comment": " ".join([c for c in comments if c])[:3000]
            }
        return merged

    merged = make_detailed_fallback()
    valid = [r for r in results if isinstance(r, dict)]
    if not valid:
        return merged
    
    merged["summary"] = "\n\n".join(
        [str(r.get("summary") or "").strip() for r in valid if str(r.get("summary") or "").strip()]
    ) or merged["summary"]
    
    merged["overall_score"] = round(
        sum(coerce_int_score(r.get("overall_score", 0)) for r in valid) / max(len(valid), 1)
    )

    all_cases = []
    for r in valid:
        all_cases.extend(r.get("cases") or [])

    dedup = []
    seen = set()
    for case in all_cases:
        key = (
            str(case.get("source_fragment") or "")[:200],
            str(case.get("target_fragment") or "")[:200],
            str(case.get("observation") or "")[:200]
        )
        if key not in seen:
            dedup.append(case)
            seen.add(key)
    merged["cases"] = dedup

    for p in PARAMETERS:
        scores = [coerce_int_score((r.get("category_results") or {}).get(p, {}).get("score", 0)) for r in valid]
        obs = []
        for r in valid:
            obs.extend(((r.get("category_results") or {}).get(p, {}).get("observations") or []))
        merged["category_results"][p] = {
            "score": round(sum(scores) / max(len(scores), 1)),
            "observations": [str(x).strip() for x in obs if str(x).strip()][:100]
        }

    for key in ["uncertain_items", "ambiguous_cases", "unresolved_passages", "notes_on_missing_categories"]:
        items = []
        for r in valid:
            items.extend(r.get(key) or [])
        merged[key] = items[:100]

    merged["coverage"] = {
        "text_processed_whole": True,
        "relevant_passages_count": len(merged["cases"]),
        "uncertain_count": sum(1 for c in merged["cases"] if str(c.get("confidence") or "low").lower() != "high")
    }
    
    merged["_chunk_count"] = chunk_count
    return merged


def run_all_modes(source_text, target_text, source_lang, target_lang, prompt_version):
    """Run all three analysis modes in parallel."""
    modes = ["overview", "detail", "research"]
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(
                run_single_analysis,
                source_text, target_text, source_lang, target_lang, prompt_version, mode
            ): mode
            for mode in modes
        }
        for future in concurrent.futures.as_completed(future_map):
            mode = future_map[future]
            try:
                results[mode] = future.result()
            except Exception as e:
                logger.error(f"Analysis failed for mode {mode}: {e}")
                results[mode] = {
                    "error": str(e),
                    "summary": f"Analysis failed: {e}",
                    "overall_score": 0,
                    "scale_max": 4
                }

    return results
