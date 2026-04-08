import { useState } from "react";
import { ArrowRight, RotateCcw, Loader } from "lucide-react";

const EXAMPLES = [
  "Build me a task management app with user authentication and MongoDB",
  "E-commerce store with Stripe payments",
  "Real-time chat app with rooms",
];

export function PromptInput({ onGenerate, onReset, status }) {
  const [prompt, setPrompt] = useState("");
  const isGenerating = status === "generating";
  const isComplete = status === "complete";
  const isError = status === "error";

  const handleSubmit = () => {
    if (!prompt.trim() || isGenerating) return;
    onGenerate(prompt.trim());
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-6 py-5">
      <div className="text-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          What do you want to build?
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Describe your app — agents will plan, code, and deploy it
          automatically
        </p>
      </div>

      <div className="relative">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
          placeholder="Build me a task management app with user authentication, MongoDB, and a React dashboard..."
          disabled={isGenerating}
          rows={3}
          className="w-full px-4 py-3 pr-36 rounded-xl text-sm
                     bg-white dark:bg-gray-900
                     border border-gray-200 dark:border-gray-700
                     text-gray-900 dark:text-gray-100
                     placeholder-gray-400 dark:placeholder-gray-600
                     focus:outline-none focus:ring-2 focus:ring-violet-500
                     focus:border-transparent resize-none
                     disabled:opacity-60 disabled:cursor-not-allowed
                     transition-all"
        />

        <div className="absolute bottom-3 right-3 flex items-center gap-2">
          {(isComplete || isError) && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                         text-xs font-medium
                         text-gray-600 dark:text-gray-400
                         bg-gray-100 dark:bg-gray-800
                         hover:bg-gray-200 dark:hover:bg-gray-700
                         transition-colors"
            >
              <RotateCcw size={11} />
              Reset
            </button>
          )}

          <button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isGenerating}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg
                       text-xs font-medium text-white
                       bg-violet-600 hover:bg-violet-700
                       disabled:opacity-40 disabled:cursor-not-allowed
                       transition-colors"
          >
            {isGenerating ? (
              <>
                <Loader size={11} className="animate-spin" /> Building...
              </>
            ) : (
              <>
                <ArrowRight size={11} /> Build
              </>
            )}
          </button>
        </div>
      </div>

      {status === "idle" && (
        <div className="mt-3 flex flex-wrap gap-2 justify-center">
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex)}
              className="text-xs px-3 py-1.5 rounded-full
                         border border-gray-200 dark:border-gray-700
                         text-gray-500 dark:text-gray-400
                         hover:border-violet-300 dark:hover:border-violet-700
                         hover:text-violet-600 dark:hover:text-violet-400
                         transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-2">
        Press ⌘ + Enter to build
      </p>
    </div>
  );
}
