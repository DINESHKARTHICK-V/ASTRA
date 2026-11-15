// ============================================================
//  ASTRA — Research Sources Page
//  File   : frontend/src/pages/ResearchSourcesPage.tsx
//  Purpose: Browse collected research records, view extraction
//           details with provenance, inspect the comparative
//           literature synthesis, and trigger new collection.
//  Rules  : Uses existing design-system CSS variables only.
//           Does not install new dependencies or frameworks.
//           Prevents concurrent collection jobs via local flag.
//           Distinguishes grounded facts from inferences.
// ============================================================

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  ResearchRecord,
  PaperExtractionResponse,
  LiteratureComparisonResponse,
  CollectorSource,
} from '../types/api';

// ─── Sub-view tabs ───────────────────────────────────────────
type ViewTab = 'papers' | 'comparison' | 'sources';

// ─── Helpers ─────────────────────────────────────────────────
const NA = 'Not available in retrieved source';
const isNA = (v: string | null | undefined) =>
  !v || v.trim() === '' || v === NA;

function Badge({
  label,
  color,
}: {
  label: string;
  color: 'blue' | 'purple' | 'green' | 'amber' | 'red' | 'slate';
}) {
  const map: Record<string, string> = {
    blue: 'var(--primary)',
    purple: 'var(--accent-purple)',
    green: 'var(--success)',
    amber: 'var(--warning)',
    red: 'var(--danger)',
    slate: 'var(--text-dim)',
  };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 8px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        background: `${map[color]}22`,
        color: map[color],
        border: `1px solid ${map[color]}55`,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

function Spinner() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 14,
        height: 14,
        border: '2px solid var(--border-active)',
        borderTopColor: 'var(--primary)',
        borderRadius: '50%',
        animation: 'rs-spin 0.7s linear infinite',
        verticalAlign: 'middle',
        marginRight: 6,
      }}
    />
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '48px 24px',
        textAlign: 'center',
        color: 'var(--text-dim)',
        fontSize: 14,
      }}
    >
      <div style={{ fontSize: 32, marginBottom: 12 }}>🔭</div>
      <div>{message}</div>
    </div>
  );
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div
      style={{
        background: '#ef444422',
        border: '1px solid #ef444455',
        borderRadius: 8,
        padding: '10px 14px',
        color: '#fca5a5',
        fontSize: 13,
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
      }}
    >
      <span style={{ flexShrink: 0 }}>⚠️</span>
      <span style={{ flex: 1 }}>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#fca5a5',
            cursor: 'pointer',
            fontSize: 16,
            lineHeight: 1,
            padding: 0,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}

function Disclaimer({ text }: { text: string }) {
  return (
    <div
      style={{
        background: '#f59e0b11',
        border: '1px solid #f59e0b44',
        borderRadius: 8,
        padding: '8px 12px',
        color: 'var(--warning)',
        fontSize: 11,
        lineHeight: 1.6,
        marginTop: 4,
      }}
    >
      ⚠️ {text}
    </div>
  );
}

// ─── Record Detail Drawer ─────────────────────────────────────
interface RecordDrawerProps {
  record: ResearchRecord;
  onClose: () => void;
}

