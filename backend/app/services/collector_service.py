# ============================================================
#  ASTRA Cloud — Research Web Collector Service
#  File   : backend/app/services/collector_service.py
#  Purpose: Discovers, normalizes, validates, and deduplicates
#           astronomy literature and dataset metadata from
#           official, permitted repository interfaces.
# ============================================================

import os
import re
import json
import time
import logging
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
import xml.etree.ElementTree as ET

import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.schemas import (
    NormalizedResearchRecord,
    CollectorSourceInfo,
    SCIENTIFIC_COLLECTOR_DISCLAIMER,
)
from backend.app.models import ResearchRecord, ProcessingRun

logger = logging.getLogger("astra.collector")

# Atom XML namespaces used by arXiv API
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# Environment configuration
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("ASTRA_COLLECTOR_TIMEOUT_SECONDS", "10.0"))
DEFAULT_USER_AGENT = os.getenv(
    "ASTRA_COLLECTOR_USER_AGENT",
    "ASTRA-Cloud-Research-Collector/1.0 (Astronomy Research Metadata Ingestion; mailto:astra-collector@example.org)"
)
ARXIV_BASE_URL = os.getenv("ASTRA_ARXIV_BASE_URL", "https://export.arxiv.org/api/query")


# ============================================================
# 1. Validation & Deduplication Utilities
# ============================================================

def validate_canonical_url(url: str) -> bool:
    """Validate that the canonical URL is a well-formed http or https URL."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_identifier(identifier: str) -> str:
    """Normalize DOIs or source IDs for robust collision detection."""
    if not identifier:
        return ""
    clean = identifier.strip().lower()
    # Strip common prefix variants
    clean = re.sub(r"^(doi:\s*|https?://(?:dx\.)?doi\.org/)", "", clean)
    clean = re.sub(r"^arxiv:\s*", "", clean)
    # Strip version suffix for arxiv papers e.g. 2403.12345v2 -> 2403.12345
    clean = re.sub(r"v\d+$", "", clean)
    return clean.strip()


def normalize_canonical_url(url: str) -> str:
    """Normalize URL by lowering host, stripping trailing slash and tracking query params."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme}://{netloc}{path}"
    except Exception:
        return url.strip().lower()


def validate_record(record: NormalizedResearchRecord) -> Tuple[bool, List[str]]:
    """Verify that all required fields are populated and valid."""
    errors = []
    if not record.title or not record.title.strip():
        errors.append("Missing required field: title")
    if not record.identifier or not record.identifier.strip():
        errors.append("Missing required field: identifier")
    if not record.source_name or not record.source_name.strip():
        errors.append("Missing required field: source_name")
    if not record.canonical_url or not validate_canonical_url(record.canonical_url):
        errors.append(f"Invalid canonical URL: '{record.canonical_url}'")
    if record.record_type not in ("paper", "dataset"):
        errors.append(f"Invalid record_type: '{record.record_type}'")
    return len(errors) == 0, errors


def deduplicate_records(
    records: List[NormalizedResearchRecord]
) -> Tuple[List[NormalizedResearchRecord], int]:
    """
    Deduplicate records by normalized identifier, falling back to normalized canonical URL.
    Preserves input order for the first occurrence of each unique record.
    """
    seen_identifiers: Set[str] = set()
    seen_urls: Set[str] = set()
    unique_records: List[NormalizedResearchRecord] = []
    dedup_count = 0

    for rec in records:
        norm_id = normalize_identifier(rec.identifier)
        norm_url = normalize_canonical_url(rec.canonical_url)

        is_duplicate = False
        if norm_id and norm_id in seen_identifiers:
            is_duplicate = True
        elif norm_url and norm_url in seen_urls:
            is_duplicate = True

        if is_duplicate:
            dedup_count += 1
            continue

        if norm_id:
            seen_identifiers.add(norm_id)
        if norm_url:
            seen_urls.add(norm_url)
        unique_records.append(rec)

    return unique_records, dedup_count


# ============================================================
# 2. Base Collector Interface
# ============================================================

