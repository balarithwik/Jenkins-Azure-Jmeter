import sys
import subprocess
import re
import textwrap
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def read_metrics(path: str) -> dict:
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                data[k] = v
    return data


def clean_ai_text(text: str) -> str:
    if not text:
        return "No response returned by Ollama."

    # Remove ANSI escape sequences like \x1b[7D\x1b[K
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub("", text)

    # Remove any remaining strange control characters except newline/tab
    text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)

    # Remove markdown bold markers
    text = text.replace("**", "")

    # Normalize spaces
    text = text.replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def call_ollama(prompt: str) -> str:
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["NO_COLOR"] = "1"
        env["TERM"] = "dumb"

        result = subprocess.run(
            ["ollama", "run", "phi3", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env=env
        )

        raw_output = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
        cleaned_output = clean_ai_text(raw_output)

        return cleaned_output if cleaned_output else "No response returned by Ollama."

    except Exception as e:
        return f"Ollama execution failed: {e}"


def derive_summary(metrics: dict):
    total = int(metrics.get("TOTAL_TESTS", "0"))
    passed = int(metrics.get("PASSED", "0"))
    failed = int(metrics.get("FAILED", "0"))
    errors = int(metrics.get("ERRORS", "0"))
    skipped = int(metrics.get("SKIPPED", "0"))
    failed_names = metrics.get("FAILED_TEST_NAMES", "None")

    effective_failures = failed + errors

    if total <= 0:
        score = 0
    else:
        score = max(0, 100 - int((effective_failures / total) * 100))

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "D"

    top_issue = "None" if failed_names == "None" else failed_names
    return str(score), grade, top_issue


def generate_pdf(output_file: str, metrics: dict, score: str, grade: str, top_issue: str, ai_text: str):
    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4
    y = height - 50
    left_margin = 50
    max_width_chars = 95

    def write_line(text="", step=18, font_name="Helvetica", font_size=11):
        nonlocal y
        if y < 50:
            c.showPage()
            y = height - 50
        c.setFont(font_name, font_size)
        c.drawString(left_margin, y, text)
        y -= step

    write_line("Functional AI Analysis Report", step=26, font_name="Helvetica-Bold", font_size=16)
    write_line("")

    write_line(f"Total Tests      : {metrics.get('TOTAL_TESTS', '0')}")
    write_line(f"Passed           : {metrics.get('PASSED', '0')}")
    write_line(f"Failed           : {metrics.get('FAILED', '0')}")
    write_line(f"Errors           : {metrics.get('ERRORS', '0')}")
    write_line(f"Skipped          : {metrics.get('SKIPPED', '0')}")
    write_line(f"Duration         : {metrics.get('DURATION', '0')}")
    write_line(f"Functional Score : {score}/100")
    write_line(f"Functional Grade : {grade}")
    write_line(f"Top Issue        : {top_issue}")
    write_line("")
    write_line("AI Analysis:", font_name="Helvetica-Bold")
    write_line("")

    for paragraph in ai_text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            write_line("")
            continue

        wrapped_lines = textwrap.wrap(paragraph, width=max_width_chars)
        for wrapped_line in wrapped_lines:
            write_line(wrapped_line)

    c.save()


def main():
    if len(sys.argv) < 2:
        print("Usage: python genai_selenium_analysis.py functional_metrics.txt")
        sys.exit(1)

    metrics_file = sys.argv[1]
    metrics = read_metrics(metrics_file)

    prompt = f"""
You are analyzing Selenium functional test results for a retail application.

Metrics:
{metrics}

Provide:
1. Brief overall functional assessment
2. Likely failure area
3. Business impact
4. Recommendation

Return plain text only.
Do not use markdown.
Do not use bullets with special symbols.
Do not include terminal formatting or ANSI characters.
"""

    ai_text = call_ollama(prompt)
    score, grade, top_issue = derive_summary(metrics)

    with open("functional_ai_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"SCORE={score}\n")
        f.write(f"GRADE={grade}\n")
        f.write(f"TOP_ISSUE={top_issue}\n")
        f.write("DETAILS_BEGIN\n")
        f.write(ai_text + "\n")
        f.write("DETAILS_END\n")

    generate_pdf(
        "Functional_AI_Report.pdf",
        metrics,
        score,
        grade,
        top_issue,
        ai_text
    )

    print("functional_ai_summary.txt generated successfully")
    print("Functional_AI_Report.pdf generated successfully")


if __name__ == "__main__":
    main()