import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Retrieving astrophysical telemetry...',
}) => {
  return (
    <div className="spinner-container">
      <div className="spinner"></div>
      <p style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)' }}>{message}</p>
    </div>
  );
};
