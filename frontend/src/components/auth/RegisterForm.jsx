import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, CheckCircle2, XCircle } from 'lucide-react';
import { VerifyEmailForm } from './VerifyEmailForm';

export const RegisterForm = () => {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Validation & Submission State
  const [validated, setValidated] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [authError, setAuthError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Transition to OTP verification
  const [pendingEmail, setPendingEmail] = useState(null);

  // Password strength calculator
  const calculateStrength = (pass) => {
    if (!pass) return { score: 0, label: '', cls: 'bg-transparent' };
    let score = 0;
    if (pass.length >= 8) score++;
    if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) score++;
    if (/\d/.test(pass) || /[^A-Za-z0-9]/.test(pass)) score++;

    if (score === 1) return { score: 1, label: 'Weak', cls: 'bg-rose-500 w-1/3' };
    if (score === 2) return { score: 2, label: 'Fair', cls: 'bg-amber-500 w-2/3' };
    return { score: 3, label: 'Strong', cls: 'bg-emerald-500 w-full' };
  };

  const strength = calculateStrength(password);

  const validate = () => {
    const errors = {};
    if (!fullName.trim()) {
      errors.fullName = 'Full name is required.';
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      errors.email = 'Please enter a valid email address.';
    }
    if (!phone.trim()) {
      errors.phone = 'Phone number is required.';
    }
    if (!password || password.length < 8) {
      errors.password = 'Password must be at least 8 characters.';
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setValidated(true);

    if (!validate()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          phone: phone.trim(),
          password,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed. Please check your details and try again.');
      }

      setPendingEmail(email.trim().toLowerCase());
    } catch (err) {
      setAuthError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (pendingEmail) {
    return (
      <VerifyEmailForm
        email={pendingEmail}
        onBack={() => setPendingEmail(null)}
      />
    );
  }

  return (
    <section className="w-full max-w-[480px] rounded-2xl sm:rounded-3xl p-7 sm:p-9 bg-gradient-to-b from-[#171e38]/90 to-[#10162b]/95 border border-[#222a48] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.7)] transition-all card-in">
      {/* Header */}
      <div className="mb-6 rise" style={{ '--d': '0.15s' }}>
        <h2 className="font-sora text-2xl sm:text-[26px] font-bold text-white tracking-tight leading-tight">
          Create your account
        </h2>
        <p className="mt-1.5 text-xs sm:text-sm text-[#8d97b8] font-normal">
          Join VerifyMesh and build your professional competency profile.
        </p>
      </div>

      {/* Auth Error Banner */}
      {authError && (
        <div
          className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs sm:text-sm text-rose-300 flex items-center justify-between"
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

      {/* Registration Form */}
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Row 1: Full Name & Phone Number */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 rise" style={{ '--d': '0.25s' }}>
          <div>
            <label
              htmlFor="fullName"
              className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
            >
              Full Name
            </label>
            <input
              type="text"
              id="fullName"
              name="fullName"
              placeholder="John Kamau"
              autoComplete="name"
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (validated) {
                  setFieldErrors((prev) => ({
                    ...prev,
                    fullName: e.target.value.trim() ? null : 'Full name is required.',
                  }));
                }
              }}
              className={`w-full h-11 px-3.5 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                validated && fieldErrors.fullName
                  ? 'border-rose-500/70 focus:border-rose-500'
                  : 'border-[#222a48] focus:border-[#6f7dff]'
              }`}
              required
            />
            {validated && fieldErrors.fullName && (
              <p className="text-xs text-rose-400 mt-1">{fieldErrors.fullName}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="phone"
              className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
            >
              Phone Number
            </label>
            <input
              type="tel"
              id="phone"
              name="phone"
              placeholder="+254711111111"
              autoComplete="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
                if (validated) {
                  setFieldErrors((prev) => ({
                    ...prev,
                    phone: e.target.value.trim() ? null : 'Phone number is required.',
                  }));
                }
              }}
              className={`w-full h-11 px-3.5 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                validated && fieldErrors.phone
                  ? 'border-rose-500/70 focus:border-rose-500'
                  : 'border-[#222a48] focus:border-[#6f7dff]'
              }`}
              required
            />
            {validated && fieldErrors.phone && (
              <p className="text-xs text-rose-400 mt-1">{fieldErrors.phone}</p>
            )}
          </div>
        </div>

        {/* Row 2: Email Address */}
        <div className="rise" style={{ '--d': '0.35s' }}>
          <label
            htmlFor="email"
            className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
          >
            Email Address
          </label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="name@university.edu"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              const val = e.target.value;
              setEmail(val);
              if (validated) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                setFieldErrors((prev) => ({
                  ...prev,
                  email: !val.trim() || !emailRegex.test(val.trim())
                    ? 'Please enter a valid email address.'
                    : null,
                }));
              }
            }}
            className={`w-full h-11 px-3.5 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
              validated && fieldErrors.email
                ? 'border-rose-500/70 focus:border-rose-500'
                : 'border-[#222a48] focus:border-[#6f7dff]'
            }`}
            required
          />
          {validated && fieldErrors.email && (
            <p className="text-xs text-rose-400 mt-1">{fieldErrors.email}</p>
          )}
        </div>

        {/* Row 3: Password & Confirm Password */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 rise" style={{ '--d': '0.45s' }}>
          <div>
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
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(e) => {
                  const val = e.target.value;
                  setPassword(val);
                  if (validated) {
                    setFieldErrors((prev) => ({
                      ...prev,
                      password: val.length < 8 ? 'Must be at least 8 characters.' : null,
                      confirmPassword: confirmPassword && val !== confirmPassword ? 'Passwords do not match.' : null,
                    }));
                  }
                }}
                className={`w-full h-11 px-3.5 pe-10 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                  validated && fieldErrors.password
                    ? 'border-rose-500/70 focus:border-rose-500'
                    : 'border-[#222a48] focus:border-[#6f7dff]'
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8d97b8] hover:text-[#e8ebf7] p-1 transition-colors cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4 transition-transform active:scale-90" /> : <Eye className="w-4 h-4 transition-transform active:scale-90" />}
              </button>
            </div>
            {validated && fieldErrors.password && (
              <p className="text-xs text-rose-400 mt-1">{fieldErrors.password}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-xs sm:text-sm font-medium text-[#cbd5e1] mb-1.5"
            >
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                placeholder="••••••••••••"
                autoComplete="new-password"
                minLength={8}
                value={confirmPassword}
                onChange={(e) => {
                  const val = e.target.value;
                  setConfirmPassword(val);
                  if (validated) {
                    setFieldErrors((prev) => ({
                      ...prev,
                      confirmPassword: val !== password ? 'Passwords do not match.' : null,
                    }));
                  }
                }}
                className={`w-full h-11 px-3.5 pe-10 rounded-xl bg-[#0c1224] border text-[#e8ebf7] text-sm placeholder:text-[#64748b] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#6f7dff]/25 focus:-translate-y-0.5 ${
                  validated && fieldErrors.confirmPassword
                    ? 'border-rose-500/70 focus:border-rose-500'
                    : 'border-[#222a48] focus:border-[#6f7dff]'
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8d97b8] hover:text-[#e8ebf7] p-1 transition-colors cursor-pointer"
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4 transition-transform active:scale-90" /> : <Eye className="w-4 h-4 transition-transform active:scale-90" />}
              </button>
            </div>
            {validated && fieldErrors.confirmPassword && (
              <p className="text-xs text-rose-400 mt-1">{fieldErrors.confirmPassword}</p>
            )}
          </div>
        </div>

        {/* Password Strength Meter */}
        {password && (
          <div className="pt-1 rise" style={{ '--d': '0.5s' }}>
            <div className="flex justify-between items-center mb-1 text-[11px]">
              <span className="text-[#8d97b8]">
                Strength: <strong className="text-white">{strength.label}</strong>
              </span>
              {confirmPassword && (
                <span className={password === confirmPassword ? 'text-emerald-400 flex items-center gap-1 transition-all' : 'text-rose-400 flex items-center gap-1 transition-all'}>
                  {password === confirmPassword ? (
                    <>
                      <CheckCircle2 className="w-3 h-3 animate-scaleIn" />
                      <span>Passwords match</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3 h-3" />
                      <span>Passwords do not match</span>
                    </>
                  )}
                </span>
              )}
            </div>
            <div className="w-full h-1 bg-[#1a2240] rounded-full overflow-hidden">
              <div className={`h-full transition-all duration-300 ${strength.cls}`} />
            </div>
          </div>
        )}

        {/* Create Account Submit Button */}
        <div className="rise" style={{ '--d': '0.58s' }}>
          <button
            type="submit"
            disabled={isLoading}
            className="btn-shine w-full h-11 sm:h-12 rounded-xl bg-[#5a69f0] hover:bg-[#6f7dff] active:bg-[#4b5bd8] text-white font-semibold text-sm sm:text-base shadow-lg shadow-indigo-500/25 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:shadow-indigo-500/40 active:translate-y-0 active:scale-[0.99] mt-3"
          >
            {isLoading && (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            <span>{isLoading ? 'Creating account…' : 'Create Account'}</span>
          </button>
        </div>

        {/* Already Have an Account Link */}
        <div className="pt-2 text-center text-xs sm:text-sm text-[#8d97b8] rise" style={{ '--d': '0.68s' }}>
          Already have an account?{' '}
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="font-semibold text-[#6f7dff] hover:text-[#8d97ff] transition-colors cursor-pointer select-none hover:underline underline-offset-4"
          >
            Sign in
          </button>
        </div>
      </form>
    </section>
  );
};
