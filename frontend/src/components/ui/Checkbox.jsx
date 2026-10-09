import React from 'react';

export const Checkbox = ({
  id,
  name,
  checked,
  onChange,
  label,
  disabled = false,
  className = '',
  ...props
}) => {
  return (
    <label
      htmlFor={id || name}
      className={`inline-flex items-center gap-2 cursor-pointer select-none ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
    >
      <input
        type="checkbox"
        id={id || name}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="w-4 h-4 rounded border-slate-300 text-[#3B50BA] focus:ring-[#3B50BA]/30 focus:ring-2 focus:ring-offset-0 transition-colors cursor-pointer accent-[#3B50BA]"
        {...props}
      />
      {label && (
        <span className="text-xs sm:text-[13px] text-slate-600 font-normal">
          {label}
        </span>
      )}
    </label>
  );
};
