"""
ASTRA Cloud — Phase 1 Audit Script
Inspect actual state of all project components.
"""
import os, sys, csv, json, hashlib, struct
from pathlib import Path

PROJECT = Path(r"e:\ASTRA CLOUD")

def section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def sha256_first_mb(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        chunk = f.read(1024*1024)
        h.update(chunk)
    return h.hexdigest()

# ──────────────────────────────────────────────────────────
# 1. HTRU2 Dataset
# ──────────────────────────────────────────────────────────
section("1. HTRU2 Dataset")
htru2_path = PROJECT / "data/htru2/HTRU_2.csv"
print(f"File exists: {htru2_path.exists()}")
print(f"File size:   {htru2_path.stat().st_size:,} bytes")

with open(htru2_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = reader.fieldnames

print(f"Row count:   {len(rows):,} (data rows, excluding header)")
print(f"Columns:     {columns}")

labels = [int(r['Target']) for r in rows]
n_positive = sum(1 for l in labels if l == 1)
n_negative = sum(1 for l in labels if l == 0)
print(f"Label dist:  positive={n_positive}, negative={n_negative}")

import struct
missing_vals = {col: sum(1 for r in rows if r[col].strip() == '') for col in columns}
print(f"Missing vals:{missing_vals}")

# ──────────────────────────────────────────────────────────
# 2. Parkes Dataset
# ──────────────────────────────────────────────────────────
section("2. Parkes Dataset")
parkes_path = PROJECT / "data/parkes/PDFB4_Search_J0437-4715.sf"
radio_fits_dir = PROJECT / "data/radio_fits"
fits_dir = PROJECT / "data/fits"

print(f"Parkes .sf file: {parkes_path.exists()}, size={parkes_path.stat().st_size:,} bytes")

# Check PSRFITS magic bytes
with open(parkes_path, 'rb') as f:
    header_bytes = f.read(8)
print(f"File magic (hex): {header_bytes.hex()}")
print(f"File magic (ascii): {header_bytes[:6]}")

# Check radio FITS files  
print(f"\nRadio FITS dir: {radio_fits_dir}")
for f in radio_fits_dir.iterdir():
    print(f"  {f.name}: {f.stat().st_size:,} bytes")

# ──────────────────────────────────────────────────────────
# 3. Integrated Master Dataset
# ──────────────────────────────────────────────────────────
section("3. Integrated Master Dataset")
master_path = PROJECT / "data/integrated/master_dataset.csv"
manifest_path = PROJECT / "data/integrated/integration_manifest.json"
validation_path = PROJECT / "data/integrated/validation_report.json"
dict_path = PROJECT / "data/integrated/data_dictionary.csv"

print(f"master_dataset.csv exists: {master_path.exists()}, size={master_path.stat().st_size:,} bytes")
print(f"integration_manifest.json: {manifest_path.exists()}")
print(f"validation_report.json:    {validation_path.exists()}")
print(f"data_dictionary.csv:       {dict_path.exists()}")

with open(master_path) as f:
    reader = csv.DictReader(f)
    master_rows = list(reader)
    master_cols = reader.fieldnames

print(f"\nMaster record count: {len(master_rows):,}")
print(f"Master columns ({len(master_cols)}): {master_cols[:10]}...")

# Count by source
htru2_recs = sum(1 for r in master_rows if r.get('source_dataset') == 'HTRU2')
parkes_recs = sum(1 for r in master_rows if r.get('source_dataset') == 'PARKES_PDFB4')
other_recs = len(master_rows) - htru2_recs - parkes_recs
print(f"Records from HTRU2:        {htru2_recs:,}")
print(f"Records from PARKES_PDFB4: {parkes_recs:,}")
print(f"Records from other:        {other_recs:,}")

# ──────────────────────────────────────────────────────────
# 4. Models
# ──────────────────────────────────────────────────────────
section("4. ML Models")
models_dir = PROJECT / "models"
for f in models_dir.iterdir():
    if not f.name.startswith('.'):
        print(f"  {f.name}: {f.stat().st_size:,} bytes")

# ──────────────────────────────────────────────────────────
# 5. Reports
# ──────────────────────────────────────────────────────────
section("5. Reports Directory")
reports_dir = PROJECT / "reports"
for f in reports_dir.iterdir():
    print(f"  {f.name}: {f.stat().st_size:,} bytes")

# ──────────────────────────────────────────────────────────
# 6. Dependencies
# ──────────────────────────────────────────────────────────
section("6. Python Package Check")
packages = ['numpy', 'pandas', 'sklearn', 'joblib', 'astropy', 'fastapi', 
            'uvicorn', 'psycopg2', 'shap', 'mlflow', 'xgboost', 'scipy',
            'pyarrow', 'fastparquet']
for pkg in packages:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, '__version__', 'installed')
        print(f"  {pkg}: ✓ {ver}")
    except ImportError:
        print(f"  {pkg}: ✗ NOT INSTALLED")

# ──────────────────────────────────────────────────────────
# 7. Neo4j Check
# ──────────────────────────────────────────────────────────
section("7. Neo4j Check")
try:
    import neo4j
    print(f"  neo4j driver: ✓ {neo4j.__version__}")
except ImportError:
    print("  neo4j driver: ✗ NOT INSTALLED")

# Check if any code references Neo4j
neo4j_refs = list(PROJECT.rglob("*.py"))
neo4j_files = []
for f in neo4j_refs:
    try:
        content = f.read_text(errors='ignore')
        if 'neo4j' in content.lower():
            neo4j_files.append(str(f))
    except:
        pass
print(f"  Python files referencing neo4j: {len(neo4j_files)}")
for f in neo4j_files[:5]:
    print(f"    {f}")

# ──────────────────────────────────────────────────────────
# 8. MLflow Check
# ──────────────────────────────────────────────────────────
section("8. MLflow Check")
try:
    import mlflow
    print(f"  mlflow: ✓ {mlflow.__version__}")
    # Check for experiment tracking
    mlflow_refs = [f for f in PROJECT.rglob("*.py") 
                   if 'mlflow' in f.read_text(errors='ignore').lower()]
    print(f"  Files using mlflow: {len(mlflow_refs)}")
except ImportError:
    print("  mlflow: ✗ NOT INSTALLED")

# ──────────────────────────────────────────────────────────
# 9. SHAP Check  
# ──────────────────────────────────────────────────────────
section("9. SHAP Check")
try:
    import shap
    print(f"  shap: ✓ {shap.__version__}")
except ImportError:
    print("  shap: ✗ NOT INSTALLED")

# ──────────────────────────────────────────────────────────
# 10. Frontend
# ──────────────────────────────────────────────────────────
section("10. Frontend Key Files")
frontend_src = PROJECT / "frontend/src"
api_ts = frontend_src / "services/api.ts"
print(f"  api.ts size: {api_ts.stat().st_size:,} bytes")

# Check for hardcoded/demo data in key pages
pages_dir = frontend_src / "pages"
for page_file in sorted(pages_dir.iterdir()):
    content = page_file.read_text(errors='ignore')
    has_hardcoded = 'Math.random' in content or 'TODO' in content or 'DEMO' in content
    has_api_calls = 'apiService' in content or 'fetch(' in content
    print(f"  {page_file.name}: hardcoded={has_hardcoded}, api_calls={has_api_calls}")

print("\n" + "="*60)
print("  AUDIT COMPLETE")
print("="*60)
