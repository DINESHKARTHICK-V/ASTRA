import React from 'react';

export interface ConfusionMatrixProps {
  title?: string;
  subtitle?: string;
  truePositives: number;
  trueNegatives: number;
  falsePositives: number;
  falseNegatives: number;
  totalSamples?: number;
}

export const ConfusionMatrix: React.FC<ConfusionMatrixProps> = ({
  title = 'Empirical Classification Confusion Matrix',
  subtitle = 'Held-out test set evaluation (actual vs. predicted classes)',
  truePositives,
  trueNegatives,
  falsePositives,
  falseNegatives,
  totalSamples,
}) => {
  const total = totalSamples || (truePositives + trueNegatives + falsePositives + falseNegatives);
  const actualPositives = truePositives + falseNegatives;
  const actualNegatives = trueNegatives + falsePositives;
  const predictedPositives = truePositives + falsePositives;

  const accuracy = total > 0 ? (truePositives + trueNegatives) / total : 0;
  const precision = predictedPositives > 0 ? truePositives / predictedPositives : 0;
  const recall = actualPositives > 0 ? truePositives / actualPositives : 0;
  const f1 = (precision + recall) > 0 ? (2 * precision * recall) / (precision + recall) : 0;
  const fpr = actualNegatives > 0 ? (falsePositives / actualNegatives) * 100 : 0;
  const fnr = actualPositives > 0 ? (falseNegatives / actualPositives) * 100 : 0;

  return (
    <div className="card" style={{ padding: '20px' }}>
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <h4 className="card-title" style={{ fontSize: '0.96rem', margin: 0, color: 'var(--text-main)' }}>
            {title}
          </h4>
          {subtitle && (
            <p style={{ margin: '3px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              {subtitle}
            </p>
          )}
        </div>
        <span className="badge badge-validated">
          N = {total.toLocaleString()} candidates
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '16px', alignItems: 'center' }}>
        {/* Actual Class Y-Axis Label */}
        <div style={{
          writingMode: 'vertical-rl',
          transform: 'rotate(180deg)',
          textAlign: 'center',
          fontWeight: 700,
          fontSize: '0.74rem',
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
        }}>
          Ground Truth (Actual)
        </div>

        <div>
          {/* Predicted Class X-Axis Label */}
          <div style={{
            textAlign: 'center',
            fontWeight: 700,
            fontSize: '0.74rem',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            marginBottom: '8px',
          }}>
            Model Prediction
          </div>

          {/* Matrix Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '120px 1fr 1fr',
            gap: '8px',
            fontSize: '0.78rem',
          }}>
            {/* Header row */}
            <div />
            <div style={{ textAlign: 'center', fontWeight: 600, color: 'var(--text-muted)', padding: '6px' }}>
              Predicted Negative (RFI)
            </div>
            <div style={{ textAlign: 'center', fontWeight: 600, color: 'var(--text-muted)', padding: '6px' }}>
              Predicted Positive (Pulsar)
            </div>

            {/* Actual Negative Row */}
            <div style={{ display: 'flex', alignItems: 'center', fontWeight: 600, color: 'var(--text-muted)' }}>
              Actual Negative (RFI)
            </div>
            {/* True Negative Box */}
            <div style={{
              background: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: '6px',
              padding: '14px 10px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.7rem', color: '#166534', fontWeight: 600, textTransform: 'uppercase' }}>
                True Negative (TN)
              </div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#15803d', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                {trueNegatives.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#166534' }}>
                {((trueNegatives / total) * 100).toFixed(1)}% of total
              </div>
            </div>
            {/* False Positive Box */}
            <div style={{
              background: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '6px',
              padding: '14px 10px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.7rem', color: '#92400e', fontWeight: 600, textTransform: 'uppercase' }}>
                False Positive (FP / Type I)
              </div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#b45309', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                {falsePositives.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#92400e' }}>
                FPR: {fpr.toFixed(2)}%
              </div>
            </div>

            {/* Actual Positive Row */}
            <div style={{ display: 'flex', alignItems: 'center', fontWeight: 600, color: 'var(--text-muted)' }}>
              Actual Positive (Pulsar)
            </div>
            {/* False Negative Box */}
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '14px 10px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.7rem', color: '#991b1b', fontWeight: 600, textTransform: 'uppercase' }}>
                False Negative (FN / Type II)
              </div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#dc2626', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                {falseNegatives.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#991b1b' }}>
                FNR: {fnr.toFixed(2)}%
              </div>
            </div>
            {/* True Positive Box */}
            <div style={{
              background: '#f0f9ff',
              border: '1px solid #bae6fd',
              borderRadius: '6px',
              padding: '14px 10px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.7rem', color: '#075985', fontWeight: 600, textTransform: 'uppercase' }}>
                True Positive (TP)
              </div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0284c7', fontFamily: 'var(--font-mono)', margin: '4px 0' }}>
                {truePositives.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#075985' }}>
                {((truePositives / total) * 100).toFixed(1)}% of total
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Calculated Metrics Summary Bar */}
      <div style={{
        marginTop: '16px',
        paddingTop: '12px',
        borderTop: '1px solid var(--border-subtle)',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        textAlign: 'center',
      }}>
        <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Accuracy</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
            {(accuracy * 100).toFixed(2)}%
          </div>
        </div>
        <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Precision</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0284c7', fontFamily: 'var(--font-mono)' }}>
            {(precision * 100).toFixed(2)}%
          </div>
        </div>
        <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Recall</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#16a34a', fontFamily: 'var(--font-mono)' }}>
            {(recall * 100).toFixed(2)}%
          </div>
        </div>
        <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>F1-Score</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#7c3aed', fontFamily: 'var(--font-mono)' }}>
            {f1.toFixed(4)}
          </div>
        </div>
      </div>
    </div>
  );
};
