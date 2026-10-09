import React from 'react';

export const BrandLogo = ({ className = '', size = 'md' }) => {
  const iconSizes = {
    sm: 'w-8 h-8 rounded-lg',
    md: 'w-9 h-9 sm:w-10 sm:h-10 rounded-[10px]',
    lg: 'w-12 h-12 rounded-xl',
  };

  const textSizes = {
    sm: 'text-lg',
    md: 'text-xl sm:text-[22px]',
    lg: 'text-2xl',
  };

  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      {/* Brand Icon Mark */}
      <div
        className={`${iconSizes[size] || iconSizes.md} bg-[#3B50BA] flex items-center justify-center shadow-xs shrink-0 p-1.5 sm:p-2 transition-transform hover:scale-[1.02]`}
      >
        <svg
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full text-white"
        >
          {/* Outer corner frame bracket */}
          <path
            d="M6 8V18C6 20.2091 7.79086 22 10 22H20"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          {/* Connected mesh nodes */}
          <path
            d="M10 17L15 13L21 16"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="10" cy="17" r="2.2" fill="currentColor" />
          <circle cx="15" cy="13" r="2.2" fill="currentColor" />
          <circle cx="21" cy="16" r="2.2" fill="currentColor" />
        </svg>
      </div>

      {/* Brand Wordmark */}
      <span
        className={`${textSizes[size] || textSizes.md} font-bold text-[#0F172A] tracking-tight leading-none`}
      >
        VerifyMesh
      </span>
    </div>
  );
};
