import { useEffect, useRef } from "react";
import { Terminal } from "lucide-react";

const LOG_STYLE = {
  info: { color: "text-gray-400 dark:text-gray-500", prefix: "→" },
  success: { color: "text-emerald-500 dark:text-emerald-400", prefix: "✓" },
  error: { color: "text-red-500 dark:text-red-400", prefix: "✗" },
  warning: { color: "text-amber-500 dark:text-amber-400", prefix: "⚠" },
  file: { color: "text-violet-400 dark:text-violet-500", prefix: " " },
};

export function LogStream({ logs, status }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3">
        <Terminal size={24} className="text-gray-300 dark:text-gray-700" />
        <p className="text-sm text-gray-400 dark:text-gray-600">
          {status === "idle"
            ? "Agent logs will stream here in real time"
            : "Starting pipeline..."}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-950 rounded-lg p-4">
      <div className="space-y-0.5 font-mono text-xs">
        {logs.map((log) => {
          const style = LOG_STYLE[log.type] || LOG_STYLE.info;
          return (
            <div
              key={log.id}
              className="flex gap-3 leading-relaxed animate-fade-in"
            >
              <span className="text-gray-700 shrink-0 tabular-nums">
                {log.time}
              </span>
              <span className={`shrink-0 w-3 ${style.color}`}>
                {style.prefix}
              </span>
              <span className={style.color}>{log.message}</span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
