import React, { forwardRef } from 'react';

export const Input = forwardRef(({
  id,
  name,
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  required = false,
  autoComplete,
  disabled = false,
  rightElement,
  className = '',
  ...props
}, ref) => {
  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={id || name}
          className="block text-[13px] font-semibold text-slate-700 mb-1.5"
        >
          {label}
        </label>
      )}
      <div className="relative">
        <input
          ref={ref}
          id={id || name}
          name={name}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          disabled={disabled}
          required={required}
          autoComplete={autoComplete}
          className={`w-full px-3.5 py-2.5 rounded-lg border text-sm text-slate-900 placeholder:text-slate-400 bg-white transition-all duration-150 focus:outline-none ${
            error
              ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
              : 'border-slate-200 hover:border-slate-300 focus:border-[#3B50BA] focus:ring-2 focus:ring-[#3B50BA]/15'
          } ${rightElement ? 'pr-11' : ''} ${className}`}
          {...props}
        />
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center justify-center">
            {rightElement}
          </div>
        )}
      </div>
      {error && (
        <p className="mt-1 text-xs text-red-600 font-medium">
          {error}
        </p>
      )}
    </div>
  );
});

Input.displayName = 'Input';
