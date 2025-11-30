# tools/detect_flakiness.py
import xml.etree.ElementTree as ET
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = ROOT / "metrics"
CSV_PATH = METRICS_DIR / "flakiness.csv"


def parse_file(xml_path: Path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    # pytest genera <testcase classname="..." name="..." time="...">
    results = {}
    for case in root.iter("testcase"):
        name = f"{case.attrib.get('classname','')}.{case.attrib.get('name','')}"
        status = "passed"
        for child in case:
            if child.tag in ("failure", "error"):
                status = "failed"
            elif child.tag == "skipped":
                status = "skipped"
        results[name] = status
    return results


def main():
    xml_files = sorted(METRICS_DIR.glob("last_run_*.xml"))
    if not xml_files:
        print("No se encontraron archivos last_run_*.xml en metrics/")
        return

    all_runs = [parse_file(f) for f in xml_files]
    # Conjunto de todos los testcases
    all_names = set().union(*[r.keys() for r in all_runs])

    rows = []
    for name in sorted(all_names):
        statuses = [r.get(name, "missing") for r in all_runs]
        flaky = len(set(statuses)) > 1  # cambió de estado
        rows.append([name] + statuses + [flaky])

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["test_name"] + [f"run_{i+1}" for i in range(len(all_runs))] + ["is_flaky"]
        writer.writerow(header)
        writer.writerows(rows)

    print("Reporte de flakiness escrito en", CSV_PATH)


if __name__ == "__main__":
    main()
