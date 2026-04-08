import { Download, Globe, Lock } from "lucide-react";

export function BottomBar({ status, stats, onDownload, onDeploy }) {
  const isComplete = status === "complete";

  return (
    <div
      className="shrink-0 h-12 px-6 flex items-center justify-between
                    border-t border-gray-200 dark:border-gray-800
                    bg-white dark:bg-gray-950"
    >
      <div className="flex items-center gap-4">
        {stats.totalFiles > 0 && (
          <span className="text-xs text-gray-400 dark:text-gray-600">
            {stats.totalFiles} files generated
          </span>
        )}
        {stats.elapsed && (
          <span className="text-xs text-gray-400 dark:text-gray-600">
            {stats.elapsed}s
          </span>
        )}
        {status === "generating" && (
          <span className="text-xs text-violet-500 animate-pulse">
            Agents running...
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onDownload}
          disabled={!isComplete}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     text-xs font-medium transition-colors
                     border border-gray-200 dark:border-gray-700
                     text-gray-600 dark:text-gray-400
                     hover:bg-gray-100 dark:hover:bg-gray-800
                     disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Download size={11} />
          Download ZIP
          <Lock size={9} className="text-gray-400 dark:text-gray-600" />
        </button>

        <button
          onClick={onDeploy}
          disabled={!isComplete}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     text-xs font-medium transition-colors
                     bg-violet-600 hover:bg-violet-700 text-white
                     disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Globe size={11} />
          Deploy Live
          <Lock size={9} className="text-white/60" />
        </button>
      </div>
    </div>
  );
}
