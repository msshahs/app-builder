import { CheckCircle, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";

export function ReviewPanel({ reviewResult }) {
  if (!reviewResult) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3">
        <ShieldCheck size={24} className="text-gray-300 dark:text-gray-700" />
        <p className="text-sm text-gray-400 dark:text-gray-600">
          Review results will appear after generation
        </p>
      </div>
    );
  }

  const critical =
    reviewResult.issues?.filter((i) => i.severity === "critical") || [];
  const warnings =
    reviewResult.issues?.filter((i) => i.severity === "warning") || [];

  return (
    <div className="h-full overflow-y-auto p-5 space-y-5">
      <div
        className={`flex items-center gap-3 p-4 rounded-xl border
        ${
          reviewResult.passed
            ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800"
            : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800"
        }`}
      >
        {reviewResult.passed ? (
          <CheckCircle size={18} className="text-emerald-500 shrink-0" />
        ) : (
          <XCircle size={18} className="text-red-500 shrink-0" />
        )}
        <div>
          <p
            className={`text-sm font-medium
            ${
              reviewResult.passed
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-red-700 dark:text-red-400"
            }`}
          >
            {reviewResult.passed ? "All checks passed" : "Issues detected"}
          </p>
          {reviewResult.summary && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
              {reviewResult.summary}
            </p>
          )}
        </div>
      </div>

      {critical.length > 0 && (
        <div>
          <p
            className="text-xs font-medium text-gray-500 dark:text-gray-400
                        uppercase tracking-wider mb-2"
          >
            Critical Issues ({critical.length})
          </p>
          <div className="space-y-2">
            {critical.map((issue, i) => (
              <div
                key={i}
                className="p-3 rounded-lg border
                           bg-red-50 dark:bg-red-950/30
                           border-red-200 dark:border-red-800"
              >
                <div className="flex items-start gap-2">
                  <XCircle size={12} className="text-red-500 mt-0.5 shrink-0" />
                  <div className="space-y-1">
                    <p className="text-xs font-mono text-red-600 dark:text-red-400">
                      {issue.file}
                    </p>
                    <p className="text-xs text-gray-700 dark:text-gray-300">
                      {issue.issue}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500">
                      Fix: {issue.fix}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div>
          <p
            className="text-xs font-medium text-gray-500 dark:text-gray-400
                        uppercase tracking-wider mb-2"
          >
            Warnings ({warnings.length})
          </p>
          <div className="space-y-2">
            {warnings.map((issue, i) => (
              <div
                key={i}
                className="p-3 rounded-lg border
                           bg-amber-50 dark:bg-amber-950/30
                           border-amber-200 dark:border-amber-800"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle
                    size={12}
                    className="text-amber-500 mt-0.5 shrink-0"
                  />
                  <div className="space-y-1">
                    <p className="text-xs font-mono text-amber-600 dark:text-amber-400">
                      {issue.file}
                    </p>
                    <p className="text-xs text-gray-700 dark:text-gray-300">
                      {issue.issue}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
