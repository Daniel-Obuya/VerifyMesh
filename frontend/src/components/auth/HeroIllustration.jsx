import React, { forwardRef } from 'react';

export const HeroIllustration = forwardRef(({ className = '' }, parallaxRef) => {
  return (
    <svg
      className={`art ${className}`}
      id="art"
      viewBox="0 0 460 300"
      role="img"
      aria-label="Competency growth chart inside a sphere"
    >
      <g
        fill="none"
        stroke="#6f7dff"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* L-shaped coordinate axis */}
        <path
          className="draw"
          pathLength="1"
          style={{ '--d': '.1s', '--t': '1.3s' }}
          d="M20 10 V225 Q20 282 78 282 H440"
        />

        {/* Outer parallax container & inner floating sphere */}
        <g id="sphere" ref={parallaxRef}>
          <g className="sphere">
            {/* Central sphere circle */}
            <circle
              className="draw"
              pathLength="1"
              style={{ '--d': '.5s', '--t': '1.2s' }}
              cx="175"
              cy="170"
              r="64"
            />

            {/* Orbit ring 1 (top spinning) */}
            <g className="spin" style={{ transformOrigin: '170px 112px' }}>
              <ellipse
                className="draw"
                pathLength="1"
                style={{ '--d': '.9s', '--t': '1.2s' }}
                cx="170"
                cy="112"
                rx="32"
                ry="11"
              />
            </g>

            {/* Orbit ring 2 (tilted left) */}
            <ellipse
              className="draw"
              pathLength="1"
              style={{ '--d': '1.1s', '--t': '1.3s' }}
              cx="108"
              cy="198"
              rx="46"
              ry="17"
              transform="rotate(-18 108 198)"
            />

            {/* Orbit ring 3 (tilted right) */}
            <ellipse
              className="draw"
              pathLength="1"
              style={{ '--d': '1.3s', '--t': '1.3s' }}
              cx="247"
              cy="188"
              rx="42"
              ry="16"
              transform="rotate(14 247 188)"
            />

            {/* Inner chart miniature axis */}
            <path
              className="draw"
              pathLength="1"
              style={{ '--d': '1.7s', '--t': '.6s' }}
              strokeWidth="1.6"
              d="M152 150 V192 H200"
            />

            {/* 3-point progression polyline */}
            <polyline
              className="draw"
              pathLength="1"
              style={{ '--d': '2.1s', '--t': '.8s' }}
              strokeWidth="1.6"
              points="156,186 170,166 182,172 198,158"
            />

            {/* Chart pop-in data points */}
            <g fill="#0a0e1c" strokeWidth="1.6">
              <circle className="pop" style={{ '--d': '2.5s' }} cx="170" cy="166" r="3.5" />
              <circle className="pop" style={{ '--d': '2.65s' }} cx="182" cy="172" r="3.5" />
              <circle className="pop" style={{ '--d': '2.8s' }} cx="198" cy="158" r="3.5" />
            </g>
          </g>
        </g>

        {/* Straight trajectory vector reaching top-right */}
        <path
          className="draw"
          pathLength="1"
          style={{ '--d': '1.9s', '--t': '1s' }}
          d="M200 120 L410 62"
        />
      </g>

      {/* Target beacon dot with expanding ping ripple */}
      <circle className="pulse" cx="410" cy="62" r="6" fill="#2dd4bf" style={{ '--d': '3s' }} />
      <circle className="pop" style={{ '--d': '2.9s' }} cx="410" cy="62" r="5" fill="#2dd4bf" />
    </svg>
  );
});

HeroIllustration.displayName = 'HeroIllustration';

