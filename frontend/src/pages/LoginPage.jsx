import React from 'react';
import { BrandLogo } from '../components/auth/BrandLogo';
import { AuthIllustration } from '../components/auth/AuthIllustration';
import { LoginForm } from '../components/auth/LoginForm';

export const LoginPage = () => {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F8FAFC]">
      {/* LEFT COLUMN: Brand, Vision & Vector Illustration */}
      <div className="w-full lg:w-1/2 bg-white flex flex-col justify-between p-8 sm:p-12 md:p-14 lg:p-16 xl:p-20 border-b lg:border-b-0 lg:border-r border-slate-100">
        {/* Brand Header */}
        <div className="flex items-center">
          <BrandLogo size="md" />
        </div>

        {/* Center Hero Content */}
        <div className="my-10 lg:my-0 max-w-lg">
          <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-bold text-[#0F172A] tracking-tight leading-[1.18]">
            AI-Assisted Competency <br className="hidden sm:inline" />
            &amp; Eligibility
          </h1>
          <p className="mt-4 text-sm sm:text-base text-slate-500 font-normal leading-relaxed max-w-md">
            Assess agent competencies, verify eligibility requirements, and support intelligent task allocation.
          </p>

          {/* Line Art Vector Illustration */}
          <div className="mt-10 lg:mt-14 flex items-center justify-start">
            <AuthIllustration />
          </div>
        </div>

        {/* Left Footer */}
        <div className="pt-4 lg:pt-0">
          <p className="text-xs text-slate-400 font-medium tracking-normal select-none">
            VerifyMesh &bull; Integrated with SalesMesh
          </p>
        </div>
      </div>

      {/* RIGHT COLUMN: Authentication Card */}
      <div className="w-full lg:w-1/2 bg-[#F8FAFC] flex flex-col justify-between items-center p-6 sm:p-10 lg:p-12 min-h-[640px] lg:min-h-screen">
        {/* Top spacer for balanced vertical alignment */}
        <div className="hidden lg:block h-6" aria-hidden="true" />

        {/* Centered Login Card */}
        <div className="w-full flex justify-center items-center my-auto py-8 lg:py-0">
          <LoginForm />
        </div>

        {/* Right Footer */}
        <div className="pb-2 select-none">
          <p className="text-xs text-slate-400 font-medium tracking-normal text-center">
            Secure access &bull; Role determined after authentication
          </p>
        </div>
      </div>
    </div>
  );
};
