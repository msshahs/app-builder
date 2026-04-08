import json
import re
import logging
from typing import Optional
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def parse_llm_json(content: str, agent_name: str) -> Optional[dict]:
    """
    Robustly parse JSON from LLM response.
    Handles markdown code blocks, extra whitespace, and common LLM formatting issues.
    """
    logger = get_logger(agent_name)

    cleaned = content.strip()

    # Strip markdown code blocks if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        cleaned = "\n".join(lines[1:-1]).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object with regex
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    logger.error(f"Failed to parse JSON response. Raw content:\n{content[:500]}")
    return None


def format_file_summary(files: dict) -> str:
    """Format a dict of generated files into a readable summary."""
    if not files:
        return "No files generated"
    lines = []
    for path, content in files.items():
        lines_count = len(content.split("\n"))
        lines.append(f"  {path} ({lines_count} lines)")
    return "\n".join(lines)


def count_tokens_estimate(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 chars)."""
    return len(text) // 4


def write_generated_files(result: dict, output_dir: str = "generated") -> str:
    """Write all generated code files to disk then apply templates."""
    logger = get_logger("file_writer")

    os.makedirs(output_dir, exist_ok=True)

    all_files = {}
    all_files.update(result.get("frontend_code") or {})
    all_files.update(result.get("backend_code") or {})
    all_files.update(result.get("database_code") or {})
    all_files.update(result.get("devops_code") or {})

    written = []
    for file_path, content in all_files.items():
        full_path = os.path.join(output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        written.append(full_path)
        logger.info(f"Written: {full_path}")

    # Apply templates AFTER writing agent files
    # Templates override agent-generated boilerplate with battle-tested versions
    from core.template_engine import apply_all_templates
    apply_all_templates(output_dir)

    logger.info(f"Total files written: {len(written)} → {output_dir}/")
    return output_dir