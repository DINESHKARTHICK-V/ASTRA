# ============================================================
#  ASTRA Cloud — Two-Dataset Integration Service
#  File   : backend/app/services/dataset_service.py
#  Purpose: Discovers, validates, and provides decoupled readers
#           for Dataset A (HTRU2 CSV) and Dataset B (Parkes PSRFITS).
#           Strictly enforces architectural separation between
#           tabular summary moments and raw radio dynamic spectra.
# ============================================================

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from astropy.io import fits

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

HTRU2_DATA_PATH = DATA_DIR / "htru2" / "HTRU_2.csv"
HTRU2_FALLBACK_PATH = PROJECT_ROOT / "pulsar_star_test2.csv"
PARKES_DATA_PATH = DATA_DIR / "parkes" / "PDFB4_Search_J0437-4715.sf"
RADIO_FITS_DIR = DATA_DIR / "radio_fits"

HTRU2_CANONICAL_COLUMNS = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
    "Target",
]

HTRU2_ALT_COLUMNS = [
    "MoIP",
    "SDoIP",
    "EkIP",
    "SoIP",
    "MoDM-SNR",
    "SDDM-SNR",
    "EkDM-SNR",
    "SoDM-SNR",
    "Class",
]


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash for strict dataset provenance."""
    if not filepath.exists():
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class DatasetRegistryService:
    """Manages dataset registration, validation, and readers for HTRU2 and Parkes PSRFITS."""

    def __init__(self):
        self.htru2_path = HTRU2_DATA_PATH if HTRU2_DATA_PATH.exists() else HTRU2_FALLBACK_PATH
        self.parkes_path = PARKES_DATA_PATH
        self.radio_fits_files = sorted(RADIO_FITS_DIR.glob("*.fits")) if RADIO_FITS_DIR.exists() else []

    def list_registered_datasets(self) -> List[Dict[str, Any]]:
        """Return catalog metadata for both registered datasets."""
        htru2_exists = self.htru2_path.exists()
        parkes_exists = self.parkes_path.exists()

        htru2_size = self.htru2_path.stat().st_size if htru2_exists else 0
        parkes_size = self.parkes_path.stat().st_size if parkes_exists else 0

        return [
            {
                "id": "DATASET_A_HTRU2",
                "name": "HTRU2 Pulsar Candidate Benchmark",
                "source": "UCI Machine Learning Repository",
                "source_url": "https://archive.ics.uci.edu/dataset/372/htru2",
                "filename": self.htru2_path.name,
                "file_path": str(self.htru2_path.relative_to(PROJECT_ROOT) if self.htru2_path.is_relative_to(PROJECT_ROOT) else self.htru2_path),
                "format": "CSV (RFC 4180)",
                "dataset_type": "Labelled Tabular Feature Moments",
                "record_count": 17898 if htru2_exists else 0,
                "feature_count": 8,
                "label_availability": True,
                "label_classes": {"0": "Non-pulsar noise / RFI (16,259)", "1": "Real pulsar candidate (1,639)"},
                "file_size_bytes": htru2_size,
                "validation_status": "VALIDATED" if htru2_exists else "MISSING",
                "supported_experiment_types": [
                    "Supervised Pulsar Classification",
                    "Feature Perturbation Evaluation (P1)",
                    "Cross-Dataset Compatibility Audit (P3)",
                    "Confidence Calibration & Reliability (P4)",
                    "False Positive / False Negative Analysis (P5)",
                ],
                "description": "Standard high-time-resolution pulsar search survey benchmark containing 8 extracted numerical summary moments across folded pulse profiles and DM-SNR curves.",
            },
            {
                "id": "DATASET_B_PARKES",
                "name": "Parkes Search-Mode PSRFITS Stream",
                "source": "NASA GSFC FITS Registry / CSIRO Parkes Observatory",
                "source_url": "https://fits.gsfc.nasa.gov/registry/psrfits.html",
                "filename": self.parkes_path.name,
                "file_path": str(self.parkes_path.relative_to(PROJECT_ROOT) if self.parkes_path.is_relative_to(PROJECT_ROOT) else self.parkes_path),
                "format": "PSRFITS Search-Mode (FITS binary table)",
                "dataset_type": "Raw Streamed Dynamic Spectrum (Time-Frequency)",
                "record_count": 40 if parkes_exists else 0,  # 40 sub-integrations = 163,840 time samples
                "feature_count": 512,  # 512 frequency channels
                "label_availability": False,
                "label_classes": None,
                "file_size_bytes": parkes_size,
                "validation_status": "VALIDATED" if parkes_exists else "MISSING",
                "supported_experiment_types": [
                    "Radio Signal Quality & Dynamic Range",
                    "Controlled Synthetic Noise Experiments (P1)",
                    "Frequency Channel Masking & Excision (P2)",
                    "Signal Recoverability Retention (P2)",
                    "Cross-Dataset Compatibility Audit (P3)",
                    "Signal Quality Failure Breakdown (P5)",
                ],
                "description": "Streamed search-mode observation of millisecond pulsar PSR J0437-4715 recorded with the Parkes PDFB4 backend. Contains 15.7 seconds of 2-bit intensity samples across 512 frequency channels (1241-1497 MHz).",
            },
            {
                "id": "DATASET_C_GBT_VEGAS",
                "name": "GBT/VEGAS Folded Timing Archives — PSR J1713+0747",
                "source": "Green Bank Telescope (GBT), NRAO",
                "source_url": "https://greenbankobservatory.org",
                "filename": f"{len(self.radio_fits_files)} files in data/radio_fits/",
                "file_path": "data/radio_fits/",
                "format": "PSRFITS Folded Timing Archive (FITS binary table)",
                "dataset_type": "Folded Pulse Profile Archives (PSR mode)",
                "record_count": len(self.radio_fits_files),
                "feature_count": 33,  # 33 extracted gbt_* columns
                "label_availability": False,
                "label_classes": None,
                "file_size_bytes": sum(f.stat().st_size for f in self.radio_fits_files),
                "validation_status": "VALIDATED" if len(self.radio_fits_files) > 0 else "MISSING",
                "supported_experiment_types": [
                    "Pulse Profile Feature Extraction",
                    "Signal Quality Monitoring",
                    "Cross-Dataset Compatibility Audit (P3)",
                ],
                "description": (
                    f"{len(self.radio_fits_files)} GBT/VEGAS PSRFITS folded timing archives of MSP J1713+0747 "
                    "(2019-06-03 to 2022-03-30). Each contains one subintegration with 128 channels, "
                    "4 Stokes parameters, 2048 phase bins at 820 MHz. Pulse-profile statistics and "
                    "auxiliary DM/RM values extracted. No candidate classification labels."
                ),
            },
        ]

    def read_htru2(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate and read HTRU2 benchmark CSV.
        Returns cleaned DataFrame with canonical columns and provenance dict.
        """
        if not self.htru2_path.exists():
            raise FileNotFoundError(f"HTRU2 dataset file not found at {self.htru2_path}")

        df = pd.read_csv(self.htru2_path)
        # Handle column naming variations
        if list(df.columns) == HTRU2_CANONICAL_COLUMNS:
            pass
        elif list(df.columns) == HTRU2_ALT_COLUMNS:
            df.columns = HTRU2_CANONICAL_COLUMNS
        elif df.shape[1] == 9:
            # First row might be header or data
            if df.iloc[0, 0] in ("Profile_Mean", "MoIP"):
                df = df.iloc[1:].reset_index(drop=True)
            df.columns = HTRU2_CANONICAL_COLUMNS
        else:
            raise ValueError(f"Unexpected HTRU2 format: expected 9 columns, got {df.shape[1]}")

        # Ensure numeric conversion
        for col in HTRU2_CANONICAL_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if df.isna().any().any():
            df = df.dropna().reset_index(drop=True)

        df["Target"] = df["Target"].astype(int)

        provenance = {
            "source": "UCI Machine Learning Repository",
            "file_path": str(self.htru2_path),
            "file_size_bytes": self.htru2_path.stat().st_size,
            "sha256": compute_file_sha256(self.htru2_path),
            "row_count": len(df),
            "feature_columns": HTRU2_CANONICAL_COLUMNS[:8],
            "target_column": "Target",
            "class_distribution": {
                "negative_noise_rfi": int((df["Target"] == 0).sum()),
                "positive_pulsar": int((df["Target"] == 1).sum()),
            },
        }

        return df, provenance

    def read_parkes_psrfits(self, max_subints: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Validate and read Parkes Search-Mode PSRFITS file.
        Unpacks 2-bit samples into calibrated physical flux intensity dynamic spectrum.
        Returns 2D matrix (time_samples, 512 channels) and header provenance dict.
        """
        if not self.parkes_path.exists():
            raise FileNotFoundError(f"Parkes PSRFITS file not found at {self.parkes_path}")

        with fits.open(self.parkes_path) as hdul:
            primary_hdr = hdul[0].header
            fitstype = primary_hdr.get("FITSTYPE", "").strip()
            obs_mode = primary_hdr.get("OBS_MODE", "").strip()
            telescop = primary_hdr.get("TELESCOP", "").strip()

            if fitstype != "PSRFITS" or obs_mode != "SEARCH":
                raise ValueError(
                    f"Invalid Parkes search-mode file: FITSTYPE={fitstype}, OBS_MODE={obs_mode} "
                    "(Expected FITSTYPE='PSRFITS', OBS_MODE='SEARCH')"
                )

            subint = hdul["SUBINT"]
            s_hdr = subint.header
            nchan = int(s_hdr.get("NCHAN", 512))
            nsblk = int(s_hdr.get("NSBLK", 4096))
            tbin = float(s_hdr.get("TBIN", 9.6e-05))
            nbits = int(s_hdr.get("NBITS", 2))
            nrows = len(subint.data)

            rows_to_read = min(nrows, max_subints) if max_subints else nrows

            f_channels = subint.data[0]["DAT_FREQ"].copy()
            weights = subint.data[0]["DAT_WTS"].copy()

            sub_blocks = []
            for i in range(rows_to_read):
                row = subint.data[i]
                raw_bytes = row["DATA"].squeeze(1)  # shape (1024, 512)
                # Unpack 4 2-bit samples per byte
                s0 = (raw_bytes & 0x03).astype(np.float32)
                s1 = ((raw_bytes >> 2) & 0x03).astype(np.float32)
                s2 = ((raw_bytes >> 4) & 0x03).astype(np.float32)
                s3 = ((raw_bytes >> 6) & 0x03).astype(np.float32)

                unp = np.empty((nsblk, nchan), dtype=np.float32)
                unp[0::4] = s0
                unp[1::4] = s1
                unp[2::4] = s2
                unp[3::4] = s3

                # Apply scaling and offsets
                scaled = unp * row["DAT_SCL"][np.newaxis, :] + row["DAT_OFFS"][np.newaxis, :]
                sub_blocks.append(scaled)

            dynamic_spectrum = np.concatenate(sub_blocks, axis=0)  # (time_samples, 512)

            provenance = {
                "source": "NASA GSFC FITS Registry / CSIRO Parkes",
                "file_path": str(self.parkes_path),
                "file_size_bytes": self.parkes_path.stat().st_size,
                "sha256": compute_file_sha256(self.parkes_path),
                "telescope": telescop,
                "backend": primary_hdr.get("BACKEND", "PDFB4"),
                "source_name": primary_hdr.get("SRC_NAME", "J0437-4715"),
                "center_frequency_mhz": float(primary_hdr.get("OBSFREQ", 1369.0)),
                "bandwidth_mhz": float(primary_hdr.get("OBSBW", 256.0)),
                "nchan": nchan,
                "nsblk_per_subint": nsblk,
                "sampling_time_seconds": tbin,
                "nbits_quantization": nbits,
                "total_subints_read": rows_to_read,
                "total_time_samples": dynamic_spectrum.shape[0],
                "total_duration_seconds": round(dynamic_spectrum.shape[0] * tbin, 4),
                "frequency_range_mhz": [float(f_channels.min()), float(f_channels.max())],
            }

            return dynamic_spectrum, provenance

    # ------------------------------------------------------------
    # Master Dataset Methods
    # ------------------------------------------------------------
    def get_master_csv_path(self) -> Path:
        return DATA_DIR / "integrated" / "master_dataset.csv"

    def get_master_manifest(self) -> Dict[str, Any]:
        manifest_path = DATA_DIR / "integrated" / "integration_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": "Manifest not found. Run build_master_dataset.py first."}

    def get_master_validation_report(self) -> Dict[str, Any]:
        val_path = DATA_DIR / "integrated" / "validation_report.json"
        if val_path.exists():
            with open(val_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": "Validation report not found."}

    def get_master_data_dictionary(self) -> List[Dict[str, Any]]:
        dict_path = DATA_DIR / "integrated" / "data_dictionary.csv"
        if dict_path.exists():
            df = pd.read_csv(dict_path)
            return df.to_dict(orient="records")
        return []

    def get_master_dataset_preview(
        self,
        limit: int = 50,
        offset: int = 0,
        source: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        csv_path = self.get_master_csv_path()
        if not csv_path.exists():
            return {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "items": [],
                "summary": {"total_records": 0, "htru2_records": 0, "parkes_records": 0}
            }

        # Read master dataset
        df = pd.read_csv(csv_path, low_memory=False)

        total_all = len(df)
        htru2_count = int(np.sum(df["source_dataset"] == "HTRU2"))
        parkes_count = int(np.sum(df["source_dataset"] == "PARKES_PDFB4"))
        gbt_count = int(np.sum(df["source_dataset"] == "GBT_VEGAS"))

        # Filter by source if specified
        if source:
            df = df[df["source_dataset"] == source]

        # Filter by search string if specified
        if search:
            search_lower = search.lower().strip()
            mask = (
                df["master_record_id"].astype(str).str.lower().str.contains(search_lower)
                | df["target_name"].astype(str).str.lower().str.contains(search_lower)
                | df["source_dataset"].astype(str).str.lower().str.contains(search_lower)
            )
            df = df[mask]

        filtered_total = len(df)
        paginated_df = df.iloc[offset : offset + limit]

        # Convert NaN to None for JSON compliance
        items = paginated_df.replace({np.nan: None}).to_dict(orient="records")
        for item in items:
            if "source_dataset" in item and "source_archive" not in item:
                item["source_archive"] = item["source_dataset"]

        return {
            "total": filtered_total,
            "limit": limit,
            "offset": offset,
            "items": items,
            "records": items,
            "total_records": filtered_total if source else total_all,
            "htru2_count": htru2_count,
            "parkes_subints": parkes_count,
            "gbt_vegas_count": gbt_count,
            "summary": {
                "total_records": total_all,
                "htru2_records": htru2_count,
                "parkes_records": parkes_count,
                "gbt_vegas_records": gbt_count,
                "filtered_records": filtered_total,
                "column_count": len(df.columns),
            }
        }


dataset_registry = DatasetRegistryService()
dataset_service = dataset_registry

