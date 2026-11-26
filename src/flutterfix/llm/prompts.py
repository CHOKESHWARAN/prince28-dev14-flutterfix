"""Find and load versioned prompts from prompts/<task>_v<n>.md."""

import re
from pathlib import Path


def version_number(name: str | Path) -> int:
    """Extract integer version n from e.g. 'classify_v2' -> 2."""
    stem = Path(name).stem
    match = re.search(r"_v(\d+)$", stem)
    return int(match.group(1)) if match else 0


def find_prompts(task: str, directory: Path | str = "prompts") -> dict[str, str]:
    """Find all prompts/<task>_v<n>.md files and sort them by version number.

    Returns a dict mapping version name to prompt content, e.g.:
    {'classify_v1': '...', 'classify_v2': '...'}
    """
    directory = Path(directory)
    pattern = f"{task}_v*.md"
    files = sorted(directory.glob(pattern), key=version_number)
    return {p.stem: p.read_text(encoding="utf-8").strip() for p in files}


def load_prompt(task: str, version: int | str = 1, directory: Path | str = "prompts") -> str:
    """Load a specific prompt file content by task and version."""
    directory = Path(directory)
    if isinstance(version, int) or (isinstance(version, str) and version.isdigit()):
        filename = f"{task}_v{version}.md"
    elif str(version).startswith(f"{task}_"):
        filename = f"{version}.md"
    else:
        filename = f"{task}_{version}.md"

    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def latest_prompt(task: str, directory: Path | str = "prompts") -> tuple[str, str]:
    """Return (version, content) for the latest version of a task prompt."""
    prompts = find_prompts(task, directory)
    if not prompts:
        raise FileNotFoundError(f"No prompts found for task {task!r} in {directory}")
    latest_ver = max(prompts.keys(), key=version_number)
    return latest_ver, prompts[latest_ver]
