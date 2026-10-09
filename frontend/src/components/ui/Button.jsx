import React from 'react';

export const Button = ({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  onClick,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed select-none';

  const variantStyles = {
    primary: 'bg-[#3B50BA] hover:bg-[#31429E] active:bg-[#283685] text-white shadow-sm focus:ring-2 focus:ring-[#3B50BA]/40 focus:ring-offset-1',
    secondary: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 focus:ring-2 focus:ring-slate-300',
    ghost: 'bg-transparent hover:bg-slate-100 text-slate-600',
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-4 py-3 text-sm sm:text-base font-semibold',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${variantStyles[variant] || variantStyles.primary} ${sizeStyles[size] || sizeStyles.md} ${className}`}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg
            className="animate-spin h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Signing in...</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
};
