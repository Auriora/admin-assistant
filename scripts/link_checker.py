
import os
import re
import sys
from pathlib import Path

# Configuration
ROOT = Path(os.getcwd()) # This will be the project root
DOCS_DIR = ROOT / 'docs'

def list_files_recursive(directory: Path) -> list[Path]:
    """Recursively list all files under a directory."""
    files = []
    for entry in directory.iterdir():
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            files.extend(list_files_recursive(entry))
    return files


def extract_links(markdown_content: str) -> list[dict]:
    """Extract markdown links of the form [text](target) ignoring images ![]()."""
    links = []
    # Regex: (?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)
    # Explanation:
    # (?<!\!) - Negative lookbehind to ensure it's not preceded by '!' (to ignore images)
    # \[      - Matches literal '['
    # [^\]]*  - Matches any character except ']' zero or more times
    # \]      - Matches literal ']'
    # \(      - Matches literal '('
    # ([^)\s]+) - Captures the link target (any character except ')' or whitespace, one or more times)
    # (?:     - Non-capturing group for optional title
    # \s+"[^"]*" - Matches whitespace, then a double-quoted string
    # )?      - Makes the title group optional
    # \)      - Matches literal ')'
    link_re = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
    
    for idx, line in enumerate(markdown_content.splitlines()):
        for match in link_re.finditer(line):
            target = match.group(1)
            links.append({'target': target, 'line': idx + 1})
    return links

def is_external_link(target: str) -> bool:
    """Determine if a link is external."""
    return target.startswith(('http://', 'https://'))

def is_anchor(target: str) -> bool:
    """Determine if a link is an anchor-only link."""
    return target.startswith('#')

def resolve_target(from_file: Path, target: str) -> Path | None:
    """Normalize a relative link target from a file."""
    # Strip any anchor (#section) for file existence check
    file_part = target.split('#')[0]
    if not file_part:
        return None

    # If absolute path (starts with /), map to root
    if file_part.startswith('/'):
        # Remove leading slashes to correctly join with ROOT
        return ROOT / file_part.lstrip('/')
    
    # Otherwise, resolve relative to the from_file directory
    return (from_file.parent / file_part).resolve()

def main():
    if not DOCS_DIR.is_dir():
        print(f"Error: 'docs' directory not found at {DOCS_DIR}")
        sys.exit(1)

    md_files = [f for f in list_files_recursive(DOCS_DIR) if f.suffix == '.md']
    broken_links = []
    link_count = 0

    for file in md_files:
        content = file.read_text(encoding='utf-8')
        links = extract_links(content)
        link_count += len(links)

        for link_info in links:
            target = link_info['target']
            line = link_info['line']

            if is_external_link(target) or is_anchor(target):
                continue
            # mailto:, tel:, etc. skip
            if target.startswith(('mailto:', 'tel:')):
                continue

            resolved_path = resolve_target(file, target)
            if not resolved_path:
                continue

            if not resolved_path.exists():
                broken_links.append({'file': file, 'line': line, 'target': target, 'resolved': resolved_path})
            elif resolved_path.is_dir():
                # If target appears to point to a directory without explicit file, allow index.md fallback
                index_md_path = resolved_path / 'index.md'
                if not index_md_path.is_file():
                    broken_links.append({'file': file, 'line': line, 'target': target, 'resolved': resolved_path})

    rel_docs = DOCS_DIR.relative_to(ROOT) if DOCS_DIR.is_relative_to(ROOT) else str(DOCS_DIR)

    if broken_links:
        print(f"\nBroken links found ({len(broken_links)}) in {len(md_files)} files ({link_count} links scanned) under {rel_docs}/:", file=sys.stderr)
        for b in broken_links:
            rel_file = b['file'].relative_to(ROOT)
            rel_resolved = b['resolved'].relative_to(ROOT) if b['resolved'].is_relative_to(ROOT) else str(b['resolved'])
            print(f"- {rel_file}:{b['line']} → '{b['target']}' (resolved: {rel_resolved})", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"No broken local links found under {rel_docs}/. Scanned {len(md_files)} files and {link_count} links.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Link check failed with error: {e}", file=sys.stderr)
        sys.exit(2)
