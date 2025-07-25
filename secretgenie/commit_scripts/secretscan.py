#!/usr/bin/env python3
"""Secret scanning module for detecting potential secrets in code."""

import sys
import os
import re
import json
import logging
import subprocess
import math
from typing import List, Dict, Union, Set, Tuple, Optional, Any
from datetime import datetime
import html
from config import (
    PATTERNS, HTML_CONFIG,
    EXCLUDED_EXTENSIONS, EXCLUDED_DIRECTORIES, ENTROPY_THRESHOLDS
)
from utils import (
    setup_logging, get_git_metadata,
    is_git_repo, has_unstaged_changes, get_git_diff,
    mask_secret
)
import webbrowser
from pathlib import Path

# --- COPY/IMPORT ValidationWindow class here (from pre_commit.py) ---
# --- END COPY ---

class SecretScanner:
    """Scanner for detecting potential secrets in code."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the secret scanner."""
        self.logger = logger or logging.getLogger(__name__)
        self.found_secrets: List[Dict[str, Any]] = []
        self._seen_secrets: Set[str] = set()
        # Track file_path:line_number combinations to avoid duplicates
        self._seen_file_lines: Set[Tuple[str, int]] = set()
    
    def calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not value:
            return 0.0
        
        # Count character frequencies
        freq = {}
        for c in value:
            freq[c] = freq.get(c, 0) + 1
            
        # Calculate entropy
        length = float(len(value))
        return -sum(f/length * math.log2(f/length) for f in freq.values())
    
    def is_suspicious_env_var(self, name: str) -> bool:
        """Check if an environment variable name suggests it contains a secret."""
        suspicious_terms = {
            'token', 'secret', 'password', 'pwd', 'pass', 'key', 'auth',
            'credential', 'api', 'private', 'cert', 'ssh'
        }
        name = name.lower()
        return any(term in name for term in suspicious_terms)
    
    def should_skip_value(self, value: str) -> bool:
        """Check if a value should be skipped (common non-secrets)."""
        # Skip very short values
        if len(value) < 6:
            return True
            
        # Skip common non-secret values
        common_values = {
            'true', 'false', 'none', 'null', 'undefined', 'localhost',
            'password', 'username', 'user', 'test', 'example', 'demo'
        }
        return value.lower() in common_values
    
    def scan_content(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Scan content for potential secrets."""
        self.found_secrets = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith(('#', '//', '/*', '*')):
                continue
            
            # Check if we've already found a secret at this file:line
            file_line_key = (file_path, line_num)
            if file_line_key in self._seen_file_lines:
                continue
            
            # Flag to track if we found a secret in this line
            found_secret_in_line = False
            
            # First pass: Check against defined patterns
            for pattern, secret_type, config in PATTERNS:
                if found_secret_in_line:
                    break
                
                matches = re.finditer(pattern, line)
                for match in matches:
                    value = match.group(0)
                    
                    # Skip if we've seen this exact secret before
                    if value in self._seen_secrets:
                        continue
                        
                    # Skip common non-secrets
                    if self.should_skip_value(value):
                        continue
                    
                    # Check minimum length if specified
                    min_length = config.get('min_length', 0)
                    if len(value) < min_length:
                        continue
                    
                    # Calculate entropy if required
                    entropy = None
                    if config.get('require_entropy', True):
                        entropy = self.calculate_entropy(value)
                        threshold = config.get('threshold', ENTROPY_THRESHOLDS['default'])
                        if entropy < threshold:
                            continue
                    
                    # For environment variables, check if the name suggests a secret
                    if config.get('check_name', False) and not self.is_suspicious_env_var(match.group(1)):
                        continue
                    
                    # Record the found secret
                    secret = {
                        'file_path': file_path,
                        'line_number': line_num,
                        'line': line,
                        'matched_content': value,
                        'type': secret_type,
                        'entropy': entropy,
                        'detection_method': 'pattern_match'
                    }
                    self.found_secrets.append(secret)
                    self._seen_secrets.add(value)
                    self._seen_file_lines.add(file_line_key)
                    
                    self.logger.info(f"Found potential {secret_type} in {file_path}:{line_num}")
                    found_secret_in_line = True
                    break  # Once we find a secret in this line, no need to check other matches
            
            # If we already found a secret in this line, skip the variable name scanning
            if found_secret_in_line:
                continue
            
            # Second pass: Variable name scanning
            var_patterns = [
                r'(?i)(?:const|let|var|private|public|protected)?\s*(\w+)\s*[=:]\s*["\']([^"\']+)["\']',
                r'(?i)(\w+)\s*[=:]\s*["\']([^"\']+)["\']',
                r'(?i)(\w+)\s*=\s*"""([^"]*)"""',  # Python multi-line strings
                r'(?i)(\w+)\s*=\s*`([^`]*)`',      # Template literals
            ]
            
            for pattern in var_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    var_name, value = match.groups()
                    
                    # Skip if we've seen this exact secret before
                    if value in self._seen_secrets:
                        continue
                        
                    # Skip common non-secrets
                    if self.should_skip_value(value):
                        continue
                    
                    # Check if variable name suggests a secret
                    if not self.is_suspicious_env_var(var_name):
                        continue
                    
                    # Calculate entropy
                    entropy = self.calculate_entropy(value)
                    
                    # Use lower threshold for password-related variables
                    threshold = ENTROPY_THRESHOLDS['password'] if 'password' in var_name.lower() else ENTROPY_THRESHOLDS['default']
                    
                    if entropy >= threshold:
                        secret = {
                            'file_path': file_path,
                            'line_number': line_num,
                            'line': line,
                            'matched_content': value,
                            'type': 'Variable Assignment',
                            'variable_name': var_name,
                            'entropy': entropy,
                            'detection_method': 'variable_scan'
                        }
                        self.found_secrets.append(secret)
                        self._seen_secrets.add(value)
                        self._seen_file_lines.add(file_line_key)
                        
                        self.logger.info(f"Found potential secret in variable '{var_name}' in {file_path}:{line_num}")
                        # Once we find a secret in this line from variable name, exit the loop
                        break
                
                # If we found a secret in this pattern, break out of the pattern loop
                if len(self.found_secrets) > 0 and self.found_secrets[-1]['line_number'] == line_num:
                    break
        
        return self.found_secrets
    
    def scan_staged_changes(self) -> List[Dict[str, Any]]:
        """Scan staged changes for secrets, focusing only on changed lines."""
        try:
            # Get list of staged files
            cmd = ['git', 'diff', '--cached', '--name-only']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            staged_files = result.stdout.strip().split('\n')
            staged_files = [f for f in staged_files if f]  # Remove empty strings
            
            if not staged_files:
                self.logger.info("No staged files found.")
                return []
                
            # Get the diff with line numbers for each staged file
            self.logger.info(f"Scanning {len(staged_files)} staged files for secrets")
            
            # Get the detailed diff information
            diff_cmd = ['git', 'diff', '--cached', '-p', '--unified=0', '--no-color']
            diff_output = subprocess.check_output(diff_cmd, text=True)
            
            # Parse the diff to extract changed lines with correct line numbers
            changed_lines = {}  # Dict to store {file_path: {line_number: content}}
            current_file = None
            
            for line in diff_output.splitlines():
                # New file being processed
                if line.startswith('diff --git'):
                    file_path = line.split()[-1].lstrip('b/')
                    current_file = file_path
                    changed_lines[current_file] = {}
                
                # Hunk header with line numbers
                elif line.startswith('@@ '):
                    # Format: "@@ -old_start,old_count +new_start,new_count @@"
                    hunk_info = line.split(' ')[2]  # gets "+new_start,new_count"
                    
                    try:
                        # Extract the starting line number from "+line_num,count"
                        new_start = int(hunk_info.split(',')[0].lstrip('+'))
                        self.logger.debug(f"Hunk starts at line {new_start} in {current_file}")
                    except (IndexError, ValueError) as e:
                        self.logger.error(f"Error parsing hunk header '{line}': {e}")
                        continue
                    
                    # Store current position in this hunk
                    current_line_number = new_start - 1  # Prepare for increment
                
                # Added or modified line (not the file header line)
                elif current_file and line.startswith('+') and not line.startswith('+++'):
                    current_line_number += 1
                    content = line[1:]  # Remove the '+' prefix
                    
                    # Store the changed line with its actual line number in the file
                    changed_lines[current_file][current_line_number] = content
                    self.logger.debug(f"Added line {current_line_number} from {current_file} for scanning")
            
            # Now scan all changed lines with their correct line numbers
            for file_path, lines in changed_lines.items():
                for line_number, content in lines.items():
                    # Skip empty lines and comments
                    if not content.strip() or content.strip().startswith(('#', '//', '/*', '*')):
                        continue
                    
                    # Scan this individual line with its correct line number
                    self.logger.debug(f"Scanning line {line_number} in {file_path}")
                    self.scan_line(file_path, line_number, content)
            
            self.logger.info(f"Found {len(self.found_secrets)} potential secrets in staged changes")
            return self.found_secrets
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running git command: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error during staged changes scan: {e}", exc_info=True)
            return []

    def scan_line(self, file_path: str, line_number: int, line: str) -> None:
        """Scan a single line for secrets."""
        # Check if we've already found a secret at this file:line
        file_line_key = (file_path, line_number)
        if file_line_key in self._seen_file_lines:
            return
        
        # First pass: Check against defined patterns
        for pattern, secret_type, config in PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                value = match.group(0)
                
                # Skip if we've seen this exact secret before
                if value in self._seen_secrets:
                    continue
                    
                # Skip common non-secrets
                if self.should_skip_value(value):
                    continue
                
                # Check minimum length if specified
                min_length = config.get('min_length', 0)
                if len(value) < min_length:
                    continue
                
                # Calculate entropy if required
                entropy = None
                if config.get('require_entropy', True):
                    entropy = self.calculate_entropy(value)
                    threshold = config.get('threshold', ENTROPY_THRESHOLDS['default'])
                    if entropy < threshold:
                        continue
                
                # For environment variables, check if the name suggests a secret
                if config.get('check_name', False) and not self.is_suspicious_env_var(match.group(1)):
                    continue
                
                # Record the found secret
                secret = {
                    'file_path': file_path,
                    'line_number': line_number,
                    'line': line,
                    'matched_content': value,
                    'type': secret_type,
                    'entropy': entropy,
                    'detection_method': 'pattern_match'
                }
                self.found_secrets.append(secret)
                self._seen_secrets.add(value)
                self._seen_file_lines.add(file_line_key)
                
                self.logger.info(f"Found potential {secret_type} in {file_path}:{line_number}")
                return  # Once we find a secret in this line, no need to check other patterns
        
        # Second pass: Variable name scanning
        var_patterns = [
            r'(?i)(?:const|let|var|private|public|protected)?\s*(\w+)\s*[=:]\s*["\']([^"\']+)["\']',
            r'(?i)(\w+)\s*[=:]\s*["\']([^"\']+)["\']',
            r'(?i)(\w+)\s*=\s*"""([^"]*)"""',  # Python multi-line strings
            r'(?i)(\w+)\s*=\s*`([^`]*)`',      # Template literals
        ]
        
        for pattern in var_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                var_name, value = match.groups()
                
                # Skip if we've seen this exact secret before
                if value in self._seen_secrets:
                    continue
                    
                # Skip common non-secrets
                if self.should_skip_value(value):
                    continue
                
                # Check if variable name suggests a secret
                if not self.is_suspicious_env_var(var_name):
                    continue
                
                # Calculate entropy
                entropy = self.calculate_entropy(value)
                
                # Use lower threshold for password-related variables
                threshold = ENTROPY_THRESHOLDS['password'] if 'password' in var_name.lower() else ENTROPY_THRESHOLDS['default']
                
                if entropy >= threshold:
                    secret = {
                        'file_path': file_path,
                        'line_number': line_number,
                        'line': line,
                        'matched_content': value,
                        'type': 'Variable Assignment',
                        'variable_name': var_name,
                        'entropy': entropy,
                        'detection_method': 'variable_scan'
                    }
                    self.found_secrets.append(secret)
                    self._seen_secrets.add(value)
                    self._seen_file_lines.add(file_line_key)
                    
                    self.logger.info(f"Found potential secret in variable '{var_name}' in {file_path}:{line_number}")
                    return  # Once we find a secret, no need to check other patterns

    def scan_file(self, file_path: str) -> List[Dict[str, Union[str, int]]]:
        """Scan a single file for secrets."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.scan_content(content, file_path=file_path)
        except Exception as e:
            logging.error(f"Error scanning file {file_path}: {e}")
            return []

    def scan_repository(self) -> List[Dict[str, Union[str, int]]]:
        """Scan the entire Git repository for secrets."""
        all_results = []
        # Track file/line combinations we've already seen
        seen_file_lines = set()
        
        try:
            # Get list of all files in the repository
            cmd = ['git', 'ls-files']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            files = result.stdout.strip().split('\n')
            
            # Filter out excluded files and directories
            files = [
                f for f in files
                if not any(f.endswith(ext) for ext in EXCLUDED_EXTENSIONS) and
                not any(d in f.split('/') for d in EXCLUDED_DIRECTORIES)
            ]
            
            # Scan each file
            for file in files:
                if os.path.exists(file):  # Make sure file still exists
                    results = self.scan_file(file)
                    
                    # Only add results that haven't been seen before based on file path and line number
                    for result in results:
                        file_line = (result.get('file_path', ''), result.get('line_number', ''))
                        if file_line not in seen_file_lines:
                            seen_file_lines.add(file_line)
                            all_results.append(result)
        
        except subprocess.CalledProcessError as e:
            logging.error(f"Error listing repository files: {e}")
        except Exception as e:
            logging.error(f"Error scanning repository: {e}")
        
        return all_results

def generate_html_report(output_path: str, **kwargs) -> bool:
    """Generate an HTML report with diff scan and repo scan results."""
    try:
        diff_secrets = kwargs.get('diff_secrets', [])
        repo_secrets = kwargs.get('repo_secrets', [])
        
        # Deduplicate secrets for the diff scan display
        already_seen = set()
        unique_diff_secrets = []
        
        for secret in diff_secrets:
            key = (secret.get('file_path', ''), secret.get('line_number', ''))
            if key not in already_seen:
                already_seen.add(key)
                unique_diff_secrets.append(secret)
        
        # For repository scan, show all unique secrets (including diff secrets)
        # This provides a complete view of all secrets in the codebase
        all_secrets_for_repo_view = unique_diff_secrets.copy()
        
        # Add repo secrets that aren't already in the diff scan
        for secret in repo_secrets:
            key = (secret.get('file_path', ''), secret.get('line_number', ''))
            if key not in already_seen:
                already_seen.add(key)
                all_secrets_for_repo_view.append(secret)
        
        # Use the deduplicated lists for the rest of the function
        diff_secrets = unique_diff_secrets
        
        git_metadata = get_git_metadata()
        
        # Generate table rows for diff scan results
        diff_secrets_table_rows = "".join(
            f"""<tr>
                <td class="sno">{i}</td>
                <td class="filename">{html.escape(data.get('file_path', ''))}</td>
                <td class="line-number">{data.get('line_number', '')}</td>
                <td class="secret"><div class="secret-content">{html.escape(mask_secret(data.get('line', '')))}</div></td>
            </tr>"""
            for i, data in enumerate(diff_secrets, 1)
        ) or "<tr><td colspan='4'>No secrets found in staged changes</td></tr>"

        # Generate table rows for repo scan results (including diff secrets)
        repo_secrets_table_rows = "".join(
            f"""<tr>
                <td class="sno">{i}</td>
                <td class="filename">{html.escape(data.get('file_path', ''))}</td>
                <td class="line-number">{data.get('line_number', '')}</td>
                <td class="secret"><div class="secret-content">{html.escape(mask_secret(data.get('line', '')))}</div></td>
            </tr>"""
            for i, data in enumerate(all_secrets_for_repo_view, 1)
        ) or "<tr><td colspan='4'>No secrets found in repository scan</td></tr>"
        
        # Empty disallowed files section
        disallowed_files_section = ""

        # Get the hooks directory (parent of the script)
        hooks_dir = Path(__file__).parent.parent
        template_path = hooks_dir / "commit_scripts" / "templates" / "report.html"
        
        if not template_path.exists():
            # If template doesn't exist, use a simple built-in template
            logging.error(f"Template file not found at {template_path}, using built-in template")
            html_content = generate_simple_html_report(diff_secrets, repo_secrets, git_metadata)
        else:
            try:
                # Read and fix the template
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
                
                # Replace any problematic format markers in the template with their actual values
                # This fixes issues like the 'margin-top' error
                template = template.replace('{margin-top}', 'margin-top')
                template = template.replace('\n            margin-top', 'margin-top')
                
                # Format the HTML content with values
                format_args = {
                    'title': HTML_CONFIG['title'],
                    'primary_color': HTML_CONFIG['styles']['primary_color'],
                    'error_color': HTML_CONFIG['styles']['error_color'],
                    'background_color': HTML_CONFIG['styles']['background_color'],
                    'container_background': HTML_CONFIG['styles']['container_background'],
                    'header_background': HTML_CONFIG['styles']['header_background'],
                    'git_metadata': git_metadata,
                    'diff_secrets_table_rows': diff_secrets_table_rows,
                    'repo_secrets_table_rows': repo_secrets_table_rows,
                    'disallowed_files_section': disallowed_files_section
                }
                
                # Add fallback for common missing keys
                for key in ['margin-top', 'tab-content', 'tab-button']:
                    if key not in format_args:
                        format_args[key] = key
                
                html_content = template.format(**format_args)
            except (KeyError, ValueError) as e:
                # If template formatting fails, fall back to simple report
                logging.error(f"Error formatting template: {e}, falling back to simple template")
                html_content = generate_simple_html_report(diff_secrets, repo_secrets, git_metadata)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write HTML content to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logging.info(f"HTML report generated at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error generating HTML report: {e}", exc_info=True)
        return False

def generate_simple_html_report(diff_secrets, repo_secrets, git_metadata):
    """Generate a simple HTML report without relying on a template file."""
    # Format git metadata values safely
    safe_metadata = {
        'author': html.escape(git_metadata.get('author', 'Unknown')),
        'repo_name': html.escape(git_metadata.get('repo_name', 'Unknown')),
        'branch': html.escape(git_metadata.get('branch', 'Unknown')),
        'commit_hash': html.escape(git_metadata.get('commit_hash', 'Unknown')),
        'timestamp': html.escape(git_metadata.get('timestamp', 'Unknown'))
    }
    
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Secret Scan Report</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; margin: 20px; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1, h2 {{ color: #0056b3; }}
        .header-info {{ background: #f1f8ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #0056b3; }}
        .header-info p {{ margin: 5px 0; color: #666; }}
        .header-info strong {{ color: #333; margin-right: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        th {{ background: #0056b3; color: white; }}
        tr:nth-child(even) {{ background-color: #f5f5f5; }}
        .secret-content {{ color: #d32f2f; font-family: monospace; white-space: pre-wrap; }}
        .tab-container {{ margin-top: 20px; }}
        .tab-buttons {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .tab-button {{ padding: 10px 20px; background-color: #f0f0f0; border: none; border-radius: 5px; cursor: pointer; }}
        .tab-button.active {{ background-color: #0056b3; color: white; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .actions {{ display: flex; justify-content: space-between; align-items: center; margin: 20px 0; }}
        .btn {{ 
            background-color: #0056b3; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
            text-decoration: none;
            display: inline-flex;
            align-items: center;
        }}
        .btn:hover {{ background-color: #004494; }}
        .icon {{ margin-right: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="actions">
            <h1>Secret Scan Report</h1>
            <button onclick="window.print()" class="btn">
                <span class="icon">📥</span> Save as PDF
            </button>
        </div>
        
        <div class="header-info">
            <p><strong>Git Author:</strong> {safe_metadata['author']}</p>
            <p><strong>Repository:</strong> {safe_metadata['repo_name']}</p>
            <p><strong>Branch:</strong> {safe_metadata['branch']}</p>
            <p><strong>Commit Hash:</strong> {safe_metadata['commit_hash']}</p>
            <p><strong>Timestamp:</strong> {safe_metadata['timestamp']}</p>
        </div>

        <div class="tab-container">
            <div class="tab-buttons">
                <button class="tab-button active" id="diffBtn">Diff Scan Results</button>
                <button class="tab-button" id="repoBtn">Repository Scan Results</button>
            </div>

            <div id="diff-scan" class="tab-content active">
                <h2>Staged Changes - Secrets Found: {len(diff_secrets)}</h2>
                <table>
                    <tr>
                        <th style="width:5%">S.No</th>
                        <th style="width:25%">Filename</th>
                        <th style="width:10%">Line #</th>
                        <th style="width:60%">Secret</th>
                    </tr>
                    {''.join(f"<tr><td>{i}</td><td>{html.escape(s.get('file_path', ''))}</td><td>{s.get('line_number', '')}</td><td><div class=\"secret-content\">{html.escape(mask_secret(s.get('line', '')))}</div></td></tr>" for i, s in enumerate(diff_secrets, 1)) or "<tr><td colspan='4'>No secrets found in staged changes</td></tr>"}
                </table>
            </div>

            <div id="repo-scan" class="tab-content">
                <h2>Repository Scan - Secrets Found: {len(repo_secrets)}</h2>
                <table>
                    <tr>
                        <th style="width:5%">S.No</th>
                        <th style="width:25%">Filename</th>
                        <th style="width:10%">Line #</th>
                        <th style="width:60%">Secret</th>
                    </tr>
                    {''.join(f"<tr><td>{i}</td><td>{html.escape(s.get('file_path', ''))}</td><td>{s.get('line_number', '')}</td><td><div class=\"secret-content\">{html.escape(mask_secret(s.get('line', '')))}</div></td></tr>" for i, s in enumerate(repo_secrets, 1)) or "<tr><td colspan='4'>No secrets found in repository scan</td></tr>"}
                </table>
            </div>
        </div>
    </div>

    <script>
    // Simple tab switching
    document.getElementById('diffBtn').addEventListener('click', function() {{
        document.getElementById('diff-scan').classList.add('active');
        document.getElementById('repo-scan').classList.remove('active');
        document.getElementById('diffBtn').classList.add('active');
        document.getElementById('repoBtn').classList.remove('active');
    }});
    
    document.getElementById('repoBtn').addEventListener('click', function() {{
        document.getElementById('repo-scan').classList.add('active');
        document.getElementById('diff-scan').classList.remove('active');
        document.getElementById('repoBtn').classList.add('active');
        document.getElementById('diffBtn').classList.remove('active');
    }});
    
    // Print setup - show both tabs when printing
    window.onbeforeprint = function() {{
        // Show both tabs for printing
        document.getElementById('diff-scan').style.display = 'block';
        document.getElementById('repo-scan').style.display = 'block';
    }};
    
    window.onafterprint = function() {{
        // Restore tab visibility after printing
        var diffDisplay = document.getElementById('diffBtn').classList.contains('active') ? 'block' : 'none';
        var repoDisplay = document.getElementById('repoBtn').classList.contains('active') ? 'block' : 'none';
        document.getElementById('diff-scan').style.display = diffDisplay;
        document.getElementById('repo-scan').style.display = repoDisplay;
    }};
    </script>
</body>
</html>"""

def main() -> None:
    """Main entry point for the secret scanner."""
    args = sys.argv[1:]
    scanner = SecretScanner()

    commit_range = None
    if '--range' in args:
        idx = args.index('--range')
        if idx + 1 < len(args):
            commit_range = args[idx + 1]

    if commit_range:
        logging.info(f"Scanning only diff for commit range: {commit_range}")
        try:
            # Get the diff for the commit range
            diff_cmd = ['git', 'diff', commit_range, '-p', '--unified=0', '--no-color']
            diff_output = subprocess.check_output(diff_cmd, text=True)
            # Parse the diff to extract changed lines
            changed_files = {}
            current_file = None
            for line in diff_output.splitlines():
                if line.startswith('diff --git'):
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        current_file = parts[2][2:]  # Remove the 'b/' prefix
                        changed_files[current_file] = set()
                elif line.startswith('@@') and current_file:
                    # Example: @@ -1,3 +1,9 @@
                    hunk = line.split(' ')
                    for part in hunk:
                        if part.startswith('+') and ',' in part:
                            start, length = part[1:].split(',')
                            for i in range(int(start), int(start) + int(length)):
                                changed_files[current_file].add(i)
            # Scan only the changed lines
            results = []
            for file_path, lines in changed_files.items():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_lines = f.readlines()
                    for line_num in lines:
                        if 1 <= line_num <= len(file_lines):
                            line = file_lines[line_num - 1]
                            res = scanner.scan_content(line, file_path)
                            for r in res:
                                r['line_number'] = line_num
                                results.append(r)
                except Exception as e:
                    print(f"Warning: Could not scan {file_path}: {e}", file=sys.stderr)
            if results:
                # Show UI/justification as in pre-commit
                validation = ValidationWindow()
                if not validation.run_validation(results):
                    sys.exit(1)
                # Save metadata, generate HTML report, etc. (reuse pre-commit logic)
        except Exception as e:
            logging.error(f"Error scanning commit range diff: {e}")
            sys.exit(1)
    elif "--diff" in args:
        logging.info("Scanning only staged changes...")
        try:
            results = scanner.scan_staged_changes()
            if results:
                print("Potential secrets found in staged changes:")
                for result in results:
                    print(f"- {result['file_path']}:{result['line_number']}")
        except Exception as e:
            logging.error(f"Error scanning staged changes: {e}")
            sys.exit(1)
    else:
        logging.info("Scanning entire repository...")
        try:
            results = scanner.scan_repository()
            if results:
                print("Potential secrets found in repository:")
                for result in results:
                    print(f"- {result['file_path']}:{result['line_number']}")
        except Exception as e:
            logging.error(f"Error scanning repository: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()