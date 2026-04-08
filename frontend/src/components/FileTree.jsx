import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  FileCode2,
  FolderOpen,
  Folder,
  FileJson,
  FileText,
  Container,
} from "lucide-react";

function getFileIcon(name) {
  if (name.endsWith(".jsx") || name.endsWith(".js")) return FileCode2;
  if (name.endsWith(".json")) return FileJson;
  if (name.endsWith(".yml") || name.endsWith(".yaml")) return FileText;
  if (name === "Dockerfile" || name === ".dockerignore") return Container;
  return FileText;
}

function buildTree(files) {
  const tree = {};

  let allPaths = [];

  const values = Object.values(files);
  if (values.length > 0 && Array.isArray(values[0])) {
    allPaths = values.flat();
  } else {
    allPaths = Object.keys(files);
  }

  allPaths.forEach((filePath) => {
    if (typeof filePath !== "string") return;
    const parts = filePath.split("/");
    let node = tree;
    parts.forEach((part, i) => {
      if (i === parts.length - 1) {
        node[part] = { __file: filePath };
      } else {
        node[part] = node[part] || {};
        node = node[part];
      }
    });
  });
  return tree;
}
function TreeNode({ name, node, onSelect, selectedFile, depth = 0 }) {
  const [open, setOpen] = useState(depth < 2);
  const isFile = "__file" in node;
  const pl = `${8 + depth * 14}px`;

  if (isFile) {
    const Icon = getFileIcon(name);
    const isSelected = selectedFile === node.__file;
    return (
      <button
        onClick={() => onSelect(node.__file)}
        style={{ paddingLeft: pl }}
        className={`w-full flex items-center gap-1.5 py-1 pr-3 text-xs
                    text-left rounded-md transition-colors
                    ${
                      isSelected
                        ? "bg-violet-100 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300"
                        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                    }`}
      >
        <Icon size={11} className="shrink-0 opacity-60" />
        <span className="truncate font-mono">{name}</span>
      </button>
    );
  }

  const isEmpty = Object.keys(node).length === 0;
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{ paddingLeft: pl }}
        className="w-full flex items-center gap-1.5 py-1 pr-3 text-xs
                   text-left text-gray-500 dark:text-gray-500
                   hover:bg-gray-100 dark:hover:bg-gray-800
                   rounded-md transition-colors"
      >
        {open ? (
          <ChevronDown size={10} className="shrink-0" />
        ) : (
          <ChevronRight size={10} className="shrink-0" />
        )}
        {open ? (
          <FolderOpen size={11} className="shrink-0 text-amber-400" />
        ) : (
          <Folder size={11} className="shrink-0 text-amber-400" />
        )}
        <span className="font-mono">{name}</span>
      </button>
      {open && !isEmpty && (
        <div>
          {Object.entries(node).map(([k, v]) => (
            <TreeNode
              key={k}
              name={k}
              node={v}
              onSelect={onSelect}
              selectedFile={selectedFile}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({ files, selectedFile, onSelect }) {
  const values = Object.values(files);
  const all =
    values.length > 0 && Array.isArray(values[0])
      ? values.flat()
      : Object.keys(files);

  const tree = buildTree(files);

  if (all.length === 0) {
    return (
      <div className="h-full flex items-center justify-center px-4">
        <p className="text-xs text-gray-400 dark:text-gray-600 text-center">
          Files will appear here as agents complete
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto py-2">
      <div className="px-3 pb-2">
        <span className="text-xs text-gray-400 dark:text-gray-600">
          {all.length} files
        </span>
      </div>
      {Object.entries(tree).map(([k, v]) => (
        <TreeNode
          key={k}
          name={k}
          node={v}
          onSelect={onSelect}
          selectedFile={selectedFile}
        />
      ))}
    </div>
  );
}
