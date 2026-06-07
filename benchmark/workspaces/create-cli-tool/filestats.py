import argparse
import csv
import json
import os
import sys

def get_file_info(root, file_path):
    """Return a dict with file info or None if skipped."""
    # Skip hidden files/directories: any component starting with '.'
    rel_path = os.path.relpath(file_path, root)
    if any(part.startswith('.') for part in rel_path.split(os.sep)):
        return None

    # Check binary file by reading first 8KB for null byte
    try:
        with open(file_path, 'rb') as f:
            head = f.read(8192)
            if b'\x00' in head:
                return None  # binary file, skip
    except PermissionError:
        print(f"Warning: Permission denied reading {file_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Cannot read {file_path}: {e}", file=sys.stderr)
        return None

    try:
        size = os.path.getsize(file_path)
        extension = os.path.splitext(file_path)[1].lower()
    except PermissionError:
        print(f"Warning: Permission denied for stat {file_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Cannot stat {file_path}: {e}", file=sys.stderr)
        return None

    # Count lines
    total_lines = 0
    non_empty_lines = 0
    try:
        with open(file_path, 'r', errors='ignore') as f:
            for line in f:
                total_lines += 1
                if line.strip():
                    non_empty_lines += 1
    except PermissionError:
        print(f"Warning: Permission denied reading lines {file_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Cannot count lines in {file_path}: {e}", file=sys.stderr)
        return None

    return {
        'path': rel_path,
        'size': size,
        'lines': total_lines,
        'non_empty_lines': non_empty_lines,
        'extension': extension
    }

def main():
    parser = argparse.ArgumentParser(description='File statistics tool')
    parser.add_argument('directory', help='Directory to scan')
    parser.add_argument('--ext', action='append', dest='extensions',
                        help='Filter by extension (can be used multiple times)')
    parser.add_argument('--sort', choices=['size', 'name', 'lines'],
                        default='size', help='Sort criteria (default: size)')
    parser.add_argument('--top', type=int, default=None,
                        help='Show only top N files')
    parser.add_argument('--format', choices=['table', 'json', 'csv'],
                        default='table', help='Output format')

    args = parser.parse_args()
    directory = args.directory

    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Collect file info
    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            info = get_file_info(directory, file_path)
            if info is not None:
                # Apply extension filter if --ext given
                if args.extensions:
                    if info['extension'] not in args.extensions:
                        continue
                files.append(info)

    # Sort
    if args.sort == 'size':
        files.sort(key=lambda x: x['size'], reverse=True)
    elif args.sort == 'name':
        files.sort(key=lambda x: x['path'])
    elif args.sort == 'lines':
        files.sort(key=lambda x: x['lines'], reverse=True)

    # Apply --top
    if args.top is not None and args.top > 0:
        files = files[:args.top]

    # Output
    if args.format == 'table':
        # Header
        header = f"| {'Path':<30} | {'Size':>8} | {'Lines':>6} | {'Non-empty Lines':>16} | {'Extension':<10} |"
        sep = '=' * len(header)
        print(sep)
        print(header)
        print(sep)
        for f in files:
            print(f"| {f['path']:<30} | {f['size']:>8} | {f['lines']:>6} | {f['non_empty_lines']:>16} | {f['extension']:<10} |")
        print(sep)
    elif args.format == 'json':
        print(json.dumps(files, indent=2))
    elif args.format == 'csv':
        writer = csv.writer(sys.stdout)
        writer.writerow(['Path', 'Size', 'Lines', 'Non-empty Lines', 'Extension'])
        for f in files:
            writer.writerow([f['path'], f['size'], f['lines'], f['non_empty_lines'], f['extension']])

    # Summary
    total_files = len(files)
    total_size = sum(f['size'] for f in files)
    total_lines = sum(f['lines'] for f in files)
    avg_lines = round(total_lines / total_files, 2) if total_files > 0 else 0.0
    if args.format == 'table': print(f"
Summary: {total_files} files, {total_size} bytes, {total_lines} lines, average {avg_lines} lines per file")

if __name__ == '__main__':
    main()
