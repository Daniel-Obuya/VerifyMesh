import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export const ThemeToggle = ({ className = '', showLabel = false }) => {
  const { theme, isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      className={`p-2 rounded-xl transition-all flex items-center gap-2 cursor-pointer ${
        isDark
          ? 'bg-[#131d36] text-amber-300 hover:text-amber-200 hover:bg-[#1b284a] border border-[#232f52]'
          : 'bg-slate-100 text-indigo-600 hover:text-indigo-700 hover:bg-slate-200 border border-slate-300 shadow-xs'
      } ${className}`}
    >
      {isDark ? (
        <Sun className="w-4 h-4 transition-transform duration-300 rotate-0 hover:rotate-45" />
      ) : (
        <Moon className="w-4 h-4 transition-transform duration-300 -rotate-12 hover:rotate-0" />
      )}
      {showLabel && (
        <span className="text-xs font-semibold select-none">
          {isDark ? 'Light Mode' : 'Dark Mode'}
        </span>
      )}
    </button>
  );
};

