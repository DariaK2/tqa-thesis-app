# TQA Thesis App

TQA Thesis App is a Flask-based web application for automated analysis of translator intervention in literary translation.

The project was developed as part of a bachelor's thesis in philology and translation studies.  
The application compares source and target text fragments and evaluates the degree of intervention across five parameters: cultural, emotional, pragmatic, stylistic, and informational-semantic.

## What the app does

The system processes aligned source and translated text fragments and produces structured evaluation results for each fragment.

It supports three analysis modes:

- **overview** — brief general assessment
- **detail** — more detailed parameter-based analysis
- **research** — extended analytical mode for deeper interpretation

The output includes:

- parameter scores
- overall intervention score
- qualitative comments
- structured response for further aggregation and interpretation

## Evaluation Parameters

The application evaluates translation intervention according to five dimensions:

- **cultural**
- **emotional**
- **pragmatic**
- **stylistic**
- **semantic**

## Application Logic

The workflow of the application can be described as follows:

1. Input texts are uploaded or inserted into the interface.
2. The system extracts and normalizes textual data.
3. The text is segmented into aligned source/target fragments.
4. A prompt is generated depending on the selected analysis mode.
5. The LLM processes the fragment pair.
6. The response is converted into structured output.
7. Results are displayed in the interface and can be aggregated for research purposes.

## Example Output Structure

```json
{
  "source_text": "Original fragment...",
  "target_text": "Translated fragment...",
  "mode": "detail",
  "scores": {
    "cultural": 1,
    "emotional": 3,
    "pragmatic": 2,
    "stylistic": 3,
    "semantic": 2
  },
  "overall_score": 2.2,
  "comment": "The translation intensifies emotional tone and introduces stylistic expansion."
}
```

## Project Structure

- `app.py` — main Flask application
- `requirements.txt` — Python dependencies
- `templates/` — HTML templates
- `static/` — CSS, JS, and other static files
- `.env` — environment variables (not tracked by Git)

## Technologies

- Python
- Flask
- Flask-CORS
- python-dotenv
- OpenAI-compatible API client
- HTML / CSS / JavaScript

## Run Locally

### 1. Open the project folder

```bash
cd ~/Desktop/files_flask
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate it

On macOS / Linux:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Create the `.env` file

Example:

```env
OPENROUTER_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

If your current version uses another provider or additional variables, add them to the same file.

### 6. Run the application

```bash
python app.py
```

The application will usually be available at:

```text
http://127.0.0.1:5000
```

## Notes

- The `.env` file and virtual environment folders are excluded from version control via `.gitignore`.
- The repository contains only the codebase required to run the application.
- Some research outputs, tables, and figures are included in the thesis appendices rather than in the repository itself.

## Repository

Public GitHub repository:  
[https://github.com/DariaK2/tqa-thesis-app](https://github.com/DariaK2/tqa-thesis-app)

## License

This project was developed for academic and research purposes.
