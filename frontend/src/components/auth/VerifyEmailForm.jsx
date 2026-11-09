import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const VerifyEmailForm = ({ email, onBack }) => {
  const navigate = useNavigate();
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const inputRefs = useRef([]);

  // Auto-focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  // Countdown timer for resend cooldown
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleDigitChange = (index, value) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const updated = [...digits];
    updated[index] = digit;
    setDigits(updated);
    setError(null);

    // Auto-advance to next input field
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    // Backspace with empty current input moves to previous input
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const updated = ['', '', '', '', '', ''];
    pasted.split('').forEach((char, i) => {
      updated[i] = char;
    });
    setDigits(updated);
    const nextIndex = Math.min(pasted.length, 5);
    inputRefs.current[nextIndex]?.focus();
  };

  const getCode = () => digits.join('');

  const handleVerify = async (e) => {
    e.preventDefault();
    const code = getCode();
    if (code.length < 6) {
      setError('Please enter the complete 6-digit verification code.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Verification failed. Please try again.');
      }

      setSuccess('Email verified successfully! Redirecting you to sign in...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.message || 'Verification failed. Please try again.');
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    setError(null);

    try {
      const response = await fetch('/api/auth/resend-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to resend code.');
      }

      setSuccess('A new verification code has been dispatched to your inbox.');
      setCooldown(60);
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(err.message || 'Failed to resend code.');
    }
  };

  // Mask email for privacy: john.kamau@example.com → jo*****@example.com
  const maskedEmail = email
    ? email.replace(/^(.{2})(.*)(@.*)$/, (_, a, b, c) => a + '*'.repeat(Math.max(b.length, 3)) + c)
    : '';

  return (
    <section className="auth-card card-in text-center">
      {/* Header Badge */}
      <div
        className="logo mb-3 mx-auto rise d-flex align-items-center justify-content-center"
        style={{ width: '52px', height: '52px', fontSize: '1.4rem', '--d': '.1s' }}
      >
        <i className="bi bi-envelope-check" />
      </div>

      <h2 className="fw-bold fs-2 mb-2 rise text-white" style={{ '--d': '.2s' }}>
        Check your email
      </h2>
      <p className="text-body-secondary mb-4 rise" style={{ '--d': '.3s' }}>
        We sent a 6-digit security code to <br />
        <span className="fw-semibold text-white">{maskedEmail}</span>
      </p>

      {/* Alerts */}
      {error && (
        <div
          className="alert alert-danger py-2 px-3 mb-4 text-start d-flex align-items-center justify-content-between"
          role="alert"
        >
          <span>{error}</span>
          <button
            type="button"
            className="btn-close btn-close-white ms-2"
            aria-label="Close"
            onClick={() => setError(null)}
          />
        </div>
      )}

      {success && (
        <div className="alert alert-success py-2 px-3 mb-4 text-start" role="alert">
          <i className="bi bi-check-circle-fill me-2" />
          {success}
        </div>
      )}

      {/* 6-Digit OTP Form */}
      <form onSubmit={handleVerify}>
        <div className="d-flex justify-content-center gap-2 mb-4 rise" style={{ '--d': '.4s' }}>
          {digits.map((digit, index) => (
            <input
              key={index}
              ref={(el) => (inputRefs.current[index] = el)}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleDigitChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={handlePaste}
              className={`otp-digit-input ${digit ? 'filled' : ''}`}
              aria-label={`Digit ${index + 1}`}
              autoComplete="one-time-code"
            />
          ))}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary w-100 mb-4 rise btn-shine d-flex align-items-center justify-content-center"
          style={{ '--d': '.5s' }}
          disabled={isLoading}
        >
          {isLoading && (
            <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
          )}
          <span className="label">{isLoading ? 'Verifying...' : 'Verify Email'}</span>
        </button>
      </form>

      {/* Resend Action */}
      <div className="text-body-secondary mb-3 rise" style={{ '--d': '.6s', fontSize: '0.875rem' }}>
        Didn't receive the code?{' '}
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0}
          className={`bg-transparent border-0 p-0 fw-semibold ${
            cooldown > 0 ? 'text-muted' : 'link-accent'
          }`}
          style={{ cursor: cooldown > 0 ? 'not-allowed' : 'pointer' }}
        >
          {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
        </button>
      </div>

      {/* Back to Registration */}
      <div className="rise" style={{ '--d': '.7s' }}>
        <button
          type="button"
          onClick={onBack ? onBack : () => navigate('/register')}
          className="text-muted hover-underline bg-transparent border-0 p-0"
          style={{ fontSize: '0.82rem', cursor: 'pointer' }}
        >
          ← Back to sign up
        </button>
      </div>
    </section>
  );
};
