import Editor from "@monaco-editor/react";
import { useTheme } from "../context/ThemeContext";
import { FileCode2 } from "lucide-react";

function getLanguage(path) {
  if (!path) return "plaintext";
  if (path.endsWith(".jsx")) return "javascript";
  if (path.endsWith(".js")) return "javascript";
  if (path.endsWith(".ts")) return "typescript";
  if (path.endsWith(".tsx")) return "typescript";
  if (path.endsWith(".css")) return "css";
  if (path.endsWith(".json")) return "json";
  if (path.endsWith(".yml") || path.endsWith(".yaml")) return "yaml";
  if (path.endsWith(".md")) return "markdown";
  if (path.includes("Dockerfile")) return "dockerfile";
  return "plaintext";
}

export function CodeViewer({ selectedFile, generatedFiles, fileContents }) {
  const { isDark } = useTheme();

  if (!selectedFile) {
    return (
      <div
        className="h-full flex flex-col items-center justify-center gap-3
                        bg-gray-950 rounded-lg"
      >
        <FileCode2 size={24} className="text-gray-700" />
        <p className="text-sm text-gray-600">Select a file to view</p>
      </div>
    );
  }

  const normalizedSelected = selectedFile?.replace(/\\/g, "/");

  const content =
    fileContents[normalizedSelected] ||
    fileContents[normalizedSelected?.split("/").slice(1).join("/")] ||
    Object.entries(fileContents).find(
      ([k]) => k.endsWith(normalizedSelected) || normalizedSelected?.endsWith(k)
    )?.[1] ||
    `// ${selectedFile}\n// File content not available`;

  console.log(
    "Selected:",
    selectedFile,
    "Keys:",
    Object.keys(fileContents).slice(0, 3)
  );

  return (
    <div
      className="h-full flex flex-col rounded-lg overflow-hidden
                      border border-gray-800"
    >
      <div
        className="shrink-0 flex items-center gap-2 px-4 py-2
                        bg-gray-900 border-b border-gray-800"
      >
        <FileCode2 size={12} className="text-gray-500" />
        <span className="text-xs text-gray-400 font-mono">{selectedFile}</span>
      </div>
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={getLanguage(selectedFile)}
          value={content}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 12,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            padding: { top: 12, bottom: 12 },
            renderLineHighlight: "none",
            fontFamily: "JetBrains Mono, Fira Code, monospace",
          }}
        />
      </div>
    </div>
  );
}
