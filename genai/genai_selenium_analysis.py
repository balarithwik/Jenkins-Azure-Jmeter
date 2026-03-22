import sys
import subprocess
from pathlib import Path

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


def call_ollama(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", "phi3", prompt],
            capture_output=True,
            text=True,
            timeout=180
        )
        output = result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
        return output if output else "No response returned by Ollama."
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

    def write_line(text, step=18):
        nonlocal y
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, text[:110])
        y -= step

    c.setFont("Helvetica-Bold", 16)
    write_line("Functional AI Analysis Report", 24)

    c.setFont("Helvetica", 11)
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
    write_line("AI Analysis:")
    write_line("")

    for line in ai_text.splitlines():
        if not line.strip():
            write_line("")
        else:
            # simple wrapping
            chunk = line
            while len(chunk) > 105:
                write_line(chunk[:105])
                chunk = chunk[105:]
            write_line(chunk)

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