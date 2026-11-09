import React from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { RegisterForm } from '../components/auth/RegisterForm';

export const RegisterPage = () => {
  return (
    <AuthLayout isRegister={true}>
      <RegisterForm />
    </AuthLayout>
  );
};
