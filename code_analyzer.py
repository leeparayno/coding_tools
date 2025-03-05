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

# Default file extensions to analyze
DEFAULT_EXTENSIONS = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.scala', '.sh',
    '.html', '.css', '.scss', '.sass', '.less', '.json', '.yml', '.yaml', '.md'
]

# Comment patterns for different languages
COMMENT_PATTERNS = {
    'py': [r'#.*', r'""".*?"""', r"'''.*?'''"],
    'js|jsx|ts|tsx|java|c|cpp|h|hpp|cs|go|php|swift|kt|rs|scala': [r'//.*', r'/\*.*?\*/'],
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
    
    # Statistics
    total_files = 0
    total_loc = 0
    total_tokens = 0
    stats_by_ext = defaultdict(lambda: {'files': 0, 'loc': 0, 'tokens': 0})
    
    # Walk through the project directory
    for root, dirs, files in os.walk(project_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in extensions:
                file_path = os.path.join(root, file)
                loc, tokens, _ = analyze_file(file_path)
                
                if loc > 0:  # Only count non-empty files
                    total_files += 1
                    total_loc += loc
                    total_tokens += tokens
                    
                    stats_by_ext[file_ext]['files'] += 1
                    stats_by_ext[file_ext]['loc'] += loc
                    stats_by_ext[file_ext]['tokens'] += tokens
    
    return {
        'total_files': total_files,
        'total_loc': total_loc,
        'total_tokens': total_tokens,
        'stats_by_ext': dict(stats_by_ext)
    }

def format_number(num):
    """Format a number with commas as thousands separators"""
    return f"{num:,}"

def print_results(results):
    """Print the analysis results in a readable format"""
    print("\n" + "="*80)
    print(f"PROJECT CODE ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\nTotal Files: {format_number(results['total_files'])}")
    print(f"Total Lines of Code: {format_number(results['total_loc'])}")
    print(f"Total Tokens: {format_number(results['total_tokens'])}")
    
    # Calculate token usage for different models
    gpt4_8k = min(100, results['total_tokens'] / 8000 * 100)
    gpt4_32k = min(100, results['total_tokens'] / 32000 * 100)
    claude_100k = min(100, results['total_tokens'] / 100000 * 100)
    
    print(f"\nContext Window Usage:")
    print(f"  - GPT-4 (8K):      {gpt4_8k:.1f}% of context window")
    print(f"  - GPT-4 (32K):     {gpt4_32k:.1f}% of context window")
    print(f"  - Claude (100K):   {claude_100k:.1f}% of context window")
    
    print("\nBreakdown by File Type:")
    print("-"*80)
    print(f"{'Extension':<10} {'Files':<10} {'Lines of Code':<15} {'Tokens':<15} {'% of Total':<10}")
    print("-"*80)
    
    # Sort by token count (descending)
    sorted_exts = sorted(
        results['stats_by_ext'].items(),
        key=lambda x: x[1]['tokens'],
        reverse=True
    )
    
    for ext, stats in sorted_exts:
        percent = stats['tokens'] / results['total_tokens'] * 100 if results['total_tokens'] > 0 else 0
        print(f"{ext:<10} {format_number(stats['files']):<10} {format_number(stats['loc']):<15} {format_number(stats['tokens']):<15} {percent:.1f}%")
    
    print("="*80)

def main():
    parser = argparse.ArgumentParser(description='Analyze code files in a git project')
    parser.add_argument('project_path', nargs='?', default='.', 
                        help='Path to the git project (default: current directory)')
    parser.add_argument('--extensions', '-e', nargs='+', 
                        help='File extensions to analyze (default: common programming languages)')
    parser.add_argument('--exclude', '-x', nargs='+',
                        help='Directories to exclude (default: common build and dependency directories)')
    
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