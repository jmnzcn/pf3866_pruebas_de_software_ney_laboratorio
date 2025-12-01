# tools/compute_kpis.py
"""
Lee los CSV de metrics/ y calcula un resumen simple de KPIs:
- T1: tiempo de diseño por caso (Plan A vs Plan B) desde design_time.csv
- T2: métricas de ejecución de tests desde test_runs.csv
- Precisión de sugerencias RAG desde rag_suggestions.csv
- Flakiness desde flakiness.csv
"""

from pathlib import Path
import csv
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = ROOT / "metrics"

DESIGN_TIME_CSV = METRICS_DIR / "design_time.csv"
TEST_RUNS_CSV = METRICS_DIR / "test_runs.csv"
RAG_SUGGESTIONS_CSV = METRICS_DIR / "rag_suggestions.csv"
FLAKINESS_CSV = METRICS_DIR / "flakiness.csv"


def load_csv(path: Path):
    if not path.is_file():
        print(f"[WARN] No se encontró {path}")
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_t1(design_rows: list[dict]):
    # Esperado: timestamp,plan,feature_or_endpoint,test_files,num_cases,time_minutes,notes
    per_plan = {"A": [], "B": []}
    for row in design_rows:
        plan = row.get("plan")
        if plan not in per_plan:
            continue
        try:
            num_cases = float(row.get("num_cases", "0") or 0)
            time_minutes = float(row.get("time_minutes", "0") or 0)
        except ValueError:
            continue
        if num_cases <= 0:
            continue
        t1_per_case = time_minutes / num_cases
        per_plan[plan].append(t1_per_case)

    result = {}
    for plan, values in per_plan.items():
        if values:
            result[plan] = mean(values)
        else:
            result[plan] = None
    return result


def compute_test_runs(test_rows: list[dict]):
    # Esperado: timestamp,command,tests,failures,errors,skipped,total_time_seconds
    if not test_rows:
        return None

    tests = []
    failures = []
    errors = []
    skipped = []
    times = []

    for row in test_rows:
        try:
            tests.append(int(row.get("tests", 0) or 0))
            failures.append(int(row.get("failures", 0) or 0))
            errors.append(int(row.get("errors", 0) or 0))
            skipped.append(int(row.get("skipped", 0) or 0))
            times.append(float(row.get("total_time_seconds", 0.0) or 0.0))
        except ValueError:
            continue

    if not tests:
        return None

    last = test_rows[-1]
    return {
        "runs": len(tests),
        "avg_tests": mean(tests),
        "avg_failures": mean(failures),
        "avg_errors": mean(errors),
        "avg_skipped": mean(skipped),
        "avg_time": mean(times),
        "last_timestamp": last.get("timestamp"),
        "last_tests": int(last.get("tests", 0) or 0),
        "last_failures": int(last.get("failures", 0) or 0),
        "last_errors": int(last.get("errors", 0) or 0),
        "last_skipped": int(last.get("skipped", 0) or 0),
        "last_time": float(last.get("total_time_seconds", 0.0) or 0.0),
    }


def compute_rag_precision(rag_rows: list[dict]):
    # Esperado: id,endpoint_or_feature,classification,used_in_test_file,notes
    if not rag_rows:
        return None

    total = 0
    A = 0
    B = 0
    C = 0

    for row in rag_rows:
        cls = (row.get("classification") or "").strip().upper()
        if not cls:
            continue
        total += 1
        if cls == "A":
            A += 1
        elif cls == "B":
            B += 1
        elif cls == "C":
            C += 1

    if total == 0:
        return None

    strict = A / total
    relaxed = (A + B) / total

    return {
        "total_suggestions": total,
        "A": A,
        "B": B,
        "C": C,
        "precision_strict": strict,
        "precision_relaxed": relaxed,
    }


def compute_flakiness(flakiness_rows: list[dict]):
    # Esperado: test_name,run_1,...,is_flaky
    if not flakiness_rows:
        return None

    total = 0
    flaky = 0

    for row in flakiness_rows:
        total += 1
        flag = str(row.get("is_flaky", "")).strip().lower()
        if flag in ("true", "1", "yes"):
            flaky += 1

    if total == 0:
        return None

    return {
        "total_tests": total,
        "flaky_tests": flaky,
        "flaky_ratio": flaky / total,
    }


def main():
    print("=== KPIs desde metrics/ ===")

    # T1
    design_rows = load_csv(DESIGN_TIME_CSV)
    t1 = compute_t1(design_rows)
    if t1:
        print("\n[T1] Tiempo de diseño promedio por caso:")
        for plan, value in t1.items():
            if value is None:
                print(f"  Plan {plan}: sin datos")
            else:
                print(f"  Plan {plan}: {value:.2f} min/caso")
    else:
        print("\n[T1] No hay datos (design_time.csv)")

    # T2 y estado de la suite
    test_rows = load_csv(TEST_RUNS_CSV)
    tr = compute_test_runs(test_rows)
    if tr:
        print("\n[T2] Métricas de ejecución de tests:")
        print(f"  Corridas registradas: {tr['runs']}")
        print(f"  Tests promedio por corrida: {tr['avg_tests']:.1f}")
        print(f"  Fallos promedio: {tr['avg_failures']:.1f}")
        print(f"  Tiempo promedio: {tr['avg_time']:.2f} s")
        print("  Última corrida:")
        print(f"    Fecha: {tr['last_timestamp']}")
        print(f"    Tests: {tr['last_tests']}  Failures: {tr['last_failures']}  Errors: {tr['last_errors']}  Skipped: {tr['last_skipped']}")
        print(f"    Tiempo total: {tr['last_time']:.2f} s")
    else:
        print("\n[T2] No hay datos (test_runs.csv)")

    # Precisión RAG
    rag_rows = load_csv(RAG_SUGGESTIONS_CSV)
    rp = compute_rag_precision(rag_rows)
    if rp:
        print("\n[Precisión RAG]")
        print(f"  Sugerencias totales: {rp['total_suggestions']}")
        print(f"  A: {rp['A']}  B: {rp['B']}  C: {rp['C']}")
        print(f"  Precisión estricta (A/total): {rp['precision_strict']:.2%}")
        print(f"  Precisión relajada ((A+B)/total): {rp['precision_relaxed']:.2%}")
    else:
        print("\n[Precisión RAG] No hay datos (rag_suggestions.csv)")

    # Flakiness
    fl_rows = load_csv(FLAKINESS_CSV)
    flk = compute_flakiness(fl_rows)
    if flk:
        print("\n[Flakiness]")
        print(f"  Tests analizados: {flk['total_tests']}")
        print(f"  Tests flaky: {flk['flaky_tests']}")
        print(f"  Proporción flaky: {flk['flaky_ratio']:.2%}")
    else:
        print("\n[Flakiness] No hay datos (flakiness.csv)")


if __name__ == "__main__":
    main()