const RecordDrawer: React.FC<RecordDrawerProps> = ({ record, onClose }) => {
  const [extraction, setExtraction] = useState<PaperExtractionResponse | null>(null);
  const [extLoading, setExtLoading] = useState(false);
  const [extError, setExtError] = useState<string | null>(null);

  useEffect(() => {
    setExtraction(null);
    setExtError(null);
    setExtLoading(true);
    apiService
      .getRecordExtraction(record.id)
      .then(setExtraction)
      .catch((e) =>
        setExtError(e instanceof ApiError ? e.message : 'Failed to load extraction.')
      )
      .finally(() => setExtLoading(false));
  }, [record.id]);

  const det = extraction?.extracted_details;
  const prov = extraction?.provenance ?? {};

  return (
    <div
      id={`research-record-drawer-${record.id}`}
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 560,
        background: 'var(--bg-card)',
        borderLeft: '1px solid var(--border-subtle)',
        zIndex: 200,
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        boxShadow: '-8px 0 40px #00000080',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          gap: 12,
          alignItems: 'flex-start',
          position: 'sticky',
          top: 0,
          background: 'var(--bg-card)',
          zIndex: 10,
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
            <Badge label={record.record_type.toUpperCase()} color="blue" />
            <Badge label={record.source_name} color="purple" />
            <Badge
              label={record.retrieval_status}
              color={record.retrieval_status === 'ok' ? 'green' : 'red'}
            />
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.4 }}>
            {record.title}
          </div>
          {record.authors.length > 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              {record.authors.slice(0, 5).join(', ')}
              {record.authors.length > 5 && ` +${record.authors.length - 5} more`}
            </div>
          )}
        </div>
        <button
          id={`close-drawer-${record.id}`}
          onClick={onClose}
          style={{
            background: 'none',
            border: '1px solid var(--border-subtle)',
            borderRadius: 6,
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: '4px 8px',
            flexShrink: 0,
          }}
        >
          ×
        </button>
      </div>

      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Metadata table */}
        <section>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text-dim)',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            Metadata
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              <tr>
                <td style={{ color: 'var(--text-dim)', paddingBottom: 4, paddingRight: 12, whiteSpace: 'nowrap', verticalAlign: 'top' }}>Identifier</td>
                <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12, wordBreak: 'break-all' }}>{record.identifier}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', paddingBottom: 4, paddingRight: 12, whiteSpace: 'nowrap', verticalAlign: 'top' }}>Published</td>
                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{record.publication_date ?? 'Unknown'}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', paddingBottom: 4, paddingRight: 12, whiteSpace: 'nowrap', verticalAlign: 'top' }}>Retrieved</td>
                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(record.retrieval_timestamp).toLocaleString()}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', paddingBottom: 4, paddingRight: 12, whiteSpace: 'nowrap', verticalAlign: 'top' }}>Source URL</td>
                <td>
                  <a
                    href={record.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary)', wordBreak: 'break-all', fontSize: 12 }}
                  >
                    {record.canonical_url}
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Abstract */}
        {record.abstract && !isNA(record.abstract) && (
          <section>
            <div
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: 'var(--text-dim)',
                textTransform: 'uppercase',
                letterSpacing: 1,
                marginBottom: 6,
              }}
            >
              Abstract
            </div>
            <div
              style={{
                fontSize: 13,
                color: 'var(--text-muted)',
                lineHeight: 1.65,
                background: 'var(--bg-space)',
                borderRadius: 6,
                padding: '10px 12px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {record.abstract}
            </div>
          </section>
        )}

        {/* Extraction */}
        <section>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text-dim)',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            Extracted Details
            {det?.is_inferred && (
              <span style={{ color: 'var(--warning)', marginLeft: 8, fontSize: 10, fontWeight: 400 }}>
                (pattern-inferred — verify manually)
              </span>
            )}
          </div>

          {extLoading && (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              <Spinner /> Loading extraction…
            </div>
          )}
          {extError && <ErrorBanner message={extError} />}

          {!extLoading && !extError && det && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
              {(
                [
                  ['Research Problem', det.research_problem],
                  ['Dataset Name', det.dataset_name],
                  ['Dataset Type', det.dataset_type],
                  ['Main Findings', det.main_reported_findings],
                  ['Stated Limitations', det.stated_limitations],
                  ['Full-text Availability', det.full_text_availability],
                  ['Licence / Access', det.licence_or_access_status],
                ] as [string, string][]
              ).map(([label, value]) => (
                <div key={label}>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 2 }}>{label}</div>
                  <div
                    style={{
                      color: isNA(value) ? 'var(--text-dim)' : 'var(--text-muted)',
                      fontStyle: isNA(value) ? 'italic' : 'normal',
                      lineHeight: 1.5,
                    }}
                  >
                    {value || NA}
                  </div>
                </div>
              ))}

              {det.algorithms_or_models.length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 4 }}>Algorithms / Models</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {det.algorithms_or_models.map((a, i) => (
                      <Badge key={i} label={a} color="blue" />
                    ))}
                  </div>
                </div>
              )}

              {det.evaluation_metrics.length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 4 }}>Evaluation Metrics</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {det.evaluation_metrics.map((m, i) => (
                      <Badge key={i} label={m} color="green" />
                    ))}
                  </div>
                </div>
              )}

              {det.feature_types.length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 4 }}>Feature Types</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {det.feature_types.map((f, i) => (
                      <Badge key={i} label={f} color="purple" />
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(det.evidence_locations).length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 4 }}>Evidence Locations</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <tbody>
                      {Object.entries(det.evidence_locations).map(([field, loc]) => (
                        <tr key={field}>
                          <td style={{ color: 'var(--text-dim)', paddingRight: 10, paddingBottom: 2, verticalAlign: 'top' }}>{field}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{loc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {Object.keys(prov).length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginBottom: 4 }}>Provenance</div>
                  <pre
                    style={{
                      background: 'var(--bg-space)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 6,
                      padding: '8px 10px',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-dim)',
                      maxHeight: 120,
                      overflowY: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                    }}
                  >
                    {JSON.stringify(prov, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>

        {extraction?.scientific_disclaimer && (
          <Disclaimer text={extraction.scientific_disclaimer} />
        )}
      </div>
    </div>
  );
};

// ─── Papers Tab ───────────────────────────────────────────────
const PapersTab: React.FC = () => {
  const [records, setRecords] = useState<ResearchRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<ResearchRecord | null>(null);

  const [searchQ, setSearchQ] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const [collectQuery, setCollectQuery] = useState('');
  const [collectMax, setCollectMax] = useState(10);
  const [collecting, setCollecting] = useState(false);
  const collectingRef = useRef(false);
  const [collectResult, setCollectResult] = useState<string | null>(null);
  const [collectError, setCollectError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.listResearchRecords({
        q: searchQ || undefined,
        source: sourceFilter || undefined,
        record_type: typeFilter || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setRecords(res.items);
      setTotal(res.total);
      setDisclaimer(res.scientific_disclaimer);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load records.');
    } finally {
      setLoading(false);
    }
  }, [searchQ, sourceFilter, typeFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCollect = async () => {
    if (collectingRef.current) return;
    if (!collectQuery.trim()) {
      setCollectError('Query is required.');
      return;
    }
    collectingRef.current = true;
    setCollecting(true);
    setCollectResult(null);
    setCollectError(null);
    try {
      const res = await apiService.queryCollector({
        query: collectQuery.trim(),
        source: 'arXiv',
        max_results: collectMax,
        save_to_db: true,
      });
      setCollectResult(
        `✓ Retrieved ${res.total_returned} records (${res.total_deduplicated} deduplicated) in ${res.execution_seconds}s.`
      );
      setCollectQuery('');
      load();
    } catch (e) {
      setCollectError(e instanceof ApiError ? e.message : 'Collection failed.');
    } finally {
      collectingRef.current = false;
      setCollecting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Collection Panel */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 10,
          padding: '16px 18px',
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)', marginBottom: 12 }}>
          🔍 Collect from arXiv
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            id="collector-query-input"
            type="text"
            value={collectQuery}
            onChange={(e) => setCollectQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCollect()}
            placeholder="e.g. pulsar RFI detection machine learning"
            disabled={collecting}
            style={{
              flex: 1,
              minWidth: 220,
              background: 'var(--bg-input)',
              border: '1px solid var(--border-active)',
              borderRadius: 6,
              color: 'var(--text-main)',
              padding: '7px 10px',
              fontSize: 13,
              outline: 'none',
            }}
          />
          <select
            id="collector-max-results"
            value={collectMax}
            onChange={(e) => setCollectMax(Number(e.target.value))}
            disabled={collecting}
            style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--border-active)',
              borderRadius: 6,
              color: 'var(--text-main)',
              padding: '7px 10px',
              fontSize: 13,
            }}
          >
            {[5, 10, 20, 50].map((n) => (
              <option key={n} value={n}>{n} results</option>
            ))}
          </select>
          <button
            id="collector-run-btn"
            onClick={handleCollect}
            disabled={collecting}
            style={{
              background: collecting ? 'var(--border-active)' : 'var(--primary)',
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              cursor: collecting ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: 13,
              padding: '7px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            {collecting && <Spinner />}
            {collecting ? 'Collecting…' : 'Collect'}
          </button>
        </div>
        {collectResult && (
          <div style={{ marginTop: 8, color: 'var(--success)', fontSize: 12 }}>{collectResult}</div>
        )}
        {collectError && (
          <div style={{ marginTop: 8 }}>
            <ErrorBanner message={collectError} onDismiss={() => setCollectError(null)} />
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          id="research-search-input"
          type="text"
          value={searchQ}
          onChange={(e) => { setSearchQ(e.target.value); setPage(0); }}
          placeholder="Search title / abstract / DOI…"
          style={{
            flex: 1,
            minWidth: 200,
            background: 'var(--bg-input)',
            border: '1px solid var(--border-active)',
            borderRadius: 6,
            color: 'var(--text-main)',
            padding: '7px 10px',
            fontSize: 13,
          }}
        />
        <select
          id="research-source-filter"
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(0); }}
          style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-active)',
            borderRadius: 6,
            color: 'var(--text-main)',
            padding: '7px 10px',
            fontSize: 13,
          }}
        >
          <option value="">All Sources</option>
          <option value="arXiv">arXiv</option>
        </select>
        <select
          id="research-type-filter"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}
          style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-active)',
            borderRadius: 6,
            color: 'var(--text-main)',
            padding: '7px 10px',
            fontSize: 13,
          }}
        >
          <option value="">All Types</option>
          <option value="paper">Papers</option>
          <option value="dataset">Datasets</option>
        </select>
        <button
          id="research-refresh-btn"
          onClick={load}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-active)',
            borderRadius: 6,
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '7px 12px',
            fontSize: 13,
          }}
        >
          ↺ Refresh
        </button>
        <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>
          {loading ? 'Loading…' : `${total} records`}
        </span>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {!loading && records.length === 0 && !error && (
        <EmptyState message="No research records collected yet. Use the panel above to collect papers from arXiv." />
      )}

      {records.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border-subtle)' }}>
                {['Type', 'Title', 'Authors', 'Published', 'Source', 'Status', ''].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: '8px 12px',
                      textAlign: 'left',
                      color: 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: 11,
                      textTransform: 'uppercase',
                      letterSpacing: 0.5,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.id}
                  style={{ borderBottom: '1px solid var(--border-subtle)', cursor: 'pointer' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                    <Badge label={r.record_type} color="blue" />
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-main)', maxWidth: 320 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.title}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      {r.identifier}
                    </div>
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)', maxWidth: 180 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.authors.slice(0, 3).join(', ')}
                      {r.authors.length > 3 && ` +${r.authors.length - 3}`}
                    </div>
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {r.publication_date ?? '—'}
                  </td>
                  <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                    <Badge label={r.source_name} color="purple" />
                  </td>
                  <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                    <Badge
                      label={r.retrieval_status}
                      color={r.retrieval_status === 'ok' ? 'green' : 'amber'}
                    />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <button
                      id={`view-record-${r.id}`}
                      onClick={() => setSelectedRecord(r)}
                      style={{
                        background: 'var(--bg-active)',
                        border: '1px solid var(--primary)55',
                        borderRadius: 5,
                        color: 'var(--primary)',
                        cursor: 'pointer',
                        fontSize: 12,
                        padding: '3px 10px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      View →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'flex-end' }}>
          <button
            id="research-prev-page"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-active)',
              borderRadius: 5,
              color: 'var(--text-muted)',
              cursor: page === 0 ? 'not-allowed' : 'pointer',
              padding: '5px 12px',
              fontSize: 13,
            }}
          >
            ← Prev
          </button>
          <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>
            Page {page + 1} / {totalPages}
          </span>
          <button
            id="research-next-page"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-active)',
              borderRadius: 5,
              color: 'var(--text-muted)',
              cursor: page >= totalPages - 1 ? 'not-allowed' : 'pointer',
              padding: '5px 12px',
              fontSize: 13,
            }}
          >
            Next →
          </button>
        </div>
      )}

      {disclaimer && <Disclaimer text={disclaimer} />}

      {selectedRecord && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, background: '#00000060', zIndex: 199 }}
            onClick={() => setSelectedRecord(null)}
          />
          <RecordDrawer record={selectedRecord} onClose={() => setSelectedRecord(null)} />
        </>
      )}
    </div>
  );
};

