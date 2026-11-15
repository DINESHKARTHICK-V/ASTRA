# ============================================================
#  ASTRA Cloud -- Step 32: Final Model Result Audit
#  File   : ml/final_model_audit.py
#  Purpose: Verify stored model metrics against live recalculation.
#           Reports any mismatch. Does NOT overwrite stored results.
#  Output : reports/final_model_audit.csv
# ============================================================
import sys, csv, json
from pathlib import Path
import pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO  = Path(__file__).resolve().parent.parent
REP   = REPO / "reports"
MOD   = REPO / "models"

HTRU2_CSV   = REPO / "data" / "htru2" / "HTRU_2.csv"
METRICS_JSON = REP / "metrics.json"
AUDIT_CSV   = REP / "final_model_audit.csv"

MODEL_FILES = {
    "random_forest": MOD / "random_forest_htru2.pkl",
    "xgboost":       MOD / "xgboost.joblib",
    "svm":           MOD / "svm.joblib",
    "mlp":           MOD / "mlp.joblib",
}
SCALER_FILE = MOD / "scaler.joblib"

def run():
    print("=" * 64)
    print("  ASTRA Cloud -- Step 32: Final Model Result Audit")
    print("=" * 64)

    # Load HTRU2 + split (same seed as training)
    df = pd.read_csv(HTRU2_CSV)
    X = df.drop("Target", axis=1)
    y = df["Target"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)

    # Load stored metrics
    with open(METRICS_JSON) as f:
        stored = json.load(f)

    # Load scaler if available
    scaler = None
    if SCALER_FILE.exists():
        scaler = joblib.load(SCALER_FILE)

    rows = []
    for name, path in MODEL_FILES.items():
        if not path.exists():
            rows.append({"model":name,"metric":"STATUS","stored":"N/A","recalculated":"MODEL_FILE_NOT_FOUND","match":"N/A","notes":str(path)})
            continue
        try:
            clf = joblib.load(path)
        except Exception as e:
            rows.append({"model":name,"metric":"STATUS","stored":"N/A","recalculated":f"LOAD_ERROR:{e}","match":"N/A","notes":""})
            continue

        # Some models need scaling
        needs_scale = name in ("svm", "mlp", "xgboost")
        if needs_scale and scaler is not None:
            Xte_use = scaler.transform(Xte)
        else:
            Xte_use = Xte.values

        try:
            ypred = clf.predict(Xte_use)
            yprob = clf.predict_proba(Xte_use)[:, 1]
        except Exception as e:
            rows.append({"model":name,"metric":"STATUS","stored":"N/A","recalculated":f"PREDICT_ERROR:{e}","match":"N/A","notes":""})
            continue

        live = {
            "accuracy" : round(accuracy_score(yte, ypred), 4),
            "precision": round(precision_score(yte, ypred, zero_division=0), 4),
            "recall"   : round(recall_score(yte, ypred), 4),
            "f1"       : round(f1_score(yte, ypred), 4),
            "roc_auc"  : round(roc_auc_score(yte, yprob), 4),
        }
        st = stored.get(name, {})
        for metric, live_val in live.items():
            stor_val = st.get(metric, "NOT_STORED")
            match = "YES" if str(round(float(stor_val),4)) == str(live_val) else "MISMATCH"
            rows.append({
                "model"       : name,
                "metric"      : metric,
                "stored"      : stor_val,
                "recalculated": live_val,
                "match"       : match,
                "notes"       : "" if match == "YES" else f"Stored={stor_val} vs Live={live_val}",
            })
        print(f"\n  {name.upper()}")
        for metric, lv in live.items():
            sv = st.get(metric,"?")
            flag = "✓" if str(round(float(sv),4))==str(lv) else "MISMATCH"
            print(f"    {metric:<12s}: stored={sv}  live={lv}  [{flag}]")

    with open(AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model","metric","stored","recalculated","match","notes"])
        w.writeheader(); w.writerows(rows)

    mismatches = [r for r in rows if r["match"] == "MISMATCH"]
    print(f"\n  Mismatches found: {len(mismatches)}")
    if mismatches:
        for m in mismatches:
            print(f"    !! {m['model']} {m['metric']}: {m['notes']}")
    print(f"\n[OK] {AUDIT_CSV}")
    print("=" * 64)

if __name__ == "__main__":
    run()
