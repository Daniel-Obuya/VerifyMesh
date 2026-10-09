import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Alert } from '../ui/Alert';
import { useAuth } from '../../context/AuthContext';

export const ForgotPasswordModal = ({ isOpen, onClose }) => {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setMessage(null);

    try {
      const res = await forgotPassword(email.trim());
      setMessage(res?.message || 'Password reset link sent! Check your inbox.');
      setEmail('');
    } catch (err) {
      setError(err?.message || 'Failed to send reset instructions. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setMessage(null);
    setError(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Reset password">
      <p className="text-xs sm:text-sm text-slate-500 mb-4">
        Enter the email address associated with your VerifyMesh account. We will send you instructions to reset your password.
      </p>

      {error && <Alert type="error" message={error} className="mb-4" />}
      {message && <Alert type="success" message={message} className="mb-4" />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          id="reset-email"
          label="Email address"
          type="email"
          placeholder="alex.morgan@university.edu"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isLoading}>
            Send link
          </Button>
        </div>
      </form>
    </Modal>
  );
};
