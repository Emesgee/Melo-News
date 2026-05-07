import React, { useEffect, useRef } from 'react';
import './ArrowPulse.css';

/**
 * ArrowPulse
 * Animated arrow with pulse effect that points downward
 * Matches the dark glossy theme
 */
const ArrowPulse = ({
  color = 'rgba(100, 225, 255, 0.8)',
  size = 36,
  className = '',
}) => {
  const arrowRef = useRef(null);

  return (
    <div className={`arrow-pulse-container ${className}`} ref={arrowRef}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="arrow-pulse-icon"
        aria-hidden="true"
      >
        <path
          d="M12 5v14M19 12l-7 7-7-7"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="arrow-pulse-ring" style={{ borderColor: color }} />
      <div className="arrow-pulse-ring arrow-pulse-ring-2" style={{ borderColor: color }} />
    </div>
  );
};

export default ArrowPulse;
