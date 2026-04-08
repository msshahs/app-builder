import { X, Globe, GitBranch } from "lucide-react";

export function AuthModal({ isOpen, onClose, reason }) {
  if (!isOpen) return null;

  const REASON_TEXT = {
    download: "Sign in to download your generated app as a ZIP file",
    deploy: "Sign in to deploy your app and get a live URL",
    default: "Sign in to access this feature",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative w-full max-w-sm panel p-6 animate-slide-up">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-7 h-7 rounded-lg
                     flex items-center justify-center
                     text-gray-400 hover:text-gray-600
                     dark:text-gray-600 dark:hover:text-gray-400
                     hover:bg-gray-100 dark:hover:bg-gray-800
                     transition-colors"
        >
          <X size={14} />
        </button>

        <div className="text-center mb-6">
          <div
            className="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-950
                          flex items-center justify-center mx-auto mb-3"
          >
            <span className="text-xl">⚡</span>
          </div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            Sign in to continue
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {REASON_TEXT[reason] || REASON_TEXT.default}
          </p>
        </div>

        <div className="space-y-2">
          <button
            className="w-full flex items-center justify-center gap-2
                   px-4 py-2.5 rounded-lg border text-sm font-medium
                   border-gray-200 dark:border-gray-700
                   text-gray-700 dark:text-gray-300
                   hover:bg-gray-50 dark:hover:bg-gray-800
                   transition-colors"
          >
            <GitBranch size={15} />
            Continue with GitHub
          </button>

          <button
            className="w-full flex items-center justify-center gap-2
                             px-4 py-2.5 rounded-lg border text-sm font-medium
                             border-gray-200 dark:border-gray-700
                             text-gray-700 dark:text-gray-300
                             hover:bg-gray-50 dark:hover:bg-gray-800
                             transition-colors"
          >
            <Github size={15} />
            Continue with GitHub
          </button>
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-4">
          Free to use — no credit card required
        </p>
      </div>
    </div>
  );
}
