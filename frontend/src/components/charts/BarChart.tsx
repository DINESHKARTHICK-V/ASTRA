import React, { useState } from 'react';

export interface BarChartSeries {
  name: string;
  data: number[];
  color: string;
  unit?: string;
}

export interface ThresholdLineConfig {
  value: number;
  label: string;
  color: string;
}

interface BarChartProps {
  categories: string[];
  series: BarChartSeries[];
  title?: string;
  subtitle?: string;
  xTitle?: string;
  yTitle?: string;
  thresholdLine?: ThresholdLineConfig;
  thresholdLines?: ThresholdLineConfig[];
  diagonalRefLine?: boolean;
  yMin?: number;
  yMax?: number;
  height?: number;
}

export const BarChart: React.FC<BarChartProps> = ({
  categories,
  series,
  title,
  subtitle,
  xTitle,
  yTitle,
  thresholdLine,
  thresholdLines,
  diagonalRefLine,
  yMin,
  yMax,
  height = 240,
}) => {
  const [hoveredBar, setHoveredBar] = useState<{
    catIdx: number;
    seriesIdx: number;
    val: number;
    cat: string;
    seriesName: string;
    x: number;
    y: number;
  } | null>(null);

  if (!series || series.length === 0 || !categories || categories.length === 0) {
    return (
      <div className="chart-empty-state">
        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No data to display in chart.
        </span>
      </div>
    );
  }

  const allVals = series.flatMap((s) => s.data);
  const minVal = yMin !== undefined ? yMin : Math.min(0, ...allVals);
  const maxVal = yMax !== undefined ? yMax : Math.max(...allVals, 1);
  const valRange = maxVal - minVal || 1;

  const padding = { top: 25, right: 30, bottom: 50, left: 55 };
  const width = 600;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const getY = (val: number) => {
    const clamped = Math.max(minVal, Math.min(maxVal, val));
    const norm = (clamped - minVal) / valRange;
    return padding.top + plotHeight - norm * plotHeight;
  };

  const groupWidth = plotWidth / categories.length;
  const barWidth = Math.min(28, (groupWidth * 0.75) / series.length);

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
          {/* Horizontal Grid lines */}
          {yTicks.map((tick, i) => {
            const y = getY(tick);
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={padding.left + plotWidth}
                  y2={y}
                  stroke="#1e293b"
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

          {/* Diagonal Reference Line (e.g. for ideal calibration y = x) */}
          {diagonalRefLine && (
            <line
              x1={padding.left}
              y1={padding.top + plotHeight}
              x2={padding.left + plotWidth}
              y2={padding.top}
              stroke="#64748b"
              strokeDasharray="4 4"
              strokeWidth="1.5"
            />
          )}

          {/* Threshold Lines if provided */}
          {(() => {
            const lines: ThresholdLineConfig[] = [
              ...(thresholdLines || []),
              ...(thresholdLine ? [thresholdLine] : []),
            ];
            if (lines.length === 0) return null;

            return (
              <g>
                {lines.map((line, idx) => (
                  <g key={idx}>
                    <line
                      x1={padding.left}
                      y1={getY(line.value)}
                      x2={padding.left + plotWidth}
                      y2={getY(line.value)}
                      stroke={line.color}
                      strokeDasharray="4 2"
                      strokeWidth="1.5"
                    />
                    <text
                      x={padding.left + plotWidth - 4}
                      y={getY(line.value) - 4}
                      textAnchor="end"
                      fill={line.color}
                      fontSize="9"
                      fontWeight="600"
                    >
                      {line.label}
                    </text>
                  </g>
                ))}
              </g>
            );
          })()}

          {/* Axes */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={padding.top + plotHeight}
            stroke="#334155"
            strokeWidth="1.5"
          />
          <line
            x1={padding.left}
            y1={padding.top + plotHeight}
            x2={padding.left + plotWidth}
            y2={padding.top + plotHeight}
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* Bars grouped by category */}
          {categories.map((cat, catIdx) => {
            const groupX = padding.left + catIdx * groupWidth;
            const totalBarsWidth = series.length * barWidth;
            const startX = groupX + (groupWidth - totalBarsWidth) / 2;

            return (
              <g key={catIdx}>
                {series.map((s, sIdx) => {
                  const val = s.data[catIdx] ?? 0;
                  const barX = startX + sIdx * barWidth;
                  const baselineVal = minVal;
                  const baselineY = getY(baselineVal);
                  const barTopY = getY(val);
                  const barY = Math.min(baselineY, barTopY);
                  const barH = Math.max(2, Math.abs(baselineY - barTopY));

                  const isHovered =
                    hoveredBar?.catIdx === catIdx && hoveredBar?.seriesIdx === sIdx;

                  return (
                    <rect
                      key={sIdx}
                      x={barX}
                      y={barY}
                      width={Math.max(1, barWidth - 2)}
                      height={barH}
                      fill={s.color}
                      rx="2"
                      opacity={isHovered ? 1 : 0.85}
                      style={{
                        cursor: 'pointer',
                        transition: 'opacity 0.15s ease, y 0.2s ease, height 0.2s ease',
                      }}
                      onMouseEnter={() =>
                        setHoveredBar({
                          catIdx,
                          seriesIdx: sIdx,
                          val,
                          cat,
                          seriesName: s.name,
                          x: barX + barWidth / 2,
                          y: barY,
                        })
                      }
                      onMouseLeave={() => setHoveredBar(null)}
                    />
                  );
                })}

                {/* Category Label */}
                <text
                  x={groupX + groupWidth / 2}
                  y={padding.top + plotHeight + 16}
                  textAnchor="middle"
                  fill="var(--text-muted)"
                  fontSize="9.5"
                  fontFamily="var(--font-mono)"
                >
                  {cat}
                </text>
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
              y={height - 6}
              textAnchor="middle"
              fill="var(--text-muted)"
              fontSize="10"
              fontWeight="600"
            >
              {xTitle}
            </text>
          )}
        </svg>

        {/* Tooltip */}
        {hoveredBar && (
          <div
            style={{
              position: 'absolute',
              top: `${(hoveredBar.y / height) * 100}%`,
              left: `${(hoveredBar.x / width) * 100}%`,
              transform: 'translate(-50%, -120%)',
              backgroundColor: '#090e1b',
              border: '1px solid #38bdf8',
              borderRadius: '4px',
              padding: '4px 8px',
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              zIndex: 10,
              whiteSpace: 'nowrap',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              {hoveredBar.cat} • {hoveredBar.seriesName}
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
              {hoveredBar.val.toFixed(4)}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginTop: '12px', flexWrap: 'wrap' }}>
        {series.map((s, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                backgroundColor: s.color,
                borderRadius: '2px',
                display: 'inline-block',
              }}
            />
            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{s.name}</span>
          </div>
        ))}
        {diagonalRefLine && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem' }}>
            <span style={{ width: '12px', height: '2px', borderTop: '2px dashed #64748b', display: 'inline-block' }} />
            <span style={{ color: 'var(--text-dim)' }}>Ideal Calibration (y = x)</span>
          </div>
        )}
      </div>
    </div>
  );
};
