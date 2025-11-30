# tools/collect_test_metrics.py
import csv
import datetime
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]  # carpeta laboratorio
METRICS_DIR = ROOT / "metrics"
XML_PATH = METRICS_DIR / "last_run.xml"
CSV_PATH = METRICS_DIR / "test_runs.csv"


def parse_junit(xml_path: Path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Formato típico de JUnit de pytest: <testsuite ... tests="..." failures="..." errors="..." skipped="..." time="...">
    suite = root
    tests = int(suite.attrib.get("tests", 0))
    failures = int(suite.attrib.get("failures", 0))
    errors = int(suite.attrib.get("errors", 0))
    skipped = int(suite.attrib.get("skipped", 0))
    time = float(suite.attrib.get("time", 0.0))
    return tests, failures, errors, skipped, time


def main():
    if not XML_PATH.is_file():
        print(f"No existe {XML_PATH}, ejecuta pytest con --junitxml primero.", file=sys.stderr)
        sys.exit(1)

    tests, failures, errors, skipped, total_time = parse_junit(XML_PATH)

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_PATH.exists()

    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow([
                "timestamp",
                "command",
                "tests",
                "failures",
                "errors",
                "skipped",
                "total_time_seconds",
            ])

        now = datetime.datetime.now().isoformat(timespec="seconds")
        # Si quieres, pasa el comando como argumento (sys.argv[1:])
        command = "pytest tests/api -q --junitxml=metrics/last_run.xml"
        writer.writerow([
            now,
            command,
            tests,
            failures,
            errors,
            skipped,
            total_time,
        ])

    print("Métricas de ejecución agregadas a", CSV_PATH)


if __name__ == "__main__":
    main()
