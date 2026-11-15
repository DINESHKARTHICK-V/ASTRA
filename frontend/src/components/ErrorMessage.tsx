import React from 'react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title = 'API Communication Error',
  message,
  onRetry,
}) => {
  return (
    <div className="alert-box alert-error" style={{ flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
        <span>⚠</span>
        <span>{title}</span>
      </div>
      <p style={{ margin: '6px 0 12px', fontSize: '0.85rem', color: '#fca5a5' }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn"
          style={{
            background: 'rgba(239, 68, 68, 0.2)',
            borderColor: 'rgba(239, 68, 68, 0.4)',
            color: '#fff',
            fontSize: '0.78rem',
            padding: '4px 12px',
          }}
        >
          ↻ Retry Connection
        </button>
      )}
    </div>
  );
};
