import React from 'react';

interface StatusBadgeProps {
  type: 'priority' | 'inference' | 'quality' | 'general';
  value: string | null | undefined;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  if (!value) {
    return <span className="badge badge-neutral">N/A</span>;
  }

  const valUpper = value.toUpperCase();

  if (type === 'priority') {
    if (valUpper === 'HIGH') {
      return <span className="badge badge-high">● High Priority</span>;
    }
    if (valUpper === 'MEDIUM') {
      return <span className="badge badge-medium">● Medium</span>;
    }
    if (valUpper === 'LOW') {
      return <span className="badge badge-low">● Low</span>;
    }
  }

  if (type === 'inference') {
    if (valUpper === 'INFERENCE_HALTED') {
      return (
        <span
          className="badge badge-halted"
          title="Inference safely halted: search-mode DM trial curves absent in folded archives."
        >
          ⚠ Inference Halted
        </span>
      );
    }
    if (valUpper === 'COMPLETED') {
      return <span className="badge badge-completed">✓ Completed</span>;
    }
  }

  if (type === 'quality') {
    if (valUpper === 'VALID' || valUpper === 'VALID_PSRFITS') {
      return <span className="badge badge-high">✓ Valid</span>;
    }
    if (valUpper === 'BLANK_OBSERVATION') {
      return <span className="badge badge-low">Empty Frame</span>;
    }
  }

  return <span className="badge badge-neutral">{value}</span>;
};
