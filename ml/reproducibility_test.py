# ============================================================
#  ASTRA Cloud -- Step 34: Reproducibility Test
#  File   : ml/reproducibility_test.py
#  Purpose: Verify that the HTRU2 preprocessing, train/test split
#           and model loading are fully reproducible.
#  Output : reports/reproducibility_check.txt
# ============================================================
import sys
from pathlib import Path
import pandas as pd, joblib
from sklearn.model_selection import train_test_split

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
REP  = REPO / "reports"
MOD  = REPO / "models"

HTRU2_CSV     = REPO / "data" / "htru2" / "HTRU_2.csv"
MODEL_FILE    = MOD / "random_forest_htru2.pkl"
FEATURES_FILE = MOD / "htru2_features.pkl"
OUT_TXT       = REP / "reproducibility_check.txt"

EXPECTED_FEATURES = [
    "Profile_Mean","Profile_Std","Profile_Skewness","Profile_Kurtosis",
    "DM_Mean","DM_Std","DM_Skewness","DM_Kurtosis",
]
EXPECTED_TRAIN = 12528
EXPECTED_TEST  = 5370

def run():
    print("=" * 64)
    print("  ASTRA Cloud -- Step 34: Reproducibility Test")
    print("=" * 64)
    results = []

    # 1. Load HTRU2
    df = pd.read_csv(HTRU2_CSV)
    results.append(f"[CHECK 1] HTRU2 file loaded: {len(df)} rows")

    # 2. Train/test split
    X = df.drop("Target", axis=1)
    y = df["Target"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
    train_ok = len(Xtr) == EXPECTED_TRAIN
    test_ok  = len(Xte) == EXPECTED_TEST
    results.append(f"[CHECK 2] Train size: {len(Xtr)}  (expected {EXPECTED_TRAIN})  {'PASS' if train_ok else 'FAIL'}")
    results.append(f"[CHECK 3] Test size : {len(Xte)}  (expected {EXPECTED_TEST})  {'PASS' if test_ok else 'FAIL'}")

    # 3. Feature order
    saved_feats = joblib.load(FEATURES_FILE)
    feats_match = list(saved_feats) == EXPECTED_FEATURES
    results.append(f"[CHECK 4] Saved feature list matches expected: {'PASS' if feats_match else 'FAIL'}")
    for i, (s, e) in enumerate(zip(list(saved_feats), EXPECTED_FEATURES)):
        status = "OK" if s == e else f"MISMATCH (got {s})"
        results.append(f"          Feature {i+1}: {e}  {status}")

    # 4. Model loads
    model = joblib.load(MODEL_FILE)
    results.append(f"[CHECK 5] Model loaded: {type(model).__name__}  PASS")
    results.append(f"          n_estimators: {model.n_estimators}")
    results.append(f"          random_state: {model.random_state}")

    # 5. Model can predict
    sample = Xte.iloc[:5]
    preds  = model.predict(sample)
    results.append(f"[CHECK 6] Model produces predictions on 5 test samples: PASS  ({list(preds)})")

    # 6. Class balance check
    train_pos = int(ytr.sum())
    test_pos  = int(yte.sum())
    results.append(f"[CHECK 7] Training positives (class 1): {train_pos}")
    results.append(f"[CHECK 7] Testing  positives (class 1): {test_pos}")

    all_pass = all(
        s in ("PASS","OK") or "PASS" in s
        for s in results if "[CHECK" in s and "Feature" not in s and "n_est" not in s and "random" not in s
    )
    results.append("")
    results.append(f"OVERALL REPRODUCIBILITY: {'PASS — All checks passed.' if all_pass else 'WARNING — See above for failures.'}")

    for r in results:
        print(" ", r)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("ASTRA Cloud — Reproducibility Check\n")
        f.write("=" * 64 + "\n")
        f.write("\n".join(results) + "\n")

    print(f"\n[OK] {OUT_TXT}")
    print("=" * 64)

if __name__ == "__main__":
    run()
