import React from 'react';

export const AuthIllustration = ({ className = '' }) => {
  return (
    <div className={`w-full max-w-[380px] select-none ${className}`}>
      <svg
        viewBox="0 0 340 220"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto"
      >
        {/* Outer boundary curve: vertical line, smooth 90 deg rounded corner, horizontal line */}
        <path
          d="M35 15V160C35 178 50 192 68 192H315"
          stroke="#3B50BA"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Central magnifying glass / evaluation circle */}
        <circle
          cx="155"
          cy="110"
          r="42"
          stroke="#3B50BA"
          strokeWidth="1.8"
        />

        {/* Pointer / handle line extending to top-right */}
        <line
          x1="184"
          y1="82"
          x2="305"
          y2="52"
          stroke="#3B50BA"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        {/* Top/slanted ellipse intersecting upper circle */}
        <ellipse
          cx="160"
          cy="75"
          rx="28"
          ry="9"
          transform="rotate(-5 160 75)"
          stroke="#3B50BA"
          strokeWidth="1.6"
        />

        {/* Bottom-left tilted ellipse */}
        <ellipse
          cx="120"
          cy="125"
          rx="26"
          ry="11"
          transform="rotate(-18 120 125)"
          stroke="#3B50BA"
          strokeWidth="1.6"
        />

        {/* Right side tilted ellipse */}
        <ellipse
          cx="195"
          cy="115"
          rx="24"
          ry="12"
          transform="rotate(10 195 115)"
          stroke="#3B50BA"
          strokeWidth="1.6"
        />

        {/* Inner coordinate grid inside the lens */}
        <line
          x1="145"
          y1="100"
          x2="145"
          y2="128"
          stroke="#3B50BA"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <line
          x1="145"
          y1="128"
          x2="175"
          y2="128"
          stroke="#3B50BA"
          strokeWidth="1.2"
          strokeLinecap="round"
        />

        {/* Connected nodes chart inside the lens */}
        <path
          d="M150 120L158 108L170 112"
          stroke="#3B50BA"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="150" cy="120" r="2.2" stroke="#3B50BA" strokeWidth="1.2" fill="#FFFFFF" />
        <circle cx="158" cy="108" r="2.2" stroke="#3B50BA" strokeWidth="1.2" fill="#FFFFFF" />
        <circle cx="170" cy="112" r="2.2" stroke="#3B50BA" strokeWidth="1.2" fill="#FFFFFF" />
      </svg>
    </div>
  );
};
