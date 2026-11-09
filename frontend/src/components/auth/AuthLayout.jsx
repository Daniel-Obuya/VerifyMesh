import React from 'react';
import { AuthIllustration } from './AuthIllustration';
import '../../styles/login-theme.css';

export const AuthLayout = ({ children, isRegister = false }) => {
  return (
    <div className="verifymesh-auth-page min-h-screen w-full bg-[#0a0e1c] text-[#e8ebf7] relative overflow-x-hidden selection:bg-[#5a69f0]/30 selection:text-white hero-bg-dots">
      {/* Ambient background glow blobs */}
      <div className="blob b1 pointer-events-none" aria-hidden="true" />
      <div className="blob b2 pointer-events-none" aria-hidden="true" />

      {/* Unified 2-Column Desktop Grid Container */}
      <div className="min-h-screen w-full flex flex-col md:flex-row relative z-10 max-w-[1600px] mx-auto">
        {/* LEFT COLUMN: Brand, Typography & Vector Illustration */}
        <aside className="w-full md:w-1/2 lg:w-[52%] flex flex-col justify-between p-7 sm:p-10 md:p-12 lg:p-16 xl:p-20 relative">
          {/* Top-Left Brand Header */}
          <div className="flex items-center gap-3 rise" style={{ '--d': '0.05s' }}>
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-[#4b5bd8] to-[#6f7dff] flex items-center justify-center p-2 shrink-0 logo-glow shadow-lg shadow-indigo-500/25">
              <svg viewBox="0 0 28 28" fill="none" className="w-full h-full text-white">
                <path d="M6 8V18C6 20.2091 7.79086 22 10 22H20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M10 17L15 13L21 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="10" cy="17" r="2.2" fill="currentColor" />
                <circle cx="15" cy="13" r="2.2" fill="currentColor" />
                <circle cx="21" cy="16" r="2.2" fill="currentColor" />
              </svg>
            </div>
            <span className="font-sora text-xl sm:text-[22px] font-bold text-white tracking-tight leading-none">
              VerifyMesh
            </span>
          </div>

          {/* Center Hero Content */}
          <div className="my-8 md:my-auto max-w-lg">
            <h1 className="font-sora text-3xl sm:text-4xl lg:text-[42px] font-bold text-white tracking-tight leading-[1.18] rise" style={{ '--d': '0.15s' }}>
              AI-Assisted Competency <br className="hidden sm:inline" />
              &amp; Eligibility
            </h1>
            <p className="mt-3.5 sm:mt-4 text-sm sm:text-base text-[#8d97b8] font-normal leading-relaxed max-w-md rise" style={{ '--d': '0.3s' }}>
              Assess agent competencies, verify eligibility requirements, and support intelligent task allocation.
            </p>

            {/* Line Art Vector Illustration */}
            <div className="mt-8 sm:mt-12 flex items-center justify-start rise" style={{ '--d': '0.45s' }}>
              <AuthIllustration color="#6f7dff" />
            </div>
          </div>

          {/* Bottom-Left Footer */}
          <div className="pt-4 md:pt-0 rise" style={{ '--d': '0.6s' }}>
            <p className="text-xs text-[#8d97b8] font-medium tracking-normal select-none">
              VerifyMesh &bull; Integrated with SalesMesh
            </p>
          </div>
        </aside>

        {/* RIGHT COLUMN: Authentication Card (Floating & Centered) */}
        <main className="w-full md:w-1/2 lg:w-[48%] flex flex-col justify-between items-center p-6 sm:p-10 lg:p-12 min-h-[600px] md:min-h-screen relative">
          {/* Top spacer for clean vertical balance matching left brand mark */}
          <div className="hidden md:block h-10" aria-hidden="true" />

          {/* Centered Auth Card Container */}
          <div className="w-full flex justify-center items-center my-auto py-6 md:py-0">
            {children}
          </div>

          {/* Bottom Security Footer Note */}
          <div className="pb-2 select-none">
            <p className="text-xs text-[#8d97b8] font-medium tracking-normal text-center flex items-center justify-center gap-1.5">
              <i className="bi bi-lock-fill text-[11px]" aria-hidden="true" />
              {isRegister
                ? 'Secure access \u2022 Role determined automatically'
                : 'Secure access \u2022 Your role is set after you sign in'}
            </p>
          </div>
        </main>
      </div>
    </div>
  );
};
