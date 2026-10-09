import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { Alert } from '../ui/Alert';
import { ForgotPasswordModal } from './ForgotPasswordModal';
import { useAuth } from '../../context/AuthContext';
import { GoogleLogin } from '@react-oauth/google';

export const LoginForm = () => {
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();

  const [identifier, setIdentifier] = useState('alex.morgan@university.edu');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const [fieldErrors, setFieldErrors] = useState({});
  const [authError, setAuthError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  const handleGoogleSuccess = async (credentialResponse) => {
  setIsLoading(true);
  try {
    const res = await loginWithGoogle(credentialResponse.credential);
    if (res?.user?.dashboardUrl) {
      navigate(res.user.dashboardUrl);
    } else {
      navigate('/agent/dashboard');
    }
  } catch (err) {
    setAuthError(err.message || 'Google authentication failed.');
  } finally {
    setIsLoading(false);
  }
};

  const validate = () => {
    const errors = {};
    if (!identifier.trim()) {
      errors.identifier = 'Email is required';
    }
    if (!password) {
      errors.password = 'Password is required';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);

    if (!validate()) {
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
      setAuthError(err.message || 'Invalid email/username or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="w-full max-w-[430px] bg-white rounded-3xl p-8 sm:p-10 figma-card-shadow border border-slate-100/80 transition-all">
        {/* Form Header */}
        <div className="mb-7">
          <h2 className="text-[26px] font-bold text-slate-900 tracking-tight leading-tight">
            Welcome back
          </h2>
          <p className="mt-1.5 text-sm text-slate-500 font-normal">
            Sign in to your VerifyMesh account
          </p>
        </div>

        {/* Invalid Credentials Error Banner */}
        {authError && (
          <Alert
            type="error"
            message={authError}
            onClose={() => setAuthError(null)}
            className="mb-5"
          />
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} noValidate>
          {/* Email */}
          <div className="mb-4 sm:mb-5">
            <Input
              id="identifier"
              name="identifier"
              label="Email"
              type="text"
              placeholder="alex.morgan@university.edu"
              value={identifier}
              onChange={(e) => {
                setIdentifier(e.target.value);
                if (fieldErrors.identifier) {
                  setFieldErrors((prev) => ({ ...prev, identifier: null }));
                }
              }}
              error={fieldErrors.identifier}
              autoComplete="username"
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
                if (fieldErrors.password) {
                  setFieldErrors((prev) => ({ ...prev, password: null }));
                }
              }}
              error={fieldErrors.password}
              autoComplete="current-password"
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

          {/* Remember Me & Forgot Password Row */}
          <div className="flex items-center justify-between mb-6 pt-0.5">
            <Checkbox
              id="remember-me"
              name="remember-me"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              label="Remember me"
            />

            <button
              type="button"
              onClick={() => setIsForgotModalOpen(true)}
              className="text-xs sm:text-[13px] font-semibold text-[#3B50BA] hover:text-[#283685] transition-colors cursor-pointer select-none"
            >
              Forgot password?
            </button>
          </div>

          {/* Sign In Button */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            className="w-full py-3 text-sm sm:text-base font-semibold tracking-wide"
          >
            Sign In
          </Button>

          <div className="mt-6 text-center text-sm text-slate-500">
            Don't have an account?{' '}
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="font-semibold text-[#3B50BA] hover:text-[#283685] transition-colors cursor-pointer select-none"
            >
              Create an account
            </button>
          </div>
        </form>

        {/* Or continue with divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-3 text-slate-400 font-medium">Or continue with</span>
          </div>
        </div>

        {/* Google Sign-In Button */}
        <div className="flex justify-center w-full">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setAuthError('Google Sign-In was cancelled or failed.')}
            shape="pill"
            size="large"
            width="380"
          />
        </div>
      </div>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
      />
    </>
  );
};
