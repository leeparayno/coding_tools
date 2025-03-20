#!/usr/bin/env python3
"""
Code Analyzer for Git Projects

This script analyzes a git project directory to:
1. Find all programming code files of specified types
2. Calculate the lines of code (excluding comments and blank lines)
3. Estimate the number of tokens that would be used if the code was passed to an LLM

Usage:
    python code_analyzer.py [path_to_git_project]
"""

import os
import sys
import re
import glob
import argparse
import tiktoken
from pathlib import Path
from collections import defaultdict
import fnmatch

# Default file extensions to analyze
DEFAULT_EXTENSIONS = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.scala', '.sh',
    '.html', '.css', '.scss', '.sass', '.less', '.json', '.yml', '.yaml', '.md',
    '.dart'  # Adding Dart extension
]

# Default ignore patterns for different tech stacks
DEFAULT_IGNORE_PATTERNS = {
    'common': [
        '*.min.js',
        '*.min.css',
        '*.map',
        '*.lock',
        '*.log',
        '*.pot',
        '*.mo',
        '*.pyc',
        '__pycache__/*',
        '.git/*',
        '.svn/*',
        '.hg/*',
        '.DS_Store',
        'Thumbs.db'
    ],
    'node': [
        'package-lock.json',
        'yarn.lock',
        'pnpm-lock.yaml',
        'node_modules/*',
        'bower_components/*',
        '.npm/*',
        '.yarn/*',
        'dist/*',
        'build/*',
        'coverage/*'
    ],
    'python': [
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        'env/*',
        'venv/*',
        '.env/*',
        '.venv/*',
        'pip-log.txt',
        'pip-delete-this-directory.txt',
        '.tox/*',
        '.coverage',
        '.coverage.*',
        'htmlcov/*',
        '*.egg-info/*',
        'dist/*',
        'build/*',
        'eggs/*',
        'lib/*',
        'lib64/*',
        'parts/*',
        'sdist/*',
        'var/*',
        '*.egg'
    ],
    'java': [
        '*.class',
        '*.jar',
        '*.war',
        '*.ear',
        '*.nar',
        'target/*',
        '.gradle/*',
        'build/*',
        'out/*',
        '.idea/*',
        '*.iml',
        '*.iws',
        '*.ipr',
        'gradle-app.setting'
    ],
    'dotnet': [
        'bin/*',
        'obj/*',
        '*.suo',
        '*.user',
        '*.userosscache',
        '*.sln.docstates',
        '[Dd]ebug/*',
        '[Rr]elease/*',
        'x64/*',
        'x86/*',
        '[Aa][Rr][Mm]/*',
        '[Aa][Rr][Mm]64/*',
        'bld/*',
        '[Bb]in/*',
        '[Oo]bj/*',
        '[Ll]og/*',
        '.vs/*'
    ]
}

# Comment patterns for different languages
COMMENT_PATTERNS = {
    'py': [r'#.*', r'""".*?"""', r"'''.*?'''"],
    'js|jsx|ts|tsx|java|c|cpp|h|hpp|cs|go|php|swift|kt|rs|scala|dart': [r'//.*', r'/\*.*?\*/'],  # Added dart to this pattern
    'rb': [r'#.*', r'=begin.*?=end'],
    'html': [r'<!--.*?-->'],
    'css|scss|sass|less': [r'/\*.*?\*/', r'//.*'],
    'sh': [r'#.*'],
    'md': [],  # Markdown doesn't have traditional code comments
    'json|yml|yaml': []  # These formats don't have traditional code comments
}

def get_encoding():
    """Get the tiktoken encoding for cl100k_base (used by GPT-4)"""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return tiktoken.encoding_for_model("gpt-4")

def count_tokens(text):
    """Count the number of tokens in the text using tiktoken"""
    encoding = get_encoding()
    return len(encoding.encode(text))

