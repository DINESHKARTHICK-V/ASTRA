# ============================================================
#  ASTRA Cloud -- Step 31: Final Dataset Audit
#  File   : ml/final_dataset_audit.py
#  Purpose: Audit all project datasets using actual files.
#           No values are invented or estimated.
#  Outputs: reports/final_dataset_audit.csv
#           reports/final_dataset_audit.txt
# ============================================================
import sys, csv
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO   = Path(__file__).resolve().parent.parent
REP    = REPO / "reports"

HTRU2_CSV      = REPO / "data" / "htru2" / "HTRU_2.csv"
VALID_CSV      = REP / "radio_fits_validation.csv"
COMPAT_CSV     = REP / "radio_htru2_compatible.csv"
REJECT_CSV     = REP / "radio_feature_rejection.csv"
PRED_CSV       = REP / "radio_predictions.csv"
AUDIT_CSV      = REP / "final_dataset_audit.csv"
AUDIT_TXT      = REP / "final_dataset_audit.txt"

def run():
    print("=" * 64)
    print("  ASTRA Cloud -- Step 31: Final Dataset Audit")
    print("=" * 64)

    # ── HTRU2 ──────────────────────────────────────────────────────
    df = pd.read_csv(HTRU2_CSV)
    htru2_total   = len(df)
    htru2_class0  = int((df["Target"] == 0).sum())
    htru2_class1  = int((df["Target"] == 1).sum())
    X = df.drop("Target", axis=1)
    y = df["Target"]
    Xtr, Xte, _, _ = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
    htru2_train  = len(Xtr)
    htru2_test   = len(Xte)

    print(f"\n  HTRU2 Dataset")
    print(f"    Total samples : {htru2_total}")
    print(f"    Class 0 (non-pulsar) : {htru2_class0}")
    print(f"    Class 1 (pulsar)     : {htru2_class1}")
    print(f"    Training split : {htru2_train}")
    print(f"    Testing split  : {htru2_test}")

    # ── Radio FITS ─────────────────────────────────────────────────
    val_df    = pd.read_csv(VALID_CSV)
    total     = len(val_df)
    valid     = int((val_df["validation_status"] == "VALID_PSRFITS").sum())
    invalid   = int((val_df["validation_status"].str.startswith("INVALID")).sum())
    unsup     = int((val_df["validation_status"].str.startswith("UNSUPPORTED")).sum())
    compat    = len(pd.read_csv(COMPAT_CSV))
    rejected  = len(pd.read_csv(REJECT_CSV))
    pred_df   = pd.read_csv(PRED_CSV)
    inference = len(pred_df)

    print(f"\n  Radio FITS Dataset")
    print(f"    Total collected files : {total}")
    print(f"    Valid (PSRFITS)       : {valid}")
    print(f"    Invalid               : {invalid}")
    print(f"    Unsupported           : {unsup}")
    print(f"    Compatible (HTRU2)    : {compat}")
    print(f"    Rejected              : {rejected}")
    print(f"    Inference pipeline    : {inference}")

    # ── CSV ────────────────────────────────────────────────────────
    rows = [
        {"dataset":"HTRU2","metric":"total_samples",      "value":htru2_total,  "notes":"All samples in HTRU_2.csv"},
        {"dataset":"HTRU2","metric":"class_0_non_pulsar",  "value":htru2_class0, "notes":"Negative class"},
        {"dataset":"HTRU2","metric":"class_1_pulsar",      "value":htru2_class1, "notes":"Positive class"},
        {"dataset":"HTRU2","metric":"training_samples",    "value":htru2_train,  "notes":"70% split, random_state=42, stratified"},
        {"dataset":"HTRU2","metric":"testing_samples",     "value":htru2_test,   "notes":"30% split, random_state=42, stratified"},
        {"dataset":"Radio FITS","metric":"total_collected","value":total,    "notes":"Files in data/radio_fits/"},
        {"dataset":"Radio FITS","metric":"valid_psrfits",  "value":valid,    "notes":"Passed astropy PSRFITS validation"},
        {"dataset":"Radio FITS","metric":"invalid",        "value":invalid,  "notes":"Failed FITS integrity check"},
        {"dataset":"Radio FITS","metric":"unsupported",    "value":unsup,    "notes":"Non-PSRFITS / non-radio format"},
        {"dataset":"Radio FITS","metric":"compatible_htru2","value":compat,  "notes":"Possess all 8 HTRU2 features"},
        {"dataset":"Radio FITS","metric":"rejected",       "value":rejected, "notes":"Missing one or more HTRU2 features"},
        {"dataset":"Radio FITS","metric":"inference_pipeline","value":inference,"notes":"Submitted to radio_inference.py"},
    ]
    with open(AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dataset","metric","value","notes"])
        w.writeheader(); w.writerows(rows)

    # ── TXT ────────────────────────────────────────────────────────
    lines = [
        "=" * 64,
        "  ASTRA Cloud -- Final Dataset Audit",
        "=" * 64,
        "",
        "  HTRU2 DATASET",
        f"    Total samples          : {htru2_total}",
        f"    Class 0 (non-pulsar)   : {htru2_class0}",
        f"    Class 1 (pulsar)       : {htru2_class1}",
        f"    Class imbalance ratio  : {htru2_class0/htru2_class1:.1f}:1",
        f"    Training samples       : {htru2_train}  (70%, stratified, random_state=42)",
        f"    Testing samples        : {htru2_test}   (30%, stratified, random_state=42)",
        "",
        "  RADIO FITS DATASET  (GBT/VEGAS, PSR J1713+0747, 820 MHz)",
        f"    Total collected files  : {total}",
        f"    Valid PSRFITS files    : {valid}",
        f"    Invalid files          : {invalid}",
        f"    Unsupported formats    : {unsup}",
        f"    Compatible with HTRU2  : {compat}  (require all 8 search-mode features)",
        f"    Rejected from ML       : {rejected}  (missing DM-SNR curve features)",
        f"    Entering inference pipe: {inference}",
        "",
        "  NOTE: All values sourced from actual files and generated reports.",
        "        No values have been estimated or invented.",
        "=" * 64,
    ]
    with open(AUDIT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n[OK] {AUDIT_CSV}")
    print(f"[OK] {AUDIT_TXT}")
    print("=" * 64)

if __name__ == "__main__":
    run()
