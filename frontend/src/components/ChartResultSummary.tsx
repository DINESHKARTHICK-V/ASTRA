import React from 'react';

export type ResultGrade =
  | 'Excellent'
  | 'Good'
  | 'Moderate'
  | 'Low'
  | 'Poor'
  | 'Stable'
  | 'Decreasing'
  | 'Incompatible'
  | 'Unavailable';

export interface MetricPill {
  label: string;
  value: string | number;
}

export interface ChartResultSummaryProps {
  grade?: ResultGrade;
  title?: string;
  summaryText: string;
  metrics?: MetricPill[];
  isUnavailable?: boolean;
}

const getGradeStyle = (grade?: ResultGrade) => {
  switch (grade) {
    case 'Excellent':
    case 'Good':
    case 'Stable':
      return {
        bg: '#ecfdf5',
        color: '#065f46',
        border: '#a7f3d0',
        dot: '#10b981',
      };
    case 'Moderate':
      return {
        bg: '#fffbeb',
        color: '#92400e',
        border: '#fde68a',
        dot: '#f59e0b',
      };
    case 'Decreasing':
      return {
        bg: '#fff7ed',
        color: '#c2410c',
        border: '#fed7aa',
        dot: '#f97316',
      };
    case 'Low':
    case 'Poor':
      return {
        bg: '#fef2f2',
        color: '#991b1b',
        border: '#fecaca',
        dot: '#ef4444',
      };
    case 'Incompatible':
      return {
        bg: '#fff1f2',
        color: '#9f1239',
        border: '#fecdd3',
        dot: '#f43f5e',
      };
    default:
      return {
        bg: '#f8fafc',
        color: '#475569',
        border: '#cbd5e1',
        dot: '#94a3b8',
      };
  }
};

export const ChartResultSummary: React.FC<ChartResultSummaryProps> = ({
  grade,
  title = 'Result Summary',
  summaryText,
  metrics,
  isUnavailable = false,
}) => {
  if (isUnavailable) {
    return (
      <div
        style={{
          marginTop: '10px',
          marginBottom: '6px',
          padding: '10px 14px',
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '6px',
          fontSize: '0.80rem',
          color: '#64748b',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span style={{ fontSize: '0.9rem' }}>ℹ️</span>
        <span>Results are not available for this test condition yet. Please run the experiment suite.</span>
      </div>
    );
  }

  const style = getGradeStyle(grade);

  return (
    <div
      style={{
        marginTop: '10px',
        marginBottom: '6px',
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderLeft: `4px solid ${style.dot}`,
        borderRadius: '6px',
        padding: '10px 14px',
        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {title}
          </span>
          {grade && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: style.bg,
                color: style.color,
                border: `1px solid ${style.border}`,
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.72rem',
                fontWeight: 700,
                lineHeight: 1.2,
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: style.dot,
                  display: 'inline-block',
                }}
              />
              {grade}
            </span>
          )}
        </div>

        {metrics && metrics.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {metrics.map((m, idx) => (
              <span
                key={idx}
                style={{
                  background: '#f1f5f9',
                  border: '1px solid #e2e8f0',
                  color: '#475569',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  fontSize: '0.70rem',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                <span style={{ color: '#64748b', fontWeight: 500 }}>{m.label}: </span>
                <strong style={{ color: '#0f172a' }}>{m.value}</strong>
              </span>
            ))}
          </div>
        )}
      </div>

      <p
        style={{
          margin: 0,
          fontSize: '0.81rem',
          lineHeight: 1.5,
          color: '#334155',
        }}
      >
        {summaryText}
      </p>
    </div>
  );
};
