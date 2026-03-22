import sys
import os
import subprocess

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
        return result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
    except Exception as e:
        return f"Ollama execution failed: {e}"

def derive_summary(metrics: dict) -> tuple[str, str, str]:
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

Return a brief analysis of functional quality, likely failure area, and business impact.
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

    print("functional_ai_summary.txt generated successfully")

if __name__ == "__main__":
    main()