#!/usr/bin/env python3
"""Secret scanning module for detecting potential secrets in code."""

import sys
import os
import re
import json
import logging
import subprocess
import platform
import math
from typing import List, Dict, Union, Set, Tuple, Optional, Any
from datetime import datetime
import html
from .config import (
    PATTERNS, HTML_CONFIG,
    EXCLUDED_EXTENSIONS, EXCLUDED_DIRECTORIES, ENTROPY_THRESHOLDS,
    should_exclude_file
)
from .utils import (
    setup_logging, get_git_metadata,
    is_git_repo, has_unstaged_changes, get_git_diff,
    mask_secret, run_subprocess
)
import webbrowser
from pathlib import Path

class SecretScanner:
    """Scanner for detecting potential secrets in code."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the secret scanner."""
        self.logger = logger or logging.getLogger(__name__)
        self.found_secrets: List[Dict[str, Any]] = []
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
        # Initialize a local list to collect secrets found in this content
        content_secrets = []
        lines = content.splitlines()
        
        self.logger.debug(f"Scanning {len(lines)} lines in {file_path}")
        
        for line_num, line in enumerate(lines, 1):
            # Only skip empty lines, but process all comments
            if not line.strip():
                continue
            
            # Check if we've already found a secret at this file:line
            file_line_key = (file_path, line_num)
            if file_line_key in self._seen_file_lines:
                self.logger.debug(f"Already found secret at {file_path}:{line_num}, skipping")
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
                    content_secrets.append(secret)
                    self._seen_file_lines.add(file_line_key)
                    
                    # Add debug log for found secret
                    self.logger.debug(f"Found secret in {file_path} at line {line_num}: type={secret_type}")
                    
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
                        content_secrets.append(secret)
                        self._seen_file_lines.add(file_line_key)
                        
                        # Add debug log for found secret
                        self.logger.debug(f"Found variable secret in {file_path} at line {line_num}: var={var_name}")
                        
                        break
                
                # If we found a secret in this pattern, break out of the pattern loop
                if len(content_secrets) > 0 and content_secrets[-1]['line_number'] == line_num:
                    break
        
        self.logger.debug(f"Completed scan of {file_path}, found {len(content_secrets)} secrets")
        return content_secrets
    
    def scan_file(self, file_path: str) -> List[Dict[str, Union[str, int]]]:
        """Scan a single file for potential secrets."""
        try:
            # Check if the file should be excluded based on the new exclusion rules
            if should_exclude_file(file_path):
                self.logger.debug(f"Skipping excluded file: {file_path}")
                return []
                
            self.logger.debug(f"Starting scan of file: {file_path}")
            
            # Read file content
            cmd = ['git', 'show', f':0:{file_path}']
            try:
                result = run_subprocess(cmd, capture_output=True, text=True, check=True)
                content = result.stdout
                self.logger.debug(f"Read {len(content)} bytes from git for file {file_path}")
            except subprocess.CalledProcessError:
                # File might not be in git yet, try reading directly
                self.logger.debug(f"File {file_path} not in git index, reading directly")
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except UnicodeDecodeError:
                    # Try reading as binary and decoding with 'latin-1'
                    self.logger.debug(f"Unicode decode error for {file_path}, trying latin-1 encoding")
                    with open(file_path, 'r', encoding='latin-1') as file:
                        content = file.read()
                self.logger.debug(f"Read {len(content)} bytes directly from file {file_path}")
            
            # Scan the content
            file_secrets = self.scan_content(content, file_path)
            
            if file_secrets:
                self.logger.debug(f"Found {len(file_secrets)} secrets in {file_path}")
            else:
                self.logger.debug(f"No secrets found in {file_path}")
                
            return file_secrets
        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")
            return []

    def scan_files_to_push(self, files_list=None) -> List[Dict[str, Any]]:
        """Scan files that will be pushed for secrets."""
        try:
            # Get list of files to be pushed if not provided
            files_to_push = files_list or []
            
            if not files_to_push:
                # Get list of files to be pushed
                cmd = ['git', 'diff', '--cached', '--name-only']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                files_to_push = result.stdout.strip().split('\n')
                files_to_push = [f for f in files_to_push if f]  # Remove empty strings
                
            self.logger.info(f"Scanning {len(files_to_push)} files to be pushed")
            
            # Filter out excluded file types and directories
            filtered_files = []
            for file_path in files_to_push:
                # Skip files that should be excluded
                if should_exclude_file(file_path):
                    self.logger.debug(f"Skipping excluded file: {file_path}")
                    continue
                filtered_files.append(file_path)
            
            self.logger.info(f"After filtering, scanning {len(filtered_files)} files")
            
            # Scan files
            for file_path in filtered_files:
                file_secrets = self.scan_file(file_path)
                if file_secrets:
                    self.found_secrets.extend(file_secrets)
                    
            return self.found_secrets
        except Exception as e:
            self.logger.error(f"Error scanning files to push: {e}")
            return []
    
    def scan_files(self, files_list: List[str]) -> List[Dict[str, Any]]:
        """Scan a list of files for secrets."""
        if not files_list:
            self.logger.info("No files to scan")
            return []
        
        self.logger.info(f"Scanning {len(files_list)} files")
        
        # Filter out excluded file types and directories
        filtered_files = []
        for file_path in files_list:
            # Skip files that should be excluded
            if should_exclude_file(file_path):
                self.logger.debug(f"Skipping excluded file: {file_path}")
                continue
            filtered_files.append(file_path)
        
        self.logger.info(f"After filtering, scanning {len(filtered_files)} files")
        
        # Scan files
        for file_path in filtered_files:
            file_secrets = self.scan_file(file_path)
            if file_secrets:
                self.found_secrets.extend(file_secrets)
                
        return self.found_secrets
    
    def scan_line(self, file_path: str, line_number: int, line: str) -> None:
        """Scan a single line for potential secrets."""
        file_line_key = (file_path, line_number)
        if file_line_key in self._seen_file_lines:
            return
        
        # Check if the file should be excluded
        if should_exclude_file(file_path):
            self.logger.debug(f"Skipping excluded file line: {file_path}:{line_number}")
            return
        
        found_secret = False
        
        # Check against defined patterns
        for pattern, secret_type, config in PATTERNS:
            if found_secret:
                break
            
            matches = re.finditer(pattern, line)
            for match in matches:
                value = match.group(0)
                
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
                self._seen_file_lines.add(file_line_key)
                
                found_secret = True
                break
        
        if found_secret:
            return
        
        # Variable name scanning
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
                    self._seen_file_lines.add(file_line_key)
                    break
            
            if file_line_key in self._seen_file_lines:
                break
    
    def scan_repository(self) -> List[Dict[str, Union[str, int]]]:
        """Scan the entire repository for secrets."""
        try:
            self.logger.info("Starting repository scan")
            
            # Get all tracked files
            cmd = ['git', 'ls-files']
            
            result = run_subprocess(cmd, capture_output=True, text=True, check=True)
            files = result.stdout.strip().split('\n')
            files = [f for f in files if f]  # Remove empty strings
            
            self.logger.info(f"Found {len(files)} tracked files in repository")
            
            # Filter out excluded file types and directories
            filtered_files = []
            for file_path in files:
                # Skip files that should be excluded
                if should_exclude_file(file_path):
                    self.logger.debug(f"Skipping excluded file: {file_path}")
                    continue
                filtered_files.append(file_path)
            
            self.logger.info(f"After filtering, scanning {len(filtered_files)} files")
            
            # Scan files
            for file_path in filtered_files:
                file_secrets = self.scan_file(file_path)
                if file_secrets:
                    self.found_secrets.extend(file_secrets)
                    
            return self.found_secrets
        except Exception as e:
            self.logger.error(f"Error scanning repository: {e}")
            return []

    def scan_changed_lines(self, files_list: List[str]) -> List[Dict[str, Any]]:
        """Scan only the changed lines in files for secrets.
        
        This method uses git diff to identify only the changed lines in the files
        and scans only those specific lines, rather than the entire file content.
        """
        if not files_list:
            self.logger.info("No files to scan")
            return []
        
        self.logger.info(f"Scanning changed lines in {len(files_list)} files")
        
        # Get git diff information to identify changed lines
        changed_lines = get_git_diff()
        
        # If we couldn't get changed lines (not a git repo or other issue),
        # fall back to scanning entire files
        if not changed_lines:
            self.logger.info("Could not determine changed lines, falling back to full file scan")
            return self.scan_files(files_list)
        
        # Filter out excluded file types and directories
        filtered_files = []
        for file_path in files_list:
            # Skip files that should be excluded
            if should_exclude_file(file_path):
                self.logger.debug(f"Skipping excluded file: {file_path}")
                continue
            filtered_files.append(file_path)
        
        self.logger.info(f"After filtering, scanning changed lines in {len(filtered_files)} files")
        
        # Scan only the changed lines in each file
        for file_path in filtered_files:
            # If the file is in our changed_lines dict, scan only those lines
            if file_path in changed_lines:
                print(f"-  Scanning {len(changed_lines[file_path])} changed lines in {file_path}")
                for line_number, line_content in changed_lines[file_path]:
                    self.scan_line(file_path, line_number, line_content)
            else:
                # If the file is not in changed_lines but still in our files list,
                # it might be a new file - scan it completely
                self.logger.debug(f"File {file_path} not found in diff, scanning entire file")
                file_secrets = self.scan_file(file_path)
                if file_secrets:
                    self.found_secrets.extend(file_secrets)
                    
        return self.found_secrets

