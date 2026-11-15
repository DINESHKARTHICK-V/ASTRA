import React, { useState } from 'react';

export interface ExplanationMetricRow {
  condition: string;
  baseline: string | number;
  experimental: string | number;
  change: string | number;
  interpretation?: string;
}

export interface ResearchExplanationPanelProps {
  problemId: string;
  title: string;
  subtitle?: string;
  defaultExpanded?: boolean;
  whatAreWeDoing: React.ReactNode;
  whyAreWeDoingThis: React.ReactNode;
  whatDoesOutputMean: React.ReactNode;
  whatChanged: {
    summary: React.ReactNode;
    table?: {
      headers: [string, string, string, string, string];
      rows: ExplanationMetricRow[];
    };
  };
  whyMightResultChanged: React.ReactNode;
  researchConclusion: React.ReactNode;
}

export const ResearchExplanationPanel: React.FC<ResearchExplanationPanelProps> = ({
  problemId,
  title,
  subtitle,
  defaultExpanded = false,
  whatAreWeDoing,
  whyAreWeDoingThis,
  whatDoesOutputMean,
  whatChanged,
  whyMightResultChanged,
  researchConclusion,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  return (
    <div
      style={{
        marginTop: '16px',
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
      }}
    >
      {/* Panel Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 18px',
          background: 'linear-gradient(to right, #f8fafc, #f1f5f9)',
          borderBottom: isExpanded ? '1px solid #e2e8f0' : 'none',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.15rem' }}>🎓</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  background: '#0284c7',
                  color: '#ffffff',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {problemId} WALKTHROUGH
              </span>
              <strong style={{ fontSize: '0.90rem', color: '#0f172a' }}>
                {title}
              </strong>
            </div>
            {subtitle && (
              <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                {subtitle}
              </p>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.74rem', color: '#64748b', fontWeight: 600 }}>
            {isExpanded ? 'Collapse Guide' : 'Expand Guide'}
          </span>
          <span
            style={{
              fontSize: '0.85rem',
              color: '#475569',
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease',
            }}
          >
            ▼
          </span>
        </div>
      </div>

      {/* Panel Content */}
      {isExpanded && (
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Section A: What are we doing? */}
          <div style={{ borderLeft: '3px solid #0284c7', paddingLeft: '12px' }}>
            <h5 style={{ margin: '0 0 6px', fontSize: '0.84rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              A. What are we doing?
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>
              {whatAreWeDoing}
            </div>
          </div>

          {/* Section B: Why are we doing this? */}
          <div style={{ borderLeft: '3px solid #059669', paddingLeft: '12px' }}>
            <h5 style={{ margin: '0 0 6px', fontSize: '0.84rem', fontWeight: 700, color: '#047857', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              B. Why are we doing this?
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>
              {whyAreWeDoingThis}
            </div>
          </div>

          {/* Section C: What does this output mean? */}
          <div style={{ borderLeft: '3px solid #7c3aed', paddingLeft: '12px' }}>
            <h5 style={{ margin: '0 0 6px', fontSize: '0.84rem', fontWeight: 700, color: '#6d28d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              C. What does this output mean?
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>
              {whatDoesOutputMean}
            </div>
          </div>

          {/* Section D: What changed in the experiment? */}
          <div style={{ borderLeft: '3px solid #d97706', paddingLeft: '12px' }}>
            <h5 style={{ margin: '0 0 6px', fontSize: '0.84rem', fontWeight: 700, color: '#b45309', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              D. What changed in the experiment?
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>
              <div style={{ marginBottom: whatChanged.table ? '10px' : 0 }}>
                {whatChanged.summary}
              </div>

              {whatChanged.table && (
                <div style={{ overflowX: 'auto', borderRadius: '6px', border: '1px solid #e2e8f0', marginTop: '8px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1' }}>
                        {whatChanged.table.headers.map((h, idx) => (
                          <th key={idx} style={{ padding: '7px 10px', color: '#475569', fontWeight: 600 }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {whatChanged.table.rows.map((row, idx) => (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: idx === whatChanged.table!.rows.length - 1 ? 'none' : '1px solid #f1f5f9',
                            background: idx % 2 === 0 ? '#ffffff' : '#fcfcfd',
                          }}
                        >
                          <td style={{ padding: '7px 10px', fontWeight: 600, color: '#1e293b' }}>
                            {row.condition}
                          </td>
                          <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', color: '#475569' }}>
                            {row.baseline}
                          </td>
                          <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', color: '#0f172a', fontWeight: 600 }}>
                            {row.experimental}
                          </td>
                          <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', color: String(row.change).startsWith('-') ? '#dc2626' : '#166534', fontWeight: 600 }}>
                            {row.change}
                          </td>
                          <td style={{ padding: '7px 10px', color: '#64748b' }}>
                            {row.interpretation || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Section E: Why might the result have changed? */}
          <div style={{ borderLeft: '3px solid #dc2626', paddingLeft: '12px' }}>
            <h5 style={{ margin: '0 0 6px', fontSize: '0.84rem', fontWeight: 700, color: '#b91c1c', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              E. Why might the result have changed?
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.55 }}>
              {whyMightResultChanged}
            </div>
          </div>

          {/* Section F: Research conclusion */}
          <div style={{ borderLeft: '3px solid #16a34a', paddingLeft: '12px', background: '#f0fdf4', padding: '10px 14px', borderRadius: '6px' }}>
            <h5 style={{ margin: '0 0 4px', fontSize: '0.84rem', fontWeight: 700, color: '#15803d', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              F. Research conclusion (Student & Mentor Summary)
            </h5>
            <div style={{ fontSize: '0.82rem', color: '#14532d', lineHeight: 1.55, fontWeight: 500 }}>
              {researchConclusion}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
