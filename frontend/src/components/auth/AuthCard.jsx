import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../../context/AuthContext';
import { ForgotPasswordModal } from './ForgotPasswordModal';

export const AuthCard = () => {
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();

  const [identifier, setIdentifier] = useState('alex.morgan@university.edu');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Validation & Submission state
  const [validated, setValidated] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({ identifier: null, password: null });
  const [authError, setAuthError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  const validateEmail = (val) => {
    if (!val || !val.trim()) return 'Enter a valid email address.';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(val.trim())) return 'Enter a valid email address.';
    return null;
  };

  const validatePassword = (val) => {
    if (!val) return 'Password must be at least 8 characters.';
    if (val.length < 8) return 'Password must be at least 8 characters.';
    return null;
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await loginWithGoogle(credentialResponse.credential);
      if (res?.user?.dashboardUrl) {
        navigate(res.user.dashboardUrl);
      } else if (res?.user?.role === 'Administrator') {
        navigate('/admin/dashboard');
      } else {
        navigate('/agent/dashboard');
      }
    } catch (err) {
      setAuthError(err.message || 'Google authentication failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setValidated(true);

    const emailErr = validateEmail(identifier);
    const passErr = validatePassword(password);

    setFieldErrors({
      identifier: emailErr,
      password: passErr,
    });

    if (emailErr || passErr) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await login({
        identifier: identifier.trim(),
        password,
        rememberMe,
      });

      if (response?.user?.dashboardUrl) {
        navigate(response.user.dashboardUrl);
      } else if (response?.user?.role === 'Administrator') {
        navigate('/admin/dashboard');
      } else {
        navigate('/agent/dashboard');
      }
    } catch (err) {
      setAuthError(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <section className="w-full max-w-[430px] rounded-2xl sm:rounded-3xl p-7 sm:p-9 bg-gradient-to-b from-[#171e38]/90 to-[#10162b]/95 border border-[#222a48] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.7)] transition-all card-in">
        {/* Card Header */}
        <div className="mb-6 sm:mb-7 rise" style={{ '--d': '0.15s' }}>
          <h2 className="font-sora text-2xl sm:text-[26px] font-bold text-white tracking-tight leading-tight">
            Welcome back
          </h2>
          <p className="mt-1.5 text-xs sm:text-sm text-[#8d97b8] font-normal">
            Sign in to your VerifyMesh account
          </p>
        </div>

        {/* Auth Error Banner */}
        {authError && (
          <div
            className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs sm:text-sm text-rose-300 flex items-center justify-between animate-shake"
            role="alert"
          >
            <span>{authError}</span>
            <button
              type="button"
              className="text-rose-400 hover:text-white p-1 text-sm font-bold cursor-pointer"
              aria-label="Close"
              onClick={() => setAuthError(null)}
            >
              &times;
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-4.5" noValidate>
          {/* Email Field with Static Label Directly Above Input */}
          <div className="rise" style={{ '--d': '0.25s' }}>
            <label
              htmlFor="email"
              className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              name="identifier"
              placeholder="alex.morgan@university.edu"
              autoComplete="email"
              value={identifier}
              onChange={(e) => {
                const val = e.target.value;
                setIdentifier(val);
                if (validated) {
                  setFieldErrors((prev) => ({ ...prev, identifier: validateEmail(val) }));
                }
              }}
              className={`w-full h-11 sm:h-12 px-3.5 sm:px-4 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                validated && fieldErrors.identifier
                  ? 'border-rose-500/70 focus:border-rose-500'
                  : 'border-[#222a48] focus:border-[#6f7dff]'
              }`}
              required
            />
            {validated && fieldErrors.identifier && (
              <p className="text-xs text-rose-400 mt-1.5 animate-fadeIn">{fieldErrors.identifier}</p>
            )}
          </div>

          {/* Password Field with Static Label Directly Above Input & Inset Eye Toggle */}
          <div className="rise" style={{ '--d': '0.35s' }}>
            <label
              htmlFor="password"
              className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
            >
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                placeholder="••••••••••••"
                autoComplete="current-password"
                minLength={8}
                value={password}
                onChange={(e) => {
                  const val = e.target.value;
                  setPassword(val);
                  if (validated) {
                    setFieldErrors((prev) => ({ ...prev, password: validatePassword(val) }));
                  }
                }}
                className={`w-full h-11 sm:h-12 px-3.5 sm:px-4 pe-11 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                  validated && fieldErrors.password
                    ? 'border-rose-500/70 focus:border-rose-500'
                    : 'border-[#222a48] focus:border-[#6f7dff]'
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8d97b8] hover:text-[#e8ebf7] p-1 transition-colors cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4 transition-transform active:scale-90" />
                ) : (
                  <Eye className="w-4 h-4 transition-transform active:scale-90" />
                )}
              </button>
            </div>
            {validated && fieldErrors.password && (
              <p className="text-xs text-rose-400 mt-1.5 animate-fadeIn">{fieldErrors.password}</p>
            )}
          </div>

          {/* Utility Row: Remember Me & Forgot Password Aligned Horizontally */}
          <div className="flex items-center justify-between pt-0.5 rise" style={{ '--d': '0.45s' }}>
            <label
              htmlFor="remember"
              className="flex items-center gap-2 cursor-pointer select-none text-xs sm:text-sm text-[#8d97b8] hover:text-[#cbd5e1] transition-colors"
            >
              <input
                type="checkbox"
                id="remember"
                name="remember-me"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-[#222a48] bg-[#0c1224] text-[#5a69f0] focus:ring-[#5a69f0]/30 focus:ring-offset-0 cursor-pointer accent-[#5a69f0] transition-transform active:scale-90"
              />
              <span>Remember me</span>
            </label>

            <button
              type="button"
              onClick={() => setIsForgotModalOpen(true)}
              className="text-xs sm:text-sm font-semibold text-[#6f7dff] hover:text-[#8d97ff] transition-colors cursor-pointer select-none hover:underline underline-offset-4"
            >
              Forgot password?
            </button>
          </div>

          {/* Full-Width Primary Sign In Button with Shimmer & Spring click */}
          <div className="rise" style={{ '--d': '0.55s' }}>
            <button
              type="submit"
              disabled={isLoading}
              className="btn-shine w-full h-11 sm:h-12 rounded-xl bg-[#5a69f0] hover:bg-[#6f7dff] active:bg-[#4b5bd8] text-white font-semibold text-sm sm:text-base shadow-lg shadow-indigo-500/25 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:shadow-indigo-500/40 active:translate-y-0 active:scale-[0.99] mt-2"
            >
              {isLoading && (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              <span>{isLoading ? 'Signing in…' : 'Sign In'}</span>
            </button>
          </div>

          {/* Create Account Link Row */}
          <div className="pt-2 text-center text-xs sm:text-sm text-[#8d97b8] rise" style={{ '--d': '0.65s' }}>
            Don't have an account?{' '}
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="font-semibold text-[#6f7dff] hover:text-[#8d97ff] transition-colors cursor-pointer select-none hover:underline underline-offset-4"
            >
              Create an account
            </button>
          </div>

          {/* Divider: OR CONTINUE WITH */}
          <div className="relative my-5 rise" style={{ '--d': '0.72s' }}>
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#222a48]" />
            </div>
            <div className="relative flex justify-center text-[10px] sm:text-[11px] uppercase tracking-wider">
              <span className="bg-[#121931] px-3 text-[#8d97b8] font-medium">
                OR CONTINUE WITH
              </span>
            </div>
          </div>

          {/* Google Sign-in */}
          <div className="flex justify-center w-full rise" style={{ '--d': '0.8s' }}>
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setAuthError('Google Sign-In was cancelled or failed.')}
              theme="filled_black"
              shape="rectangular"
              size="large"
              width="356"
              text="signin_with"
            />
          </div>
        </form>
      </section>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
      />
    </>
  );
};
