import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => authService.getStoredUser());
  const [token, setToken] = useState(() => authService.getStoredToken());
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const verifySession = async () => {
      const storedToken = authService.getStoredToken();
      if (storedToken) {
        try {
          const res = await authService.getCurrentUser();
          if (res?.user) {
            setUser(res.user);
          }
        } catch {
          // Token expired or invalid
          authService.logout();
          setUser(null);
          setToken(null);
        }
      }
      setIsInitializing(false);
    };

    verifySession();
  }, []);

  const login = async ({ identifier, password, rememberMe }) => {
    const res = await authService.login({ identifier, password, rememberMe });
    if (res?.user && res?.token) {
      setUser(res.user);
      setToken(res.token);
    }
    return res;
  };

  const loginWithGoogle = async (credential) => {
    const res = await authService.googleLogin(credential);
    if (res?.user && res?.token) {
      setUser(res.user);
      setToken(res.token);
    }
    return res;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
    setToken(null);
  };

  const forgotPassword = async (email) => {
    return authService.forgotPassword(email);
  };

  const value = {
    user,
    token,
    role: user?.role || null,
    isAuthenticated: Boolean(user && token),
    isInitializing,
    login,
    loginWithGoogle,
    logout,
    forgotPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
