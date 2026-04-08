import { useState } from "react";
import { useBuilder } from "./hooks/useBuilder";
import { ThemeProvider } from "./context/ThemeContext";
import { Header } from "./components/Header";
import { PromptInput } from "./components/PromptInput";
import { AgentPipeline } from "./components/AgentPipeline";
import { LogStream } from "./components/LogStream";
import { FileTree } from "./components/FileTree";
import { CodeViewer } from "./components/CodeViewer";
import { ReviewPanel } from "./components/ReviewPanel";
import { BottomBar } from "./components/BottomBar";
import { AuthModal } from "./components/AuthModal";

const TABS = [
  { id: "logs", label: "Agent Logs" },
  { id: "code", label: "Code" },
  { id: "review", label: "Review" },
];

function ForgeApp() {
  const builder = useBuilder();
  const [authModal, setAuthModal] = useState({
    open: false,
    reason: "default",
  });

  const openAuth = (reason) => setAuthModal({ open: true, reason });
  const closeAuth = () => setAuthModal({ open: false, reason: "default" });

  return (
    <div
      className="h-screen flex flex-col overflow-hidden
                    bg-gray-50 dark:bg-gray-950"
    >
      <Header onSignIn={() => openAuth("default")} />

      <PromptInput
        onGenerate={builder.generate}
        onReset={builder.reset}
        status={builder.status}
      />

      <div className="flex-1 flex overflow-hidden px-4 pb-0 gap-3 min-h-0">
        {/* Left — Agent Pipeline */}
        <div className="w-48 shrink-0 panel p-4 overflow-hidden">
          <AgentPipeline agents={builder.agents} stats={builder.stats} />
        </div>

        {/* Center — Main Panel */}
        <div className="flex-1 panel flex flex-col overflow-hidden min-w-0">
          {/* Tabs */}
          <div className="shrink-0 flex border-b border-gray-200 dark:border-gray-800 px-4">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => builder.setActiveTab(tab.id)}
                className={`px-4 py-3 text-xs font-medium border-b-2 -mb-px
                            transition-colors
                            ${
                              builder.activeTab === tab.id
                                ? "tab-active"
                                : "tab-inactive"
                            }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden p-4">
            {builder.activeTab === "logs" && (
              <LogStream logs={builder.logs} status={builder.status} />
            )}

            {builder.activeTab === "code" && (
              <div className="h-full flex gap-3">
                <div className="w-52 shrink-0 panel overflow-hidden rounded-lg">
                  <FileTree
                    files={builder.generatedFiles}
                    selectedFile={builder.selectedFile}
                    onSelect={builder.setSelectedFile}
                  />
                </div>
                <div className="flex-1 overflow-hidden min-w-0">
                  <CodeViewer
                    selectedFile={builder.selectedFile}
                    generatedFiles={builder.generatedFiles}
                    fileContents={builder.fileContents}
                  />
                </div>
              </div>
            )}

            {builder.activeTab === "review" && (
              <ReviewPanel reviewResult={builder.reviewResult} />
            )}
          </div>
        </div>
      </div>

      <BottomBar
        status={builder.status}
        stats={builder.stats}
        onDownload={() => openAuth("download")}
        onDeploy={() => openAuth("deploy")}
      />

      <AuthModal
        isOpen={authModal.open}
        onClose={closeAuth}
        reason={authModal.reason}
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ForgeApp />
    </ThemeProvider>
  );
}