// ─── Comparison Tab ───────────────────────────────────────────
const ComparisonTab: React.FC = () => {
  const [data, setData] = useState<LiteratureComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const triggeringRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiService.getLatestComparison());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load comparison.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleTrigger = async () => {
    if (triggeringRef.current) return;
    triggeringRef.current = true;
    setTriggering(true);
    setError(null);
    try {
      setData(await apiService.triggerComparison());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Comparison generation failed.');
    } finally {
      triggeringRef.current = false;
      setTriggering(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: 13, flex: 1 }}>
          {data
            ? `Last generated: ${new Date(data.generated_at).toLocaleString()} — ${data.total_papers_compared} papers compared`
            : 'No comparison generated yet.'}
        </div>
        <button
          id="comparison-refresh-btn"
          onClick={load}
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border-active)', borderRadius: 6, color: 'var(--text-muted)', cursor: 'pointer', padding: '7px 12px', fontSize: 13 }}
        >
          ↺ Reload
        </button>
        <button
          id="comparison-trigger-btn"
          onClick={handleTrigger}
          disabled={triggering}
          style={{
            background: triggering ? 'var(--border-active)' : 'var(--primary)',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            cursor: triggering ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 13,
            padding: '7px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          {triggering && <Spinner />}
          {triggering ? 'Generating…' : '⚡ Regenerate'}
        </button>
      </div>

      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}><Spinner /> Loading…</div>}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {!loading && !data && !error && (
        <EmptyState message="No comparison report. Collect papers then click Regenerate." />
      )}

      {data && (
        <>
          {data.comparison_table.length > 0 && (
            <section>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)', marginBottom: 10 }}>
                📊 Comparison Table ({data.comparison_table.length} papers)
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 900 }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Title', 'Research Problem', 'Data Source', 'Algorithm', 'Metrics', 'Main Result', 'Limitations', 'ASTRA Relevance'].map((h) => (
                        <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--text-dim)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.comparison_table.map((row, i) => (
                      <tr
                        key={i}
                        style={{ borderBottom: '1px solid var(--border-subtle)' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        {[
                          row.title, row.research_problem, row.data_source,
                          row.algorithm_or_method, row.evaluation_metrics,
                          row.main_result, row.limitations, row.astra_relevance,
                        ].map((cell, j) => (
                          <td
                            key={j}
                            style={{
                              padding: '6px 10px',
                              color: isNA(cell) ? 'var(--text-dim)' : 'var(--text-muted)',
                              fontStyle: isNA(cell) ? 'italic' : 'normal',
                              maxWidth: 200,
                              verticalAlign: 'top',
                            }}
                          >
                            <div
                              style={{
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                display: '-webkit-box',
                                WebkitLineClamp: 3,
                                WebkitBoxOrient: 'vertical',
                              }}
                            >
                              {cell || NA}
                            </div>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {data.research_gap_candidates.length > 0 && (
            <section>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)', marginBottom: 10 }}>
                🔎 Research Gap Candidates
              </div>
              {data.research_gap_candidates.map((g, i) => (
                <div key={i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '12px 14px', marginBottom: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, color: 'var(--text-main)', fontSize: 13 }}>{g.candidate_gap}</div>
                    <Badge label={g.confidence} color={g.confidence === 'low' ? 'amber' : g.confidence === 'medium' ? 'blue' : 'green'} />
                    {g.human_verification_required && <Badge label="Verify manually" color="amber" />}
                  </div>
                  {g.supporting_papers.length > 0 && (
                    <div style={{ marginTop: 6, color: 'var(--text-dim)', fontSize: 11 }}>
                      Supporting: {g.supporting_papers.join(' · ')}
                    </div>
                  )}
                  {g.provenance_note && (
                    <div style={{ marginTop: 4, color: 'var(--text-dim)', fontSize: 11, fontStyle: 'italic' }}>
                      {g.provenance_note}
                    </div>
                  )}
                </div>
              ))}
            </section>
          )}

          {data.conflicting_or_incomparable_setups.length > 0 && (
            <section>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)', marginBottom: 8 }}>
                ⚡ Conflicting or Incomparable Setups
              </div>
              {data.conflicting_or_incomparable_setups.map((c, i) => (
                <div key={i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '10px 14px', marginBottom: 8, fontSize: 13 }}>
                  <div style={{ color: 'var(--text-main)' }}>{c.description}</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginTop: 4 }}>
                    Type: {c.conflict_type} · Papers: {c.papers_involved.join(', ')}
                  </div>
                </div>
              ))}
            </section>
          )}

          {data.manual_verification_items.length > 0 && (
            <section>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)', marginBottom: 8 }}>
                📋 Requires Manual Verification
              </div>
              {data.manual_verification_items.map((m, i) => (
                <div key={i} style={{ background: 'var(--bg-card)', border: '1px solid #f59e0b33', borderRadius: 8, padding: '10px 14px', marginBottom: 8, fontSize: 13 }}>
                  <div style={{ color: 'var(--text-main)' }}>{m.item}</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 11, marginTop: 4 }}>
                    Reason: {m.reason} · Papers: {m.related_papers.join(', ')}
                  </div>
                </div>
              ))}
            </section>
          )}

          <Disclaimer text={data.coverage_warning || data.scientific_disclaimer} />
        </>
      )}
    </div>
  );
};

