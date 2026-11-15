import React, { useState } from 'react';

export interface PieChartItem {
  label: string;
  value: number;
  color: string;
  description?: string;
}

interface PieChartProps {
  data: PieChartItem[];
  title?: string;
  subtitle?: string;
  size?: number;
  donut?: boolean;
}

export const PieChart: React.FC<PieChartProps> = ({
  data,
  title,
  subtitle,
  size = 280,
  donut = true,
}) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const total = data.reduce((acc, item) => acc + item.value, 0);

  if (total === 0) {
    return (
      <div className="chart-empty-state">
        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No categorical data available for chart.
        </span>
      </div>
    );
  }

  const radius = size / 2;
  const innerRadius = donut ? radius * 0.58 : 0;
  const cx = radius;
  const cy = radius;

  // Compute SVG arc paths
  let accumulatedAngle = -Math.PI / 2; // Start at top (12 o'clock)

  const slices = data.map((item, idx) => {
    const sliceAngle = (item.value / total) * 2 * Math.PI;
    const startAngle = accumulatedAngle;
    const endAngle = accumulatedAngle + sliceAngle;
    accumulatedAngle += sliceAngle;

    const isLargeArc = sliceAngle > Math.PI ? 1 : 0;

    // Calculate outer arc points
    const x1 = cx + radius * Math.cos(startAngle);
    const y1 = cy + radius * Math.sin(startAngle);
    const x2 = cx + radius * Math.cos(endAngle);
    const y2 = cy + radius * Math.sin(endAngle);

    let path = '';
    if (donut) {
      const ix1 = cx + innerRadius * Math.cos(endAngle);
      const iy1 = cy + innerRadius * Math.sin(endAngle);
      const ix2 = cx + innerRadius * Math.cos(startAngle);
      const iy2 = cy + innerRadius * Math.sin(startAngle);

      path = [
        `M ${x1} ${y1}`,
        `A ${radius} ${radius} 0 ${isLargeArc} 1 ${x2} ${y2}`,
        `L ${ix1} ${iy1}`,
        `A ${innerRadius} ${innerRadius} 0 ${isLargeArc} 0 ${ix2} ${iy2}`,
        'Z',
      ].join(' ');
    } else {
      path = [
        `M ${cx} ${cy}`,
        `L ${x1} ${y1}`,
        `A ${radius} ${radius} 0 ${isLargeArc} 1 ${x2} ${y2}`,
        'Z',
      ].join(' ');
    }

    const pct = ((item.value / total) * 100).toFixed(1);

    return {
      ...item,
      path,
      pct,
      idx,
    };
  });

  const activeItem = hoveredIdx !== null ? slices[hoveredIdx] : null;

  return (
    <div className="chart-container-box">
      {title && (
        <div className="chart-header">
          <h4 className="chart-title">{title}</h4>
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '24px', flexWrap: 'wrap' }}>
        {/* SVG Circle */}
        <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            style={{ overflow: 'visible', filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))' }}
          >
            {slices.map((slice) => {
              const isHovered = hoveredIdx === slice.idx;
              return (
                <path
                  key={slice.idx}
                  d={slice.path}
                  fill={slice.color}
                  opacity={hoveredIdx === null || isHovered ? 1 : 0.65}
                  stroke="#ffffff"
                  strokeWidth="2"
                  style={{
                    cursor: 'pointer',
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    transform: isHovered ? 'scale(1.03)' : 'scale(1)',
                    transformOrigin: `${cx}px ${cy}px`,
                  }}
                  onMouseEnter={() => setHoveredIdx(slice.idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                />
              );
            })}
          </svg>

          {/* Central Donut Readout */}
          {donut && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                pointerEvents: 'none',
              }}
            >
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: activeItem ? activeItem.color : '#0f172a', lineHeight: 1.1 }}>
                {activeItem ? `${activeItem.pct}%` : total.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {activeItem ? activeItem.label : 'Total Samples'}
              </div>
            </div>
          )}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px', flex: 1 }}>
          {slices.map((slice) => {
            const isHovered = hoveredIdx === slice.idx;
            return (
              <div
                key={slice.idx}
                onMouseEnter={() => setHoveredIdx(slice.idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  backgroundColor: isHovered ? '#e2e8f0' : '#f8fafc',
                  border: `1px solid ${isHovered ? slice.color : '#e2e8f0'}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: slice.color,
                    }}
                  />
                  <div>
                    <span style={{ fontSize: '0.8rem', color: '#0f172a', fontWeight: 600 }}>
                      {slice.label}
                    </span>
                    {slice.description && (
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                        {slice.description}
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: slice.color, fontFamily: 'var(--font-mono)' }}>
                    {slice.value.toLocaleString()}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: '4px' }}>
                    ({slice.pct}%)
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