def generate_html_report(output_path: str, **kwargs) -> bool:
    """Generate an HTML report with diff scan and repo scan results."""
    try:
        diff_secrets = kwargs.get('diff_secrets', [])
        repo_secrets = kwargs.get('repo_secrets', [])
        
        # Enhanced logging to show exact counts and details
        logging.info(f"Generating HTML report with {len(diff_secrets)} diff secrets and {len(repo_secrets)} repo secrets")
        logging.debug(f"Raw diff_secrets count: {len(diff_secrets)}")
        logging.debug(f"Raw repo_secrets count: {len(repo_secrets)}")
        
        if repo_secrets:
            # Log some details about repository secrets to help diagnose issues
            logging.debug("Repository secrets summary:")
            file_counts = {}
            for s in repo_secrets:
                file_path = s.get('file_path', 'unknown')
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
            
            for file_path, count in file_counts.items():
                logging.debug(f"  - {file_path}: {count} secrets")
        else:
            logging.debug("No repository secrets provided to HTML report generator")
        
        # Deduplicate secrets for diff display based on file+line
        diff_seen = set()
        unique_diff_secrets = []
        
        for secret in diff_secrets:
            key = (secret.get('file_path', ''), secret.get('line_number', 0))
            if key not in diff_seen:
                diff_seen.add(key)
                unique_diff_secrets.append(secret)
        
        # For repository scan, deduplicate based on file+line
        repo_seen = set()
        unique_repo_secrets = []
        
        for secret in repo_secrets:
            key = (secret.get('file_path', ''), secret.get('line_number', 0))
            if key not in repo_seen:
                repo_seen.add(key)
                unique_repo_secrets.append(secret)
        
        # Use the deduplicated lists
        diff_secrets = unique_diff_secrets
        repo_secrets = unique_repo_secrets
        
        # Log after deduplication
        logging.debug(f"After deduplication: {len(diff_secrets)} diff secrets, {len(repo_secrets)} repo secrets")
        
        git_metadata = get_git_metadata()
        
        # Generate table rows
        diff_secrets_table_rows = generate_table_rows(diff_secrets)
        repo_secrets_table_rows = generate_table_rows(repo_secrets)
        
        # Log row generation results
        logging.debug(f"Generated {diff_secrets_table_rows.count('<tr>') if diff_secrets_table_rows else 0} diff secret table rows")
        logging.debug(f"Generated {repo_secrets_table_rows.count('<tr>') if repo_secrets_table_rows else 0} repo secret table rows")
        
        # Empty disallowed files section
        disallowed_files_section = ""

        # Get the hooks directory (parent of the script)
        hooks_dir = Path(__file__).parent.parent
        template_path = hooks_dir / "commit_scripts" / "templates" / "report.html"
        
        if not template_path.exists():
            # If template doesn't exist, use a simple built-in template
            logging.warning(f"Template file not found at {template_path}, using built-in template")
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
                # logging.error(f"Error formatting template: {e}, falling back to simple template")
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
    
    # Generate table rows for diff secrets and repo secrets
    diff_secrets_table_rows = generate_table_rows(diff_secrets)
    repo_secrets_table_rows = generate_table_rows(repo_secrets)
    
    # Create HTML template with tab buttons and styling
    html_content = """<!DOCTYPE html>
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
            <p><strong>Git Author:</strong> {author}</p>
            <p><strong>Repository:</strong> {repo_name}</p>
            <p><strong>Branch:</strong> {branch}</p>
            <p><strong>Commit Hash:</strong> {commit_hash}</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
        </div>

        <div class="tab-container">
            <div class="tab-buttons">
                <button class="tab-button active" onclick="showTab('diff-scan')">Push Scan Results</button>
                <button class="tab-button" onclick="showTab('repo-scan')">Repository Scan Results</button>
            </div>

            <div id="diff-scan" class="tab-content active">
                <h2>Files to be Pushed - Secrets Found: {diff_secrets_count}</h2>
                <table>
                    <tr>
                        <th style="width:5%">S.No</th>
                        <th style="width:25%">Filename</th>
                        <th style="width:10%">Line #</th>
                        <th style="width:60%">Secret</th>
                    </tr>
                    {diff_secrets_rows}
                </table>
            </div>

            <div id="repo-scan" class="tab-content">
                <h2>Repository Scan - Secrets Found: {repo_secrets_count}</h2>
                <table>
                    <tr>
                        <th style="width:5%">S.No</th>
                        <th style="width:25%">Filename</th>
                        <th style="width:10%">Line #</th>
                        <th style="width:60%">Secret</th>
                    </tr>
                    {repo_secrets_rows}
                </table>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabId) {{
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            // Remove active class from all buttons
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => button.classList.remove('active'));
            
            // Show the selected tab
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to the clicked button
            event.target.classList.add('active');
        }}
        
        // Print setup - show both tabs when printing
        window.onbeforeprint = function() {{
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.style.display = 'block';
            }});
        }};
        
        window.onafterprint = function() {{
            // Restore tab visibility after printing
            document.querySelectorAll('.tab-content').forEach(tab => {{
                if (tab.classList.contains('active')) {{
                    tab.style.display = 'block';
                }} else {{
                    tab.style.display = 'none';
                }}
            }});
        }};
    </script>
</body>
</html>"""

    # Replace placeholders with actual values
    formatted_html = html_content.format(
        author=safe_metadata['author'],
        repo_name=safe_metadata['repo_name'],
        branch=safe_metadata['branch'],
        commit_hash=safe_metadata['commit_hash'],
        timestamp=safe_metadata['timestamp'],
        diff_secrets_count=len(diff_secrets),
        repo_secrets_count=len(repo_secrets),
        diff_secrets_rows=diff_secrets_table_rows or "<tr><td colspan='4'>No secrets found in files to be pushed</td></tr>",
        repo_secrets_rows=repo_secrets_table_rows or "<tr><td colspan='4'>No secrets found in repository scan</td></tr>"
    )
    
    return formatted_html