// ─── Sources Tab ──────────────────────────────────────────────
const SourcesTab: React.FC = () => {
  const [sources, setSources] = useState<CollectorSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    apiService
      .listCollectorSources()
      .then(setSources)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load sources.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}><Spinner /> Loading…</div>}
      {error && <ErrorBanner message={error} />}
      {!loading && sources.length === 0 && !error && <EmptyState message="No sources configured." />}
      {sources.map((s) => (
        <div
          key={s.name}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 10,
            padding: '14px 18px',
          }}
        >
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-main)' }}>{s.name}</span>
            <Badge label={s.status} color={s.status === 'active' ? 'green' : s.status === 'planned' ? 'amber' : 'red'} />
            {s.supported_record_types.map((t) => (
              <Badge key={t} label={t} color="blue" />
            ))}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 6 }}>{s.description}</div>
          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-dim)', flexWrap: 'wrap' }}>
            <span>
              🔗{' '}
              <a href={s.base_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)' }}>
                {s.base_url}
              </a>
            </span>
            <span>⏱ {s.rate_limit_note}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────
export const ResearchSourcesPage: React.FC = () => {
  const [activeView, setActiveView] = useState<ViewTab>('papers');

  const tabs: { id: ViewTab; label: string; icon: string }[] = [
    { id: 'papers', label: 'Papers & Records', icon: '📄' },
    { id: 'comparison', label: 'Comparison', icon: '📊' },
    { id: 'sources', label: 'Sources', icon: '🛰️' },
  ];

  return (
    <div className="page-container" style={{ maxWidth: 1200 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-main)', marginBottom: 4 }}>
          Research Sources
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Collect and browse peer-reviewed astronomy literature via official metadata interfaces.
          Extracted methods and metrics reflect the available abstract only — full-text claims require manual verification.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border-subtle)', marginBottom: 20 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            id={`research-tab-${t.id}`}
            onClick={() => setActiveView(t.id)}
            style={{
              background: activeView === t.id ? 'var(--bg-active)' : 'transparent',
              border: 'none',
              borderBottom: activeView === t.id ? '2px solid var(--primary)' : '2px solid transparent',
              color: activeView === t.id ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeView === t.id ? 600 : 400,
              padding: '8px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {activeView === 'papers' && <PapersTab />}
      {activeView === 'comparison' && <ComparisonTab />}
      {activeView === 'sources' && <SourcesTab />}

      <style>{`@keyframes rs-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};
