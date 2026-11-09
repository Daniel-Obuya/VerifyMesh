import React from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { AuthCard } from '../components/auth/AuthCard';

export const LoginPage = () => {
  return (
    <AuthLayout>
      <AuthCard />
    </AuthLayout>
  );
};
