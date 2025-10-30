#!/usr/bin/env python3
"""
AGTAG Syntax Validator - Prevents syntax errors in Python files

This tool validates that AGTAG blocks use the correct syntax for their file type:
- Python files (.py): MUST use AGTAG_METADATA = '''...''' wrapper
- HTML/Markdown files: Can use direct <!--AGTAG v1 START--> comments

Usage:
    python3 tools/validate_agtag_syntax.py <file_path>
    python3 tools/validate_agtag_syntax.py --scan-all

Returns exit code 0 if valid, 1 if invalid.
"""

import sys
import re
from pathlib import Path
from typing import Tuple, List


def validate_python_agtag(file_path: Path, content: str) -> Tuple[bool, str]:
    """
    Validate AGTAG syntax in Python files.

    Python files MUST wrap AGTAG in AGTAG_METADATA variable.

    Returns:
        (is_valid, error_message)
    """
    has_agtag_marker = '<!--AGTAG v1 START-->' in content
    has_metadata_var = 'AGTAG_METADATA' in content

    if not has_agtag_marker:
        # No AGTAG - that's fine
        return True, ""

    if has_agtag_marker and not has_metadata_var:
        return False, (
            f"❌ INVALID PYTHON AGTAG SYNTAX: {file_path}\n"
            f"   Python files MUST wrap AGTAG in AGTAG_METADATA variable.\n"
            f"   \n"
            f"   WRONG (current):\n"
            f"   <!--AGTAG v1 START-->\n"
            f"   ...\n"
            f"   \n"
            f"   CORRECT:\n"
            f"   AGTAG_METADATA = '''<!--AGTAG v1 START-->\n"
            f"   {{\"version\":\"v1\",\"symbols\":[...]}}\n"
            f"   <!--AGTAG v1 END-->'''\n"
            f"   \n"
            f"   See examples/example.py for reference."
        )

    # Verify AGTAG is actually inside the AGTAG_METADATA string
    # Look for pattern: AGTAG_METADATA = """...""" or '''...'''
    metadata_pattern = r'AGTAG_METADATA\s*=\s*["\']' + '{3}.*?<!--AGTAG v1 START-->'
    if not re.search(metadata_pattern, content, re.DOTALL):
        return False, (
            f"⚠️  WARNING: {file_path} has both AGTAG and AGTAG_METADATA but format may be incorrect.\n"
            f"   Ensure <!--AGTAG v1 START--> is INSIDE the AGTAG_METADATA string."
        )

    return True, ""


def validate_html_markdown_agtag(file_path: Path, content: str) -> Tuple[bool, str]:
    """
    Validate AGTAG syntax in HTML/Markdown files.

    These files can use direct HTML comments.

    Returns:
        (is_valid, error_message)
    """
    # HTML/Markdown can use direct comments - always valid
    # (HTML comments are native syntax)
    return True, ""


def validate_file(file_path: Path) -> Tuple[bool, str]:
    """
    Validate AGTAG syntax for any file type.

    Returns:
        (is_valid, error_message)
    """
    if not file_path.exists():
        return False, f"❌ File not found: {file_path}"

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        return False, f"❌ Error reading {file_path}: {e}"

    # Determine file type and validate accordingly
    suffix = file_path.suffix.lower()

    if suffix == '.py':
        return validate_python_agtag(file_path, content)
    elif suffix in ['.html', '.md', '.markdown']:
        return validate_html_markdown_agtag(file_path, content)
    else:
        # Unknown file type - skip validation
        return True, ""


def scan_directory(root_path: Path, exclude_patterns: List[str] = None) -> List[Tuple[Path, bool, str]]:
    """
    Scan directory for all files with AGTAGs and validate syntax.

    Args:
        root_path: Root directory to scan
        exclude_patterns: Patterns to exclude (e.g., '.venv', '__pycache__')

    Returns:
        List of (file_path, is_valid, error_message) tuples
    """
    if exclude_patterns is None:
        exclude_patterns = ['.venv', '__pycache__', '.git', 'node_modules']

    results = []

    # Scan Python files
    for py_file in root_path.rglob('*.py'):
        # Skip excluded directories
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue

        is_valid, error = validate_file(py_file)
        if not is_valid or error:
            results.append((py_file, is_valid, error))

    # Scan HTML/Markdown files
    for pattern in ['*.html', '*.md', '*.markdown']:
        for file in root_path.rglob(pattern):
            if any(excl in str(file) for excl in exclude_patterns):
                continue

            is_valid, error = validate_file(file)
            if not is_valid or error:
                results.append((file, is_valid, error))

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate AGTAG syntax in files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single file
  python3 tools/validate_agtag_syntax.py src/agentdb/core.py

  # Scan all files in project
  python3 tools/validate_agtag_syntax.py --scan-all

  # Scan specific directory
  python3 tools/validate_agtag_syntax.py --scan-dir dashboard/
        """
    )

    parser.add_argument('file', nargs='?', help='File to validate')
    parser.add_argument('--scan-all', action='store_true', help='Scan entire project')
    parser.add_argument('--scan-dir', help='Scan specific directory')

    args = parser.parse_args()

    if args.scan_all or args.scan_dir:
        # Scan mode
        root = Path(args.scan_dir) if args.scan_dir else Path('.')

        print(f"🔍 Scanning {root} for AGTAG syntax issues...")
        results = scan_directory(root)

        if not results:
            print("✅ No AGTAG syntax issues found!")
            return 0

        # Show results
        invalid_count = sum(1 for _, is_valid, _ in results if not is_valid)
        warning_count = sum(1 for _, is_valid, _ in results if is_valid and _[2])

        print(f"\n📊 Found {len(results)} files with issues:")
        print(f"   ❌ Invalid: {invalid_count}")
        print(f"   ⚠️  Warnings: {warning_count}")
        print()

        for file_path, is_valid, error in results:
            if error:
                print(error)
                print()

        return 1 if invalid_count > 0 else 0

    elif args.file:
        # Single file mode
        file_path = Path(args.file)
        is_valid, error = validate_file(file_path)

        if is_valid and not error:
            print(f"✅ {file_path}: AGTAG syntax valid")
            return 0
        else:
            if error:
                print(error)
            return 1 if not is_valid else 0

    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
