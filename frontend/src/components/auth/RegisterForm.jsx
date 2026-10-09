import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Alert } from '../ui/Alert';
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

  const [fieldErrors, setFieldErrors] = useState({});
  const [authError, setAuthError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // When set, swaps registration form for OTP verification screen
  const [pendingEmail, setPendingEmail] = useState(null);

  const validate = () => {
    const errors = {};
    if (!fullName.trim()) {
      errors.fullName = 'Full name is required.';
    }
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
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
    setSuccessMessage(null);

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
          email: email.trim(),
          phone: phone.trim(),
          password,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Something went wrong. Please try again.');
      }

      // Switch to OTP verification screen
      setPendingEmail(email.trim().toLowerCase());
    } catch (err) {
      setAuthError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // If registration succeeded, show OTP verification form
  if (pendingEmail) {
    return <VerifyEmailForm email={pendingEmail} />;
  }

  return (
    <div className="w-full max-w-[430px] bg-white rounded-3xl p-8 sm:p-10 figma-card-shadow border border-slate-100/80 transition-all">
      {/* Form Header */}
      <div className="mb-7">
        <h2 className="text-[26px] font-bold text-slate-900 tracking-tight leading-tight">
          Create your account
        </h2>
        <p className="mt-1.5 text-sm text-slate-500 font-normal">
          Join VerifyMesh and build your professional competency profile.
        </p>
      </div>

      {/* Messages */}
      {authError && (
        <Alert
          type="error"
          message={authError}
          onClose={() => setAuthError(null)}
          className="mb-5"
        />
      )}
      {successMessage && (
        <Alert
          type="success"
          message={successMessage}
          onClose={() => setSuccessMessage(null)}
          className="mb-5"
        />
      )}

      {/* Registration Form */}
      <form onSubmit={handleSubmit} noValidate>
        {/* Full Name */}
        <div className="mb-4">
          <Input
            id="fullName"
            name="fullName"
            label="Full Name"
            type="text"
            placeholder="John Kamau"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              if (fieldErrors.fullName) setFieldErrors((prev) => ({ ...prev, fullName: null }));
            }}
            error={fieldErrors.fullName}
            required
          />
        </div>

        {/* Email */}
        <div className="mb-4">
          <Input
            id="email"
            name="email"
            label="Email"
            type="email"
            placeholder="john.kamau@example.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: null }));
            }}
            error={fieldErrors.email}
            required
          />
        </div>

        {/* Phone */}
        <div className="mb-4">
          <Input
            id="phone"
            name="phone"
            label="Phone Number"
            type="tel"
            placeholder="+254711111111"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value);
              if (fieldErrors.phone) setFieldErrors((prev) => ({ ...prev, phone: null }));
            }}
            error={fieldErrors.phone}
            required
          />
        </div>

        {/* Password */}
        <div className="mb-4">
          <Input
            id="password"
            name="password"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: null }));
            }}
            error={fieldErrors.password}
            required
            rightElement={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-slate-400 hover:text-slate-600 focus:outline-none p-1 transition-colors cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? (
                  <Eye className="w-[18px] h-[18px]" strokeWidth={1.8} />
                ) : (
                  <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.8} />
                )}
              </button>
            }
          />
        </div>

        {/* Confirm Password */}
        <div className="mb-6">
          <Input
            id="confirmPassword"
            name="confirmPassword"
            label="Confirm Password"
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="••••••••••••"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (fieldErrors.confirmPassword) setFieldErrors((prev) => ({ ...prev, confirmPassword: null }));
            }}
            error={fieldErrors.confirmPassword}
            required
            rightElement={
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="text-slate-400 hover:text-slate-600 focus:outline-none p-1 transition-colors cursor-pointer"
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showConfirmPassword ? (
                  <Eye className="w-[18px] h-[18px]" strokeWidth={1.8} />
                ) : (
                  <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.8} />
                )}
              </button>
            }
          />
        </div>

        {/* Create Account Button */}
        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          className="w-full py-3 text-sm sm:text-base font-semibold tracking-wide"
        >
          {isLoading ? 'Creating account...' : 'Create Account'}
        </Button>

        <div className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{' '}
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="font-semibold text-[#3B50BA] hover:text-[#283685] transition-colors cursor-pointer select-none"
          >
            Sign in
          </button>
        </div>
      </form>
    </div>
  );
};
