import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Alert } from '../ui/Alert';

export const VerifyEmailForm = ({ email }) => {
  const navigate = useNavigate();
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const inputRefs = useRef([]);

  // Focus the first input on mount
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
    // Allow only single digit 0-9
    const digit = value.replace(/\D/g, '').slice(-1);
    const updated = [...digits];
    updated[index] = digit;
    setDigits(updated);
    setError(null);

    // Auto-advance to next input
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    // On Backspace with empty input, go back to previous
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const updated = ['', '', '', '', '', ''];
    pasted.split('').forEach((char, i) => { updated[i] = char; });
    setDigits(updated);
    // Focus the last filled input or the next empty one
    const nextIndex = Math.min(pasted.length, 5);
    inputRefs.current[nextIndex]?.focus();
  };

  const getCode = () => digits.join('');

  const handleVerify = async (e) => {
    e.preventDefault();
    const code = getCode();
    if (code.length < 6) {
      setError('Please enter the complete 6-digit code.');
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

      setSuccess('Email verified! Redirecting you to sign in...');
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.message);
      // Clear digit inputs on wrong code
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

      setSuccess('A new code has been sent to your email.');
      setCooldown(60); // 60-second cooldown
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(err.message);
    }
  };

  // Mask email: john.doe@gmail.com → jo*****@gmail.com
  const maskedEmail = email.replace(/^(.{2})(.*)(@.*)$/, (_, a, b, c) => a + '*'.repeat(b.length) + c);

  return (
    <div className="w-full max-w-[430px] bg-white rounded-3xl p-8 sm:p-10 figma-card-shadow border border-slate-100/80">
      {/* Header */}
      <div className="mb-7 text-center">
        <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3B50BA" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
        </div>
        <h2 className="text-[26px] font-bold text-slate-900 tracking-tight">Check your email</h2>
        <p className="mt-2 text-sm text-slate-500">
          We sent a 6-digit code to <br />
          <span className="font-semibold text-slate-700">{maskedEmail}</span>
        </p>
      </div>

      {/* Alerts */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} className="mb-5" />
      )}
      {success && (
        <Alert type="success" message={success} onClose={() => setSuccess(null)} className="mb-5" />
      )}

      {/* OTP Input Form */}
      <form onSubmit={handleVerify}>
        <div className="flex justify-center gap-3 mb-7">
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
              className={`w-12 h-14 text-center text-xl font-bold rounded-xl border-2 outline-none transition-all
                ${digit ? 'border-[#3B50BA] bg-blue-50 text-[#3B50BA]' : 'border-slate-200 text-slate-800'}
                focus:border-[#3B50BA] focus:ring-2 focus:ring-blue-100`}
              aria-label={`Digit ${index + 1}`}
            />
          ))}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isLoading}
          className="w-full py-3 text-sm sm:text-base font-semibold tracking-wide"
        >
          {isLoading ? 'Verifying...' : 'Verify Email'}
        </Button>
      </form>

      {/* Resend */}
      <div className="mt-5 text-center text-sm text-slate-500">
        Didn't receive the code?{' '}
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0}
          className={`font-semibold transition-colors cursor-pointer select-none
            ${cooldown > 0
              ? 'text-slate-400 cursor-not-allowed'
              : 'text-[#3B50BA] hover:text-[#283685]'}`}
        >
          {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
        </button>
      </div>

      {/* Back to Register */}
      <div className="mt-3 text-center text-sm text-slate-500">
        <button
          type="button"
          onClick={() => navigate('/register')}
          className="text-slate-400 hover:text-slate-600 transition-colors text-xs cursor-pointer"
        >
          ← Back to sign up
        </button>
      </div>
    </div>
  );
};
