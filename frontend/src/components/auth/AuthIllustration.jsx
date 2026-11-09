import React from 'react';

export const AuthIllustration = ({ className = '', color = '#6f7dff' }) => {
  return (
    <div className={`w-full max-w-[380px] select-none ${className}`}>
      <svg
        viewBox="0 0 340 220"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="art w-full h-auto"
        role="img"
        aria-label="Competency growth illustration"
      >
        {/* Outer boundary curve: vertical line, smooth 90 deg rounded corner, horizontal line */}
        <path
          className="draw"
          pathLength="1"
          style={{ '--d': '0.1s', '--t': '1.2s' }}
          d="M35 15V160C35 178 50 192 68 192H315"
          stroke={color}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Central magnifying glass / evaluation circle and floating content */}
        <g id="sphere">
          <g className="sphere">
            {/* Main lens circle */}
            <circle
              className="draw"
              pathLength="1"
              style={{ '--d': '0.45s', '--t': '1.1s' }}
              cx="155"
              cy="110"
              r="42"
              stroke={color}
              strokeWidth="1.8"
            />

            {/* Orbit ellipse with gentle continuous 3D spin */}
            <g className="spin" style={{ transformOrigin: '160px 75px' }}>
              <ellipse
                className="draw"
                pathLength="1"
                style={{ '--d': '0.75s', '--t': '1.1s' }}
                cx="160"
                cy="75"
                rx="28"
                ry="9"
                transform="rotate(-5 160 75)"
                stroke={color}
                strokeWidth="1.6"
              />
            </g>

            {/* Bottom-left tilted ellipse */}
            <ellipse
              className="draw"
              pathLength="1"
              style={{ '--d': '0.95s', '--t': '1.2s' }}
              cx="120"
              cy="125"
              rx="26"
              ry="11"
              transform="rotate(-18 120 125)"
              stroke={color}
              strokeWidth="1.6"
            />

            {/* Right side tilted ellipse */}
            <ellipse
              className="draw"
              pathLength="1"
              style={{ '--d': '1.15s', '--t': '1.2s' }}
              cx="195"
              cy="115"
              rx="24"
              ry="12"
              transform="rotate(10 195 115)"
              stroke={color}
              strokeWidth="1.6"
            />

            {/* Inner coordinate grid axes */}
            <path
              className="draw"
              pathLength="1"
              style={{ '--d': '1.4s', '--t': '0.6s' }}
              d="M145 100 V128 H175"
              stroke={color}
              strokeWidth="1.2"
              strokeLinecap="round"
            />

            {/* Connected nodes chart inside the lens */}
            <path
              className="draw"
              pathLength="1"
              style={{ '--d': '1.65s', '--t': '0.8s' }}
              d="M150 120L158 108L170 112"
              stroke={color}
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Popping data points with staggered pop scale animation */}
            <g fill="#0a0e1c">
              <circle
                className="pop"
                style={{ '--d': '2.0s' }}
                cx="150"
                cy="120"
                r="2.5"
                stroke={color}
                strokeWidth="1.4"
              />
              <circle
                className="pop"
                style={{ '--d': '2.15s' }}
                cx="158"
                cy="108"
                r="2.5"
                stroke={color}
                strokeWidth="1.4"
              />
              <circle
                className="pop"
                style={{ '--d': '2.3s' }}
                cx="170"
                cy="112"
                r="2.5"
                stroke={color}
                strokeWidth="1.4"
              />
            </g>
          </g>
        </g>

        {/* Pointer / handle line extending to top-right */}
        <path
          className="draw"
          pathLength="1"
          style={{ '--d': '1.5s', '--t': '0.9s' }}
          d="M184 82 L305 52"
          stroke={color}
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        {/* Glowing teal beacon dot and radar pulse rings at the tip */}
        <circle
          className="pulse"
          cx="305"
          cy="52"
          r="6"
          fill="#2dd4bf"
          style={{ '--d': '2.6s' }}
        />
        <circle
          className="pop"
          style={{ '--d': '2.5s' }}
          cx="305"
          cy="52"
          r="4.5"
          fill="#2dd4bf"
        />
        <circle
          cx="305"
          cy="52"
          r="9"
          fill="#2dd4bf"
          opacity="0.18"
        />
      </svg>
    </div>
  );
};
