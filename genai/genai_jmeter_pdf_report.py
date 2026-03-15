import os
import json
import sys
import requests
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"

def find_statistics(report_path):
    for root, dirs, files in os.walk(report_path):
        if "statistics.json" in files:
            return os.path.join(root, "statistics.json")
    raise Exception("statistics.json not found")

def extract_metrics(report_path):
    stats_file = find_statistics(report_path)

    with open(stats_file) as f:
        data = json.load(f)

    total = data["Total"]

    metrics = {
        "avg": total["meanResTime"],
        "p90": total["pct3ResTime"],
        "throughput": total["throughput"],
        "error": total["errorPct"]
    }

    endpoints = {}
    for k in data:
        if k != "Total":
            endpoints[k] = data[k]["meanResTime"]

    return metrics, endpoints

def performance_score(metrics):
    score = 100

    if metrics["avg"] > 1000:
        score -= 30
    elif metrics["avg"] > 500:
        score -= 15

    if metrics["error"] > 5:
        score -= 40
    elif metrics["error"] > 1:
        score -= 20

    if metrics["throughput"] < 10:
        score -= 20

    return max(score, 0)

def grade(score):
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"

def slowest_endpoint(endpoints):
    return max(endpoints, key=endpoints.get)

def ask_ai(metrics, slowest):
    prompt = f"""
Analyze these performance test results:

Average Response Time: {metrics['avg']} ms
Throughput: {metrics['throughput']} req/sec
Error Rate: {metrics['error']} %
Slowest Endpoint: {slowest}

Provide performance insights and optimization recommendations.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload)
    return r.json()["response"]

def create_graph(metrics, report_path):
    labels = ["Avg", "P90"]
    values = [metrics["avg"], metrics["p90"]]

    plt.figure()
    plt.bar(labels, values)
    plt.title("Response Time Comparison")

    graph = os.path.join(report_path, "performance_graph.png")
    plt.savefig(graph)
    plt.close()

    return graph

def create_pdf(report_path, metrics, score, grade_val, slowest, ai_text, graph):
    pdf_path = os.path.join(report_path, "AI_Performance_Report.pdf")

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AI Performance Analysis Report", styles["Title"]))
    story.append(Spacer(1,20))

    story.append(Paragraph(f"Performance Score: {score}/100", styles["Heading2"]))
    story.append(Paragraph(f"Performance Grade: {grade_val}", styles["Heading2"]))
    story.append(Spacer(1,20))

    story.append(Paragraph(f"Average Response Time: {metrics['avg']} ms", styles["Normal"]))
    story.append(Paragraph(f"Throughput: {metrics['throughput']} req/sec", styles["Normal"]))
    story.append(Paragraph(f"Error Rate: {metrics['error']} %", styles["Normal"]))
    story.append(Paragraph(f"Slowest Endpoint: {slowest}", styles["Normal"]))

    story.append(Spacer(1,20))
    story.append(Image(graph, width=400, height=250))

    story.append(Spacer(1,20))
    story.append(Paragraph("AI Insights", styles["Heading2"]))
    story.append(Paragraph(ai_text.replace("\n","<br/>"), styles["Normal"]))

    doc = SimpleDocTemplate(pdf_path)
    doc.build(story)

    return pdf_path

def main():
    report_path = sys.argv[1]

    metrics, endpoints = extract_metrics(report_path)
    score = performance_score(metrics)
    grade_val = grade(score)
    slowest = slowest_endpoint(endpoints)

    ai_text = ask_ai(metrics, slowest)
    graph = create_graph(metrics, report_path)

    pdf = create_pdf(report_path, metrics, score, grade_val, slowest, ai_text, graph)
    print("AI Report Generated:", pdf)

    summary = os.path.join(report_path, "ai_summary.txt")
    with open(summary, "w") as f:
        f.write(f"SCORE={score}\n")
        f.write(f"GRADE={grade_val}\n")
        f.write(f"SLOWEST={slowest}\n")

    print("AI summary saved:", summary)

if __name__ == "__main__":
    main()
