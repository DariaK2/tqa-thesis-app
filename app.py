"""
Flask web application for Translation Intervention Analysis.
"""
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from config import (
    FLASK_DEBUG, FLASK_PORT, VALID_PROMPT_VERSIONS, VALID_ANALYSIS_MODES,
    YANDEX_API_KEY, YANDEX_CLOUD_FOLDER, YANDEX_CLOUD_MODEL
)
from text_extraction import extract_text_from_upload, TextExtractionError, OCRUnavailableError
from analysis import run_single_analysis, run_all_modes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if FLASK_DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        # Extract parameters from request
        source_text = (request.form.get("sourceText") or "").strip()
        target_text = (request.form.get("targetText") or "").strip()
        source_lang = (request.form.get("sourceLang") or "auto").strip()
        target_lang = (request.form.get("targetLang") or "auto").strip()

        prompt_version = (request.form.get("promptVersion") or "MASTER").strip().upper()
        if prompt_version not in VALID_PROMPT_VERSIONS:
            prompt_version = "MASTER"

        analysis_mode = (request.form.get("analysisMode") or "overview").strip().lower()
        if analysis_mode not in VALID_ANALYSIS_MODES:
            analysis_mode = "overview"

        # Handle file uploads
        source_file = request.files.get("sourceFile")
        target_file = request.files.get("targetFile")

        if source_file and source_file.filename:
            source_text = extract_text_from_upload(source_file)
        if target_file and target_file.filename:
            target_text = extract_text_from_upload(target_file)

        # Validate inputs
        if not source_text:
            return jsonify({"error": "No source text provided."}), 400
        if not target_text:
            return jsonify({"error": "No target text provided."}), 400
        if not YANDEX_API_KEY or not YANDEX_CLOUD_FOLDER:
            return jsonify({"error": "Yandex Cloud API key or folder ID not configured."}), 500

        logger.info(f"Starting analysis: mode={analysis_mode}, prompt={prompt_version}")

        # Run analysis
        if analysis_mode == "all":
            results = run_all_modes(
                source_text, target_text, source_lang, target_lang, prompt_version
            )
            return jsonify({
                "mode": "all",
                "results": results,
                "_meta": {
                    "model": YANDEX_CLOUD_MODEL,
                    "prompt_version": prompt_version,
                    "analysis_mode": "all"
                }
            })

        result = run_single_analysis(
            source_text, target_text, source_lang, target_lang, prompt_version, analysis_mode
        )
        
        result["_meta"] = {
            "model": YANDEX_CLOUD_MODEL,
            "prompt_version": prompt_version,
            "analysis_mode": analysis_mode
        }
        
        return jsonify(result)

    except OCRUnavailableError as e:
        logger.error(f"OCR unavailable: {e}")
        return jsonify({"error": str(e)}), 400
    except TextExtractionError as e:
        logger.error(f"Text extraction error: {e}")
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error during analysis")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)
