import { CheckCircle, Circle, XCircle, Loader, GitBranch } from "lucide-react";
import { AGENTS } from "../hooks/useBuilder";

const STATUS = {
  waiting: {
    icon: Circle,
    color: "text-gray-300 dark:text-gray-700",
    bg: "bg-gray-50 dark:bg-gray-900",
    border: "border-gray-200 dark:border-gray-800",
    dot: "bg-gray-300 dark:bg-gray-700",
  },
  running: {
    icon: Loader,
    color: "text-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950/30",
    border: "border-violet-200 dark:border-violet-800",
    dot: "bg-violet-500",
    spin: true,
  },
  done: {
    icon: CheckCircle,
    color: "text-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    border: "border-emerald-200 dark:border-emerald-800",
    dot: "bg-emerald-500",
  },
  error: {
    icon: XCircle,
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-950/30",
    border: "border-red-200 dark:border-red-800",
    dot: "bg-red-500",
  },
};

function AgentRow({ agent, data, isLast }) {
  const cfg = STATUS[data.status];
  const Icon = cfg.icon;

  return (
    <div className="relative">
      <div
        className={`p-3 rounded-lg border transition-all duration-300 ${cfg.bg} ${cfg.border}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon
              size={13}
              className={`${cfg.color} ${
                cfg.spin ? "animate-spin" : ""
              } shrink-0`}
            />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {agent.label}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {data.duration && (
              <span className="text-xs text-gray-400 dark:text-gray-600">
                {data.duration}s
              </span>
            )}
            {data.status === "running" && (
              <div
                className={`w-1.5 h-1.5 rounded-full ${cfg.dot} animate-pulse`}
              />
            )}
          </div>
        </div>

        {data.status === "running" && (
          <p className="text-xs text-violet-500 dark:text-violet-400 mt-1 ml-5">
            {agent.description}
          </p>
        )}

        {data.status === "done" && data.files.length > 0 && (
          <p className="text-xs text-gray-400 dark:text-gray-600 mt-1 ml-5">
            {data.files.length} files
          </p>
        )}
      </div>

      {!isLast && (
        <div className="absolute left-[1.35rem] top-full w-px h-2 bg-gray-200 dark:bg-gray-800" />
      )}
    </div>
  );
}

export function AgentPipeline({ agents, stats }) {
  const doneCount = Object.values(agents).filter(
    (a) => a.status === "done"
  ).length;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch size={13} className="text-gray-400" />
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Pipeline
        </span>
      </div>

      <div className="flex flex-col gap-2 flex-1">
        {AGENTS.map((agent, i) => (
          <AgentRow
            key={agent.id}
            agent={agent}
            data={agents[agent.id]}
            isLast={i === AGENTS.length - 1}
          />
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-400 dark:text-gray-600">Agents</span>
          <span className="text-gray-600 dark:text-gray-400 font-mono">
            {doneCount}/6
          </span>
        </div>
        {stats.totalFiles > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-400 dark:text-gray-600">Files</span>
            <span className="text-gray-600 dark:text-gray-400 font-mono">
              {stats.totalFiles}
            </span>
          </div>
        )}
        {stats.elapsed && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-400 dark:text-gray-600">Time</span>
            <span className="text-gray-600 dark:text-gray-400 font-mono">
              {stats.elapsed}s
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
