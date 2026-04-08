import { Sun, Moon, Zap, LogIn } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

export function Header({ onSignIn }) {
  const { isDark, toggle } = useTheme();

  return (
    <header
      className="shrink-0 h-14 px-6 flex items-center justify-between
                       border-b border-gray-200 dark:border-gray-800
                       bg-white dark:bg-gray-950"
    >
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
          <Zap size={14} className="text-white" />
        </div>
        <span className="font-semibold text-gray-900 dark:text-white tracking-tight">
          Forge
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500 hidden sm:block">
          AI full-stack generator
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggle}
          className="w-8 h-8 rounded-lg flex items-center justify-center
                     text-gray-500 hover:text-gray-900 hover:bg-gray-100
                     dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-800
                     transition-colors"
          aria-label="Toggle theme"
        >
          {isDark ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <button
          onClick={onSignIn}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                     font-medium text-gray-700 dark:text-gray-300
                     hover:bg-gray-100 dark:hover:bg-gray-800
                     border border-gray-200 dark:border-gray-700
                     transition-colors"
        >
          <LogIn size={13} />
          Sign in
        </button>
      </div>
    </header>
  );
}
