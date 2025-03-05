# Code Analyzer for Git Projects

This tool analyzes a git project directory to:
1. Find all programming code files of specified types
2. Calculate the lines of code (excluding comments and blank lines)
3. Estimate the number of tokens that would be used if the code was passed to an LLM

This is useful for estimating how much of your codebase can fit within an LLM's context window.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Analyze the current directory
python code_analyzer.py

# Analyze a specific project directory
python code_analyzer.py /path/to/project

# Analyze only specific file extensions
python code_analyzer.py --extensions py js ts

# Exclude additional directories
python code_analyzer.py --exclude vendor tests
```

## Features

- Automatically detects git repository root
- Excludes common build and dependency directories by default
- Calculates lines of code by removing comments and blank lines
- Estimates token usage for different LLM context windows (GPT-4 8K, GPT-4 32K, Claude 100K)
- Provides detailed breakdown by file type

## Example Output

```
================================================================================
PROJECT CODE ANALYSIS SUMMARY
================================================================================

Total Files: 125
Total Lines of Code: 15,432
Total Tokens: 98,765

Context Window Usage:
  - GPT-4 (8K):      100.0% of context window
  - GPT-4 (32K):     30.9% of context window
  - Claude (100K):   9.9% of context window

Breakdown by File Type:
--------------------------------------------------------------------------------
Extension  Files      Lines of Code   Tokens         % of Total
--------------------------------------------------------------------------------
.py        45         8,234           52,345         53.0%
.js        32         3,456           25,678         26.0%
.tsx       15         2,345           12,345         12.5%
.css       18         987             5,432          5.5%
.md        15         410             2,965          3.0%
================================================================================
```

## License

MIT 