def is_binary_file(file_path):
    """Check if a file is binary by reading the first few bytes"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception:
        return True

def get_comment_pattern(file_ext):
    """Get the appropriate comment pattern for a file extension"""
    ext = file_ext.lstrip('.')
    for pattern, patterns in COMMENT_PATTERNS.items():
        if re.match(f'^({pattern})$', ext):
            return patterns
    return []

def remove_comments(content, file_ext):
    """Remove comments from code content based on file extension"""
    comment_patterns = get_comment_pattern(file_ext)
    
    # Handle multi-line comments first
    for pattern in comment_patterns:
        if '.*?' in pattern:  # This is a multi-line comment pattern
            content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Then handle single-line comments
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:  # Skip empty lines
            continue
            
        # Check if the entire line is a comment
        is_comment = False
        for pattern in comment_patterns:
            if '.*?' not in pattern and re.match(f'^{pattern}$', line_stripped):
                is_comment = True
                break
                
        if not is_comment:
            # Remove inline comments
            for pattern in comment_patterns:
                if '.*?' not in pattern:
                    line = re.sub(pattern, '', line)
            
            # Only add non-empty lines after comment removal
            if line.strip():
                result_lines.append(line)
    
    return '\n'.join(result_lines)

def analyze_file(file_path):
    """Analyze a single file for lines of code and token count"""
    try:
        if is_binary_file(file_path):
            return 0, 0, ""
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Remove comments and blank lines
        clean_content = remove_comments(content, file_ext)
        
        # Count lines of code (non-empty, non-comment lines)
        loc = len(clean_content.split('\n'))
        
        # Count tokens
        token_count = count_tokens(content)
        
        return loc, token_count, content
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return 0, 0, ""

def find_git_root(path):
    """Find the root directory of the git repository"""
    current = os.path.abspath(path)
    while current != '/':
        if os.path.isdir(os.path.join(current, '.git')):
            return current
        current = os.path.dirname(current)
    return None

def load_ignore_patterns(project_path):
    """Load ignore patterns from .codeanalyzerignore file and detect project type"""
    ignore_patterns = set(DEFAULT_IGNORE_PATTERNS['common'])
    
    # Detect project type and add relevant patterns
    if os.path.exists(os.path.join(project_path, 'package.json')):
        ignore_patterns.update(DEFAULT_IGNORE_PATTERNS['node'])
    if os.path.exists(os.path.join(project_path, 'requirements.txt')) or \
       os.path.exists(os.path.join(project_path, 'setup.py')):
        ignore_patterns.update(DEFAULT_IGNORE_PATTERNS['python'])
    if os.path.exists(os.path.join(project_path, 'pom.xml')) or \
       os.path.exists(os.path.join(project_path, 'build.gradle')):
        ignore_patterns.update(DEFAULT_IGNORE_PATTERNS['java'])
    if glob.glob(os.path.join(project_path, '*.csproj')) or \
       glob.glob(os.path.join(project_path, '*.sln')):
        ignore_patterns.update(DEFAULT_IGNORE_PATTERNS['dotnet'])
    
    # Load custom ignore patterns from .codeanalyzerignore
    ignore_file = os.path.join(project_path, '.codeanalyzerignore')
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignore_patterns.add(line)
    
    return ignore_patterns

def should_ignore_file(file_path, base_path, ignore_patterns):
    """Check if a file should be ignored based on ignore patterns"""
    rel_path = os.path.relpath(file_path, base_path)
    
    # Convert path to forward slashes for consistent pattern matching
    rel_path = rel_path.replace(os.sep, '/')
    
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(rel_path, pattern) or \
           fnmatch.fnmatch(os.path.basename(rel_path), pattern):
            return True
    return False

def analyze_project(project_path, extensions=None, exclude_dirs=None):
    """Analyze all code files in the project directory"""
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS
    
    if exclude_dirs is None:
        exclude_dirs = ['.git', 'node_modules', 'venv', '.venv', 'env', '.env', 
                       'dist', 'build', 'target', 'out', 'bin', 'obj']
    
    # Find git root if it exists
    git_root = find_git_root(project_path)
    if git_root:
        project_path = git_root
        print(f"Found git root at: {git_root}")
    
    # Load ignore patterns
    ignore_patterns = load_ignore_patterns(project_path)
    
    # Statistics for both production and test code
    stats = {
        'production': {
            'total_files': 0,
            'total_loc': 0,
            'total_tokens': 0,
            'stats_by_ext': defaultdict(lambda: {'files': 0, 'loc': 0, 'tokens': 0}),
            'top_files': []
        },
        'test': {
            'total_files': 0,
            'total_loc': 0,
            'total_tokens': 0,
            'stats_by_ext': defaultdict(lambda: {'files': 0, 'loc': 0, 'tokens': 0}),
            'top_files': []
        }
    }
    
    # Common test file/directory patterns
    test_patterns = [
        r'test[s]?$',  # test, tests directories
        r'spec[s]?$',   # spec, specs directories
        r'__tests?__',  # __test__, __tests__ directories
        r'.*[._-]tests?[._-].*',  # files containing .test., _test_, etc.
        r'.*[._-]specs?[._-].*',  # files containing .spec., _spec_, etc.
        r'test_.*\..*$',  # files starting with test_
        r'.*_test\..*$',  # files ending with _test
        r'.*\.tests?\.',  # .test. in filename
        r'.*\.spec\.',    # .spec. in filename
    ]
    
    def is_test_file(file_path, file_name):
        """Determine if a file is a test file based on its path and name"""
        # Check if file is in a test directory
        path_parts = file_path.split(os.sep)
        for part in path_parts:
            for pattern in test_patterns:
                if re.match(pattern, part, re.IGNORECASE):
                    return True
        
        # Check if the file name matches test patterns
        for pattern in test_patterns:
            if re.match(pattern, file_name, re.IGNORECASE):
                return True
        
        return False
    
    # Walk through the project directory
    for root, dirs, files in os.walk(project_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip ignored files
            if should_ignore_file(file_path, project_path, ignore_patterns):
                continue
                
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in extensions:
                loc, tokens, _ = analyze_file(file_path)
                
                if loc > 0:  # Only count non-empty files
                    # Determine if this is a test file
                    is_test = is_test_file(file_path, file)
                    category = 'test' if is_test else 'production'
                    
                    # Update statistics
                    stats[category]['total_files'] += 1
                    stats[category]['total_loc'] += loc
                    stats[category]['total_tokens'] += tokens
                    
                    stats[category]['stats_by_ext'][file_ext]['files'] += 1
                    stats[category]['stats_by_ext'][file_ext]['loc'] += loc
                    stats[category]['stats_by_ext'][file_ext]['tokens'] += tokens
                    
                    # Track this file for top files list
                    rel_path = os.path.relpath(file_path, project_path)
                    stats[category]['top_files'].append((rel_path, tokens, loc))
                    # Keep only top 10 files by token count
                    stats[category]['top_files'].sort(key=lambda x: x[1], reverse=True)
                    stats[category]['top_files'] = stats[category]['top_files'][:10]
    
    return stats

def format_number(num):
    """Format a number with commas as thousands separators"""
    return f"{num:,}"

def print_category_results(category_name, stats, models):
    """Print results for a specific category (production/test)"""
    print(f"\n{category_name} Code Analysis:")
    print("-"*80)
    
    print(f"Total Files: {format_number(stats['total_files'])}")
    print(f"Total Lines of Code: {format_number(stats['total_loc'])}")
    print(f"Total Tokens: {format_number(stats['total_tokens'])}")
    
    print("\nContext Window Usage:")
    for provider, provider_models in models.items():
        print(f"\n{provider}:")
        for model_name, context_size in provider_models.items():
            percentage = min(100, stats['total_tokens'] / context_size * 100)
            print(f"  - {model_name:<20} {percentage:.1f}% of context window")
    
    print("\nTop 10 Files by Token Count:")
    print("-"*80)
    print(f"{'File':<50} {'Tokens':<12} {'Lines':<10} {'% of Total':<10}")
    print("-"*80)
    
    for file_path, tokens, loc in stats['top_files']:
        percent = tokens / stats['total_tokens'] * 100 if stats['total_tokens'] > 0 else 0
        # Truncate long file paths with ellipsis
        truncated_path = file_path if len(file_path) <= 47 else '...' + file_path[-44:]
        print(f"{truncated_path:<50} {format_number(tokens):<12} {format_number(loc):<10} {percent:.1f}%")
    
    print("\nBreakdown by File Type:")
    print("-"*80)
    print(f"{'Extension':<10} {'Files':<10} {'Lines of Code':<15} {'Tokens':<15} {'% of Total':<10}")
    print("-"*80)
    
    # Sort by token count (descending)
    sorted_exts = sorted(
        stats['stats_by_ext'].items(),
        key=lambda x: x[1]['tokens'],
        reverse=True
    )
    
    for ext, ext_stats in sorted_exts:
        percent = ext_stats['tokens'] / stats['total_tokens'] * 100 if stats['total_tokens'] > 0 else 0
        print(f"{ext:<10} {format_number(ext_stats['files']):<10} {format_number(ext_stats['loc']):<15} {format_number(ext_stats['tokens']):<15} {percent:.1f}%")

def print_results(results):
    """Print the analysis results in a readable format"""
    print("\n" + "="*80)
    print(f"PROJECT CODE ANALYSIS SUMMARY")
    print("="*80)
    
    # Calculate combined totals
    total_files = results['production']['total_files'] + results['test']['total_files']
    total_loc = results['production']['total_loc'] + results['test']['total_loc']
    total_tokens = results['production']['total_tokens'] + results['test']['total_tokens']
    
    print(f"\nOverall Statistics:")
    print(f"Total Files: {format_number(total_files)}")
    print(f"Total Lines of Code: {format_number(total_loc)}")
    print(f"Total Tokens: {format_number(total_tokens)}")
    
    # Print production/test code ratio
    prod_ratio = (results['production']['total_tokens'] / total_tokens * 100) if total_tokens > 0 else 0
    test_ratio = (results['test']['total_tokens'] / total_tokens * 100) if total_tokens > 0 else 0
    print(f"\nCode Distribution:")
    print(f"Production Code: {prod_ratio:.1f}%")
    print(f"Test Code: {test_ratio:.1f}%")
    
    # Define models and their context window sizes
    models = {
        "OpenAI Models": {
            "GPT-3.5 Turbo (4K)": 4000,
            "GPT-3.5 Turbo (16K)": 16000,
            "GPT-4o (128K)": 128000,
            "GPT-4 Turbo (128K)": 128000,
            "GPT-4 (8K)": 8000,
            "GPT-4 (32K)": 32000,
        },
        "Anthropic Models": {
            "Claude 3 Haiku (200K)": 200000,
            "Claude 3 Sonnet (200K)": 200000,
            "Claude 3 Opus (200K)": 200000,
            "Claude 3.5 Sonnet (200K)": 200000,
            "Claude 2 (100K)": 100000,
        }
    }
    
    # Print detailed results for production and test code separately
    print_category_results("Production", results['production'], models)
    print_category_results("Test", results['test'], models)
    
    print("="*80)

def main():
    parser = argparse.ArgumentParser(description='Analyze code files in a git project')
    parser.add_argument('project_path', nargs='?', default='.', 
                        help='Path to the git project (default: current directory)')
    parser.add_argument('--extensions', '-e', nargs='+', 
                        help='File extensions to analyze (default: common programming languages)')
    parser.add_argument('--exclude', '-x', nargs='+',
                        help='Directories to exclude (default: common build and dependency directories)')
    parser.add_argument('--include-tests', action='store_true',
                        help='Include test files in the main analysis (default: separate test analysis)')
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a valid directory")
        return 1
    
    # Process extensions
    extensions = args.extensions
    if extensions:
        extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
    else:
        extensions = DEFAULT_EXTENSIONS
    
    # Run analysis
    print(f"Analyzing project at: {project_path}")
    print(f"File types: {', '.join(extensions)}")
    
    results = analyze_project(project_path, extensions, args.exclude)
    print_results(results)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 