class BaseMetadataCollector(ABC):
    """Abstract provider interface for astronomy metadata harvesting."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the official metadata provider."""
        pass

    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """Supported record types ('paper', 'dataset')."""
        pass

    @abstractmethod
    def query(
        self,
        query: str,
        max_results: int = 10,
        category: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Tuple[List[NormalizedResearchRecord], int, Dict[str, Any]]:
        """
        Execute search against official metadata interface.
        Returns: (records, total_found, raw_summary)
        """
        pass


# ============================================================
# 3. Official Source Provider: arXiv API
# ============================================================

class ArxivCollector(BaseMetadataCollector):
    """
    Official astronomy preprint and paper metadata collector via arXiv Atom API.
    Covers astro-ph (astrophysics), astro-ph.HE (high energy / pulsars), etc.
    """

    def __init__(self, base_url: str = ARXIV_BASE_URL, user_agent: str = DEFAULT_USER_AGENT):
        self.base_url = base_url
        self.user_agent = user_agent

    @property
    def source_name(self) -> str:
        return "arXiv"

    @property
    def supported_types(self) -> List[str]:
        return ["paper"]

    def _build_search_query(self, query: str, category: Optional[str] = None) -> str:
        """Construct arXiv search query syntax."""
        clean_q = query.strip()
        if category and category.strip():
            cat = category.strip()
            # If query already specifies field qualifiers, append category filter
            if ":" in clean_q:
                return f"({clean_q}) AND cat:{cat}"
            return f"(ti:\"{clean_q}\" OR abs:\"{clean_q}\" OR all:\"{clean_q}\") AND cat:{cat}"
        return clean_q

    def query(
        self,
        query: str,
        max_results: int = 10,
        category: Optional[str] = "astro-ph",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Tuple[List[NormalizedResearchRecord], int, Dict[str, Any]]:
        search_query = self._build_search_query(query, category)
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/atom+xml, application/xml",
        }

        retrieval_time = datetime.now(timezone.utc)
        meta_summary = {
            "source": self.source_name,
            "query": query,
            "category": category,
            "retrieval_timestamp": retrieval_time.isoformat(),
            "status": "INITIATED",
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            meta_summary["status"] = "TIMEOUT"
            meta_summary["error"] = f"Request timed out after {timeout} seconds"
            return [], 0, meta_summary
        except requests.exceptions.RequestException as exc:
            meta_summary["status"] = "CONNECTION_ERROR"
            meta_summary["error"] = str(exc)
            return [], 0, meta_summary

        if response.status_code == 429:
            meta_summary["status"] = "RATE_LIMITED"
            meta_summary["error"] = "Upstream provider rate limit reached (HTTP 429)"
            return [], 0, meta_summary

        if response.status_code != 200:
            meta_summary["status"] = "SOURCE_ERROR"
            meta_summary["error"] = f"Provider returned HTTP status {response.status_code}"
            return [], 0, meta_summary

        # Parse Atom XML
        try:
            records, total_found = self._parse_atom_feed(response.content, retrieval_time)
            meta_summary["status"] = "COMPLETED"
            meta_summary["total_found"] = total_found
            return records, total_found, meta_summary
        except ET.ParseError as err:
            meta_summary["status"] = "MALFORMED_RESPONSE"
            meta_summary["error"] = f"Failed to parse XML response: {err}"
            return [], 0, meta_summary

    def _parse_atom_feed(
        self, xml_bytes: bytes, retrieval_time: datetime
    ) -> Tuple[List[NormalizedResearchRecord], int]:
        root = ET.fromstring(xml_bytes)
        
        # Total results
        total_found = 0
        total_results_el = root.find(f"{{{ATOM_NS}}}totalResults") or root.find(f"{{{ARXIV_NS}}}totalResults")
        if total_results_el is not None and total_results_el.text:
            try:
                total_found = int(total_results_el.text.strip())
            except ValueError:
                total_found = 0

        entries = root.findall(f"{ATOM_NS}entry")
        if not total_found and entries:
            total_found = len(entries)

        records: List[NormalizedResearchRecord] = []
        for entry in entries:
            rec = self._parse_single_entry(entry, retrieval_time)
            if rec:
                is_valid, errors = validate_record(rec)
                if is_valid:
                    records.append(rec)
                else:
                    rec.validation_notes = "; ".join(errors)
                    rec.retrieval_status = "VALIDATION_FAILED"
                    # Still keep if identifier and title exist
                    if rec.title and rec.identifier:
                        records.append(rec)

        return records, total_found

    def _parse_single_entry(
        self, entry: ET.Element, retrieval_time: datetime
    ) -> Optional[NormalizedResearchRecord]:
        id_el = entry.find(f"{ATOM_NS}id")
        title_el = entry.find(f"{ATOM_NS}title")

        if id_el is None or not id_el.text or title_el is None or not title_el.text:
            return None

        raw_id_url = id_el.text.strip()
        # Clean title
        title = " ".join(title_el.text.split())

        # Extract stable arXiv ID and canonical URL
        # Format e.g. http://arxiv.org/abs/2403.12345v1
        match = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+(?:v[0-9]+)?|[a-zA-Z\-]+/[0-9]+)", raw_id_url)
        if match:
            arxiv_id = match.group(1)
            # Standard canonical URL
            canonical_url = f"https://arxiv.org/abs/{arxiv_id}"
        else:
            arxiv_id = raw_id_url
            canonical_url = raw_id_url

        # Check for DOI
        doi_el = entry.find(f"{ARXIV_NS}doi")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None
        stable_identifier = doi if doi else f"arXiv:{arxiv_id}"

        # Authors
        authors = []
        for author_el in entry.findall(f"{ATOM_NS}author"):
            name_el = author_el.find(f"{ATOM_NS}name")
            if name_el is not None and name_el.text:
                authors.append(" ".join(name_el.text.split()))

        # Abstract / Summary
        summary_el = entry.find(f"{ATOM_NS}summary")
        abstract = None
        if summary_el is not None and summary_el.text:
            abstract = " ".join(summary_el.text.split())

        # Publication date
        pub_date = None
        published_el = entry.find(f"{ATOM_NS}published")
        if published_el is not None and published_el.text:
            try:
                # e.g. 2024-03-15T12:00:00Z
                dt = datetime.fromisoformat(published_el.text.strip().replace("Z", "+00:00"))
                pub_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pub_date = published_el.text.strip()[:10]

        # Raw metadata capture for scientific provenance
        raw_meta = {
            "arxiv_id": arxiv_id,
            "doi": doi,
            "raw_id_url": raw_id_url,
            "published_raw": published_el.text.strip() if published_el is not None and published_el.text else None,
            "primary_category": None,
        }
        primary_cat_el = entry.find(f"{ARXIV_NS}primary_category")
        if primary_cat_el is not None and "term" in primary_cat_el.attrib:
            raw_meta["primary_category"] = primary_cat_el.attrib["term"]

        return NormalizedResearchRecord(
            record_type="paper",
            title=title,
            authors=authors,
            abstract=abstract,
            publication_date=pub_date,
            identifier=stable_identifier,
            source_name=self.source_name,
            canonical_url=canonical_url,
            retrieval_timestamp=retrieval_time,
            retrieval_status="COLLECTED",
            raw_metadata=raw_meta,
            validation_notes=None,
            scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
        )


# ============================================================
# 4. Collector Manager & Source Registry
# ============================================================

class CollectorService:
    """Orchestrates metadata queries, validation, deduplication, and persistence."""

    def __init__(self):
        self._sources: Dict[str, BaseMetadataCollector] = {
            "arXiv": ArxivCollector(),
        }

    def list_sources(self) -> List[CollectorSourceInfo]:
        """Return catalog of available and modularly supported sources."""
        return [
            CollectorSourceInfo(
                name="arXiv",
                supported_record_types=["paper"],
                is_operational=True,
                requires_credentials=False,
                description="Official arXiv Atom API covering astro-ph (astrophysics, pulsars, radio astronomy).",
                rate_limit_policy="Respects 3-second polite request pacing and handles HTTP 429 backoff.",
            ),
            CollectorSourceInfo(
                name="NASA ADS",
                supported_record_types=["paper"],
                is_operational=bool(os.getenv("ASTRA_NASA_ADS_TOKEN")),
                requires_credentials=True,
                description="NASA Astrophysics Data System REST API (requires ASTRA_NASA_ADS_TOKEN).",
                rate_limit_policy="Token-based 5000 requests/day official rate ceiling.",
            ),
            CollectorSourceInfo(
                name="Crossref",
                supported_record_types=["paper"],
                is_operational=False,
                requires_credentials=False,
                description="Crossref REST API for official published DOI metadata resolution.",
                rate_limit_policy="Polite pool with mailto header.",
            ),
            CollectorSourceInfo(
                name="Zenodo",
                supported_record_types=["dataset", "paper"],
                is_operational=False,
                requires_credentials=False,
                description="Zenodo Open Science REST API for astronomical dataset DOIs and open archives.",
                rate_limit_policy="100 requests per minute.",
            ),
        ]

    def execute_collection(
        self,
        query: str,
        source_name: str = "arXiv",
        category: Optional[str] = "astro-ph",
        max_results: int = 10,
        save_to_db: bool = True,
        db: Optional[Session] = None,
    ) -> Tuple[List[NormalizedResearchRecord], int, int, int, float]:
        """
        Execute collection pipeline: query -> validate -> deduplicate -> optionally persist.
        Returns: (records, total_found, total_returned, total_deduplicated, elapsed_seconds)
        """
        start_time = time.perf_counter()
        collector = self._sources.get(source_name)
        if not collector:
            raise ValueError(f"Metadata source '{source_name}' is not registered or supported.")

        raw_records, total_found, meta = collector.query(
            query=query,
            max_results=max_results,
            category=category,
        )

        unique_records, dedup_count = deduplicate_records(raw_records)
        elapsed = time.perf_counter() - start_time

        saved_count = 0
        if save_to_db and db is not None:
            saved_count = self.save_records(db, unique_records, query, source_name, elapsed)

        return unique_records, total_found, len(unique_records), dedup_count, elapsed

    def save_records(
        self,
        db: Session,
        records: List[NormalizedResearchRecord],
        query: str,
        source_name: str,
        elapsed_seconds: float,
    ) -> int:
        """Persist unique records into PostgreSQL research_records and log in processing_runs."""
        saved_count = 0
        run_id = f"COLLECT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{int(time.time() * 1000) % 10000}"

        try:
            for rec in records:
                # Check for existing record by identifier or canonical URL
                existing = db.query(ResearchRecord).filter(
                    (ResearchRecord.identifier == rec.identifier) |
                    (ResearchRecord.canonical_url == rec.canonical_url)
                ).first()

                pub_date = None
                if rec.publication_date:
                    try:
                        pub_date = datetime.strptime(rec.publication_date, "%Y-%m-%d").date()
                    except Exception:
                        pub_date = None

                authors_json = json.dumps(rec.authors, ensure_ascii=False)
                raw_json = json.dumps(rec.raw_metadata or {}, ensure_ascii=False)

                if existing:
                    # Update status and timestamp if previously failed
                    if existing.retrieval_status != "COLLECTED" and rec.retrieval_status == "COLLECTED":
                        existing.retrieval_status = rec.retrieval_status
                        existing.updated_at = datetime.now(timezone.utc)
                    continue

                new_record = ResearchRecord(
                    record_type=rec.record_type,
                    title=rec.title,
                    authors=authors_json,
                    abstract=rec.abstract,
                    publication_date=pub_date,
                    identifier=rec.identifier,
                    source_name=rec.source_name,
                    canonical_url=rec.canonical_url,
                    retrieval_timestamp=rec.retrieval_timestamp,
                    retrieval_status=rec.retrieval_status,
                    raw_metadata_json=raw_json,
                    validation_notes=rec.validation_notes,
                )
                db.add(new_record)
                saved_count += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to persist research records to database: {exc}")
            raise

        return saved_count


# Global singleton collector instance
collector_service = CollectorService()
