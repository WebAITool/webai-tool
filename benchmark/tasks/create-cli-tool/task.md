# Create a file stats CLI tool

Create a Python CLI tool called `filestats` that analyzes files in a directory and reports statistics.

## Requirements

1. **Command-line interface** using `argparse`:
   - `filestats <directory>` — analyze all files in the directory
   - `--ext .py` — filter by file extension (can be used multiple times)
   - `--sort size|name|lines` — sort results (default: size)
   - `--top N` — show only top N results (default: show all)
   - `--format table|json|csv` — output format (default: table)

2. **Statistics per file**:
   - File path (relative to input directory)
   - File size in bytes
   - Number of lines
   - Number of non-empty lines
   - File extension

3. **Summary at the end**:
   - Total files analyzed
   - Total size
   - Total lines
   - Average lines per file

4. **Behavior**:
   - Recursively scan the directory
   - Skip binary files (detect by checking for null bytes in first 8KB)
   - Skip hidden files/dirs (starting with `.`)
   - Handle permission errors gracefully (skip + warn on stderr)
   - Output should be clean and readable

5. **Entry point**: The tool should be runnable as `python filestats.py <dir>`

6. Create a `requirements.txt` if any external packages are needed (prefer stdlib only).