def generate_table_rows(secrets):
    """Generate HTML table rows for secrets."""
    rows = []
    for i, s in enumerate(secrets, 1):
        row = "<tr>"
        row += f"<td>{i}</td>"
        row += f"<td>{html.escape(s.get('file_path', ''))}</td>"
        row += f"<td>{s.get('line_number', '')}</td>"
        row += f"<td><div class=\"secret-content\">{html.escape(mask_secret(s.get('line', '')))}</div></td>"
        row += "</tr>"
        rows.append(row)
    return ''.join(rows) if rows else ""

def main() -> None:
    """Main entry point for the secret scanner."""
    # Set up logging
    setup_logging()
    
    args = sys.argv[1:]
    scanner = SecretScanner()
    
    # Initialize variables to store results
    repo_results = []
    diff_results = []
    
    # Always scan the repository first
    logging.info("Scanning entire repository...")
    try:
        repo_results = scanner.scan_repository()
        if repo_results:
            print(f"Found {len(repo_results)} potential secrets in repository")
            logging.debug(f"Repository scan returned {len(repo_results)} secrets")
        else:
            logging.info("No secrets found in repository scan")
    except Exception as e:
        logging.error(f"Error scanning repository: {e}")
        sys.exit(1)
    
    # If --diff flag is present, also scan files to be pushed
    if "--diff" in args:
        logging.info("Scanning files to be pushed...")
        try:
            diff_results = scanner.scan_files_to_push()
            if diff_results:
                print(f"Found {len(diff_results)} potential secrets in files to be pushed")
                logging.debug(f"Diff scan returned {len(diff_results)} secrets")
            else:
                logging.info("No secrets found in files to be pushed")
        except Exception as e:
            logging.error(f"Error scanning files to be pushed: {e}")
            sys.exit(1)
    
    # Verify we have the expected data
    logging.debug(f"Before report generation: repo_results={len(repo_results)}, diff_results={len(diff_results)}")
    
    # Generate HTML report with both sets of results
    try:
        output_path = "secret_scan_report.html"
        success = generate_html_report(
            output_path,
            diff_secrets=diff_results,
            repo_secrets=repo_results
        )
        
        if success:
            print(f"HTML report generated at {output_path}")
            print(f"Repository secrets: {len(repo_results)}, Diff secrets: {len(diff_results)}")
        else:
            print("Failed to generate HTML report")
    except Exception as e:
        logging.error(f"Error generating HTML report: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()