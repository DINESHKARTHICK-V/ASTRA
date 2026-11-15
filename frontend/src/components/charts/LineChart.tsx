import React, { useState } from 'react';

export interface LineChartSeries {
  name: string;
  data: number[];
  color: string;
  unit?: string;
  dashed?: boolean;
}

interface LineChartProps {
  xLabels: string[];
  series: LineChartSeries[];
  title?: string;
  subtitle?: string;
  xTitle?: string;
  yTitle?: string;
  yMin?: number;
  yMax?: number;
  height?: number;
}

export const LineChart: React.FC<LineChartProps> = ({
  xLabels,
  series,
  title,
  subtitle,
  xTitle,
  yTitle,
  yMin,
  yMax,
  height = 240,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<{
    seriesIdx: number;
    pointIdx: number;
    x: number;
    y: number;
    value: number;
    name: string;
    label: string;
  } | null>(null);

  if (!series || series.length === 0 || !xLabels || xLabels.length === 0) {
    return (
      <div className="chart-empty-state">
        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No data points to render.
        </span>
      </div>
    );
  }

  // Determine Y domain
  const allValues = series.flatMap((s) => s.data);
  const minVal = yMin !== undefined ? yMin : Math.min(0, ...allValues);
  const maxVal = yMax !== undefined ? yMax : Math.max(...allValues, 1);
  const valRange = maxVal - minVal || 1;

  const padding = { top: 25, right: 30, bottom: 45, left: 55 };
  const width = 600; // SVG viewBox coordinate width
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  // X coordinate calculation
  const getX = (idx: number) => {
    if (xLabels.length === 1) return padding.left + plotWidth / 2;
    return padding.left + (idx / (xLabels.length - 1)) * plotWidth;
  };

  // Y coordinate calculation
  const getY = (val: number) => {
    const norm = (val - minVal) / valRange;
    return padding.top + plotHeight - norm * plotHeight;
  };

  // Y ticks (5 ticks)
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => minVal + t * valRange);

  return (
    <div className="chart-container-box">
      {title && (
        <div className="chart-header">
          <h4 className="chart-title">{title}</h4>
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
      )}

      <div style={{ position: 'relative', width: '100%', overflow: 'hidden' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
          {/* Horizontal Grid lines & Y tick labels */}
          {yTicks.map((tick, i) => {
            const y = getY(tick);
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={padding.left + plotWidth}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--text-dim)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  {tick >= 10 ? tick.toFixed(0) : tick >= 1 ? tick.toFixed(1) : tick.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Axes */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={padding.top + plotHeight}
            stroke="#cbd5e1"
            strokeWidth="1.5"
          />
          <line
            x1={padding.left}
            y1={padding.top + plotHeight}
            x2={padding.left + plotWidth}
            y2={padding.top + plotHeight}
            stroke="#cbd5e1"
            strokeWidth="1.5"
          />

          {/* X Axis Labels */}
          {xLabels.map((label, idx) => {
            const x = getX(idx);
            return (
              <g key={idx}>
                <line
                  x1={x}
                  y1={padding.top + plotHeight}
                  x2={x}
                  y2={padding.top + plotHeight + 5}
                  stroke="#cbd5e1"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y={padding.top + plotHeight + 18}
                  textAnchor="middle"
                  fill="var(--text-muted)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  {label}
                </text>
              </g>
            );
          })}

          {/* Series lines & points */}
          {series.map((s, sIdx) => {
            const points = s.data.map((val, pIdx) => ({
              x: getX(pIdx),
              y: getY(val),
              val,
              pIdx,
            }));

            const pathD = points.reduce((acc, p, i) => {
              return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
            }, '');

            return (
              <g key={sIdx}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="2.5"
                  strokeDasharray={s.dashed ? '5 5' : undefined}
                  style={{ filter: `drop-shadow(0 2px 6px ${s.color}40)` }}
                />

                {points.map((p) => {
                  const isHovered =
                    hoveredPoint?.seriesIdx === sIdx && hoveredPoint?.pointIdx === p.pIdx;
                  return (
                    <circle
                      key={p.pIdx}
                      cx={p.x}
                      cy={p.y}
                      r={isHovered ? 6 : 4}
                      fill={s.color}
                      stroke="#ffffff"
                      strokeWidth="2"
                      style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
                      onMouseEnter={() =>
                        setHoveredPoint({
                          seriesIdx: sIdx,
                          pointIdx: p.pIdx,
                          x: p.x,
                          y: p.y,
                          value: p.val,
                          name: s.name,
                          label: xLabels[p.pIdx],
                        })
                      }
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                  );
                })}
              </g>
            );
          })}

          {/* Y Axis Title */}
          {yTitle && (
            <text
              transform={`rotate(-90)`}
              x={-(padding.top + plotHeight / 2)}
              y="16"
              textAnchor="middle"
              fill="var(--text-muted)"
              fontSize="10"
              fontWeight="600"
            >
              {yTitle}
            </text>
          )}

          {/* X Axis Title */}
          {xTitle && (
            <text
              x={padding.left + plotWidth / 2}
              y={height - 8}
              textAnchor="middle"
              fill="var(--text-muted)"
              fontSize="10"
              fontWeight="600"
            >
              {xTitle}
            </text>
          )}
        </svg>

        {/* Floating Tooltip */}
        {hoveredPoint && (
          <div
            style={{
              position: 'absolute',
              top: `${(hoveredPoint.y / height) * 100}%`,
              left: `${(hoveredPoint.x / width) * 100}%`,
              transform: 'translate(-50%, -120%)',
              backgroundColor: '#0f172a',
              border: '1px solid #0284c7',
              borderRadius: '4px',
              padding: '4px 8px',
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              zIndex: 10,
              whiteSpace: 'nowrap',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              {hoveredPoint.label} • {hoveredPoint.name}
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
              {hoveredPoint.value.toFixed(4)}
            </div>
          </div>
        )}
      </div>

      {/* Series Legend */}
      <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginTop: '12px', flexWrap: 'wrap' }}>
        {series.map((s, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem' }}>
            <span
              style={{
                width: '12px',
                height: '3px',
                backgroundColor: s.color,
                borderRadius: '2px',
                display: 'inline-block',
              }}
            />
            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{s.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
