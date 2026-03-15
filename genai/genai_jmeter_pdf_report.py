import os
import sys
import json
import requests
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"


def find_statistics_file(report_path):
    for root, dirs, files in os.walk(report_path):
        if "statistics.json" in files:
            return os.path.join(root, "statistics.json")
    return None


def extract_metrics(report_path):

    stats_file = find_statistics_file(report_path)

    if not stats_file:
        raise Exception("statistics.json not found")

    with open(stats_file) as f:
        data = json.load(f)

    total = data["Total"]

    metrics = {
        "samples": total["sampleCount"],
        "error_pct": total["errorPct"],
        "avg": total["meanResTime"],
        "p90": total["pct1ResTime"],
        "p95": total["pct2ResTime"],
        "p99": total["pct3ResTime"],
        "throughput": total["throughput"]
    }

    return metrics


def create_graphs(metrics, output_path):

    latency_chart = os.path.join(output_path, "latency_chart.png")

    labels = ["Average", "P90", "P95", "P99"]
    values = [metrics["avg"], metrics["p90"], metrics["p95"], metrics["p99"]]

    plt.bar(labels, values)
    plt.title("Latency Distribution")
    plt.ylabel("Response Time (ms)")
    plt.savefig(latency_chart)
    plt.clf()

    percentile_chart = os.path.join(output_path, "percentile_chart.png")

    plt.plot(labels, values, marker='o')
    plt.title("Latency Percentiles")
    plt.ylabel("Response Time (ms)")
    plt.savefig(percentile_chart)
    plt.clf()

    return latency_chart, percentile_chart


def analyze_with_ollama(metrics):

    prompt = f"""
You are a performance engineer.

Analyze the following JMeter performance metrics.

Total Requests: {metrics['samples']}
Average Response Time: {metrics['avg']} ms
P95 Latency: {metrics['p95']} ms
Error Percentage: {metrics['error_pct']} %
Throughput: {metrics['throughput']} req/sec

Provide:

1. Performance Health Summary
2. Bottleneck Analysis
3. Risk Level
4. Optimization Recommendations
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


def generate_pdf(report_path, metrics, analysis, charts):

    pdf_file = os.path.join(report_path, "AI_Performance_Report.pdf")

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Performance Test Report", styles['Title']))
    elements.append(Spacer(1,20))

    summary = f"""
Total Requests: {metrics['samples']}<br/>
Average Response Time: {metrics['avg']} ms<br/>
95th Percentile: {metrics['p95']} ms<br/>
Error Percentage: {metrics['error_pct']} %<br/>
Throughput: {metrics['throughput']} req/sec
"""

    elements.append(Paragraph(summary, styles['BodyText']))
    elements.append(Spacer(1,20))

    elements.append(Image(charts[0], width=400, height=250))
    elements.append(Spacer(1,20))

    elements.append(Image(charts[1], width=400, height=250))
    elements.append(Spacer(1,20))

    elements.append(Paragraph("AI Analysis", styles['Heading2']))
    elements.append(Paragraph(analysis.replace("\n","<br/>"), styles['BodyText']))

    doc = SimpleDocTemplate(pdf_file)
    doc.build(elements)

    return pdf_file


def main():

    if len(sys.argv) < 2:
        print("Usage: python script.py <jmeter_html_folder>")
        sys.exit(1)

    report_path = sys.argv[1]

    metrics = extract_metrics(report_path)

    charts = create_graphs(metrics, report_path)

    analysis = analyze_with_ollama(metrics)

    pdf = generate_pdf(report_path, metrics, analysis, charts)

    print("AI Report Generated:", pdf)


if __name__ == "__main__":
    main()