# Code Analyzer for Git Projects

This tool analyzes a git project directory to:
1. Find all programming code files of specified types
2. Calculate the lines of code (excluding comments and blank lines)
3. Estimate the number of tokens that would be used if the code was passed to an LLM
4. Separate production code from test code for better context window estimation
5. Identify largest files by token count to find potential outliers
6. Automatically ignore non-relevant files based on technology stack

This is useful for estimating how much of your codebase can fit within an LLM's context window, with separate analysis for production and test code.

## Features

- Automatically detects git repository root
- Separates production code from test code for better context analysis
- Identifies largest files by token count to help optimize context window usage
- Smart file ignoring based on project type (Node.js, Python, Java, .NET, etc.)
- Excludes common build and dependency directories by default
- Calculates lines of code by removing comments and blank lines
- Estimates token usage for different LLM context windows (including GPT-3.5, GPT-4, GPT-4o, Claude 3 series, and more)
- Provides detailed breakdown by file type
- Identifies test files and directories using common patterns:
  - Test directories: `test/`, `tests/`, `spec/`, `specs/`, `__tests__/`
  - Test files: `*_test.*`, `test_*.*`, `*.test.*`, `*.spec.*`
  - Common testing patterns across different languages

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Install dependencies
pip install -r requirements.txt

# Optional: Copy and customize the ignore file
cp .codeanalyzerignore.example .codeanalyzerignore
```

## Usage

```bash
# Basic usage - analyzes current directory
python code_analyzer.py

# Analyze a specific project directory
python code_analyzer.py /path/to/project

# Analyze only specific file extensions
python code_analyzer.py --extensions py js ts

# Exclude additional directories beyond the defaults
python code_analyzer.py --exclude vendor docs

# Include test files in the main analysis instead of separate reporting
python code_analyzer.py --include-tests
```

## Ignore Patterns

The tool automatically detects your project type and applies appropriate ignore patterns. You can also create a `.codeanalyzerignore` file in your project root to customize which files to ignore.

### Automatic Project Type Detection

The tool detects your project type based on these files:
- Node.js: `package.json`
- Python: `requirements.txt` or `setup.py`
- Java: `pom.xml` or `build.gradle`
- .NET: `*.csproj` or `*.sln`

### Default Ignored Patterns by Type

#### Common (All Projects)
- Minified files: `*.min.js`, `*.min.css`
- Source maps: `*.map`
- Lock files: `*.lock`
- Log files: `*.log`
- System files: `.DS_Store`, `Thumbs.db`

#### Node.js Projects
- `package-lock.json`
- `yarn.lock`
- `pnpm-lock.yaml`
- `node_modules/*`
- `bower_components/*`
- Build directories: `dist/*`, `build/*`

#### Python Projects
- `*.pyc`, `*.pyo`, `*.pyd`
- Virtual environments: `venv/*`, `.env/*`
- Build artifacts: `*.egg-info/*`, `dist/*`
- Cache directories: `__pycache__/*`

#### Java Projects
- `*.class`, `*.jar`, `*.war`
- Build directories: `target/*`, `build/*`
- IDE files: `.idea/*`, `*.iml`

#### .NET Projects
- Build directories: `bin/*`, `obj/*`
- Debug/Release folders
- IDE files: `.vs/*`

### Custom Ignore File

Create a `.codeanalyzerignore` file in your project root to add your own patterns:

```gitignore
# Custom ignore patterns
specific_file.txt
custom_directory/*
*.custom_extension

# Override default patterns
!package-lock.json  # Include a file that would be ignored by default
```

## Example Output

```
================================================================================
PROJECT CODE ANALYSIS SUMMARY
================================================================================

Overall Statistics:
Total Files: 250
Total Lines of Code: 25,432
Total Tokens: 198,765

Code Distribution:
Production Code: 75.5%
Test Code: 24.5%

Production Code Analysis:
--------------------------------------------------------------------------------
Total Files: 180
Total Lines of Code: 18,432
Total Tokens: 150,000

Context Window Usage:

OpenAI Models:
  - GPT-3.5 Turbo (4K)    100.0% of context window
  - GPT-3.5 Turbo (16K)   93.8% of context window
  - GPT-4o (128K)         11.7% of context window
  - GPT-4 Turbo (128K)    11.7% of context window
  - GPT-4 (8K)            100.0% of context window
  - GPT-4 (32K)           46.9% of context window

Anthropic Models:
  - Claude 3 Haiku (200K) 7.5% of context window
  - Claude 3 Sonnet (200K) 7.5% of context window
  - Claude 3 Opus (200K)  7.5% of context window
  - Claude 3.5 Sonnet (200K) 7.5% of context window
  - Claude 2 (100K)       15.0% of context window

Top 10 Files by Token Count:
--------------------------------------------------------------------------------
File                                                  Tokens      Lines     % of Total
--------------------------------------------------------------------------------
src/components/LargeComponent.tsx                     15,234      1,234     10.2%
src/utils/helpers.ts                                 12,456      987       8.3%
src/services/api.js                                  10,789      876       7.2%
...other top files...

Breakdown by File Type:
--------------------------------------------------------------------------------
Extension  Files      Lines of Code   Tokens         % of Total
--------------------------------------------------------------------------------
.py        35         6,234           42,345         28.2%
.js        52         5,456           38,678         25.8%
.tsx       45         4,345           36,345         24.2%
.css       28         1,987           22,432         15.0%
.md        20         410             10,200         6.8%

Test Code Analysis:
--------------------------------------------------------------------------------
Total Files: 70
Total Lines of Code: 7,000
Total Tokens: 48,765

Context Window Usage:

OpenAI Models:
  - GPT-3.5 Turbo (4K)    100.0% of context window
  - GPT-3.5 Turbo (16K)   93.8% of context window
  - GPT-4o (128K)         11.7% of context window
  - GPT-4 Turbo (128K)    11.7% of context window
  - GPT-4 (8K)            100.0% of context window
  - GPT-4 (32K)           46.9% of context window

Anthropic Models:
  - Claude 3 Haiku (200K) 7.5% of context window
  - Claude 3 Sonnet (200K) 7.5% of context window
  - Claude 3 Opus (200K)  7.5% of context window
  - Claude 3.5 Sonnet (200K) 7.5% of context window
  - Claude 2 (100K)       15.0% of context window

Top 10 Files by Token Count:
--------------------------------------------------------------------------------
File                                                  Tokens      Lines     % of Total
--------------------------------------------------------------------------------
tests/integration/api.test.js                         5,234       432      10.7%
tests/components/LargeComponent.test.tsx              4,567       345       9.4%
...other top test files...
================================================================================
```

## Command Line Options

- `project_path`: Path to the git project (default: current directory)
- `--extensions, -e`: File extensions to analyze (default: common programming languages)
- `--exclude, -x`: Additional directories to exclude (default: common build and dependency directories)
- `--include-tests`: Include test files in the main analysis instead of separate reporting (default: False)

## Default Excluded Directories

The following directories are excluded by default:
- `.git`
- `node_modules`
- `venv`, `.venv`, `env`, `.env`
- `dist`, `build`
- `target`, `out`
- `bin`, `obj`

## License

MIT 
