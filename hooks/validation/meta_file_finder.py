"""
Meta File Finder Module

This module is responsible for finding and reading api.meta files
throughout the repository structure.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


class MetaFileFinder:
    """Finds and manages api.meta files in the repository."""
    
    def __init__(self, root_path: Optional[str] = None):
        """Initialize with optional root path (defaults to current directory)."""
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self._meta_files_cache = None
    
    def find_meta_files(self, refresh_cache: bool = False) -> List[str]:
        """
        Find all api.meta files in the repository.
        
        Args:
            refresh_cache: If True, refresh the cached results
            
        Returns:
            List of paths to api.meta files
        """
        if self._meta_files_cache is not None and not refresh_cache:
            return self._meta_files_cache
        
        meta_files = []
        
        # Search for api.meta files recursively
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not self._should_skip_directory(d)]
                
                for file in files:
                    if self._is_meta_file(file):
                        file_path = os.path.join(root, file)
                        # Convert to relative path from root
                        relative_path = os.path.relpath(file_path, self.root_path)
                        meta_files.append(relative_path)
        
        except Exception as e:
            print(f"Error searching for meta files: {e}")
            return []
        
        # Cache the results
        self._meta_files_cache = meta_files
        return meta_files
    
    def _is_meta_file(self, filename: str) -> bool:
        """Check if a filename matches api.meta patterns."""
        meta_patterns = [
            'api.meta',
            'api.meta.yaml',
            'api.meta.yml',
            'api.meta.json',
            'API.meta',
            'API.META'
        ]
        return filename in meta_patterns
    
    def _should_skip_directory(self, dirname: str) -> bool:
        """Check if a directory should be skipped during search."""
        skip_patterns = [
            '.git',
            '.svn',
            '__pycache__',
            'node_modules',
            '.venv',
            'venv',
            '.pytest_cache',
            'target',
            'build',
            'dist',
            '.tox',
            '.coverage'
        ]
        return dirname.startswith('.') or dirname in skip_patterns
    
    def read_meta_file(self, meta_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read and parse a meta file.
        
        Args:
            meta_file_path: Path to the meta file
            
        Returns:
            Parsed content as dictionary, or None if failed
        """
        try:
            full_path = self.root_path / meta_file_path
            
            if not full_path.exists():
                print(f"Meta file does not exist: {meta_file_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse as different formats
            parsed_content = self._parse_meta_content(content, meta_file_path)
            return parsed_content
            
        except Exception as e:
            print(f"Error reading meta file {meta_file_path}: {e}")
            return None
    
    def _parse_meta_content(self, content: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse meta file content based on file extension or content format.
        
        Args:
            content: Raw file content
            file_path: Path to the file for format detection
            
        Returns:
            Parsed content as dictionary
        """
        # Try JSON first
        if file_path.endswith('.json') or self._looks_like_json(content):
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Failed to parse {file_path} as JSON: {e}")
        
        # Try YAML with simple built-in parser
        if file_path.endswith(('.yaml', '.yml')) or self._looks_like_yaml(content):
            try:
                return self._parse_simple_yaml(content)
            except Exception as e:
                print(f"Failed to parse {file_path} as YAML: {e}")
        
        # Try as properties file or key-value pairs
        try:
            return self._parse_properties(content)
        except Exception as e:
            print(f"Failed to parse {file_path} as properties: {e}")
        
        # If all parsing fails, return raw content
        print(f"Could not parse {file_path}, returning raw content")
        return {"raw_content": content}
    
    def _looks_like_json(self, content: str) -> bool:
        """Check if content looks like JSON."""
        stripped = content.strip()
        return stripped.startswith(('{', '['))
    
    def _looks_like_yaml(self, content: str) -> bool:
        """Check if content looks like YAML."""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # YAML typically has key: value format
                if ':' in line and not line.startswith('{'):
                    return True
                break
        return False
    
    def _parse_simple_yaml(self, content: str) -> Dict[str, Any]:
        """
        Parse simple YAML content without external dependencies.
        
        This is a basic parser that handles simple key-value pairs and nested objects.
        It's designed for basic API meta files, not complex YAML structures.
        """
        result = {}
        lines = content.split('\n')
        current_dict = result
        dict_stack = []
        
        for line in lines:
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Calculate indentation level
            indent = len(line) - len(line.lstrip())
            
            # Handle nested structure based on indentation
            while len(dict_stack) > 0 and indent <= dict_stack[-1][1]:
                dict_stack.pop()
            
            current_dict = dict_stack[-1][0] if dict_stack else result
            
            # Parse key-value pairs
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip()
                
                # Handle different value types
                if not value:
                    # Empty value, might be a nested object
                    nested_dict = {}
                    current_dict[key] = nested_dict
                    dict_stack.append((nested_dict, indent))
                else:
                    current_dict[key] = self._parse_yaml_value(value)
        
        return result
    
    def _parse_yaml_value(self, value: str) -> Any:
        """Parse a YAML value string into appropriate Python type."""
        value = value.strip()
        
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Handle boolean values
        if value.lower() in ('true', 'yes', 'on'):
            return True
        elif value.lower() in ('false', 'no', 'off'):
            return False
        
        # Handle null values
        if value.lower() in ('null', 'none', '~'):
            return None
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    def _parse_properties(self, content: str) -> Dict[str, Any]:
        """
        Parse content as properties/key-value pairs.
        
        Supports formats like:
        key=value
        key: value
        key value
        """
        result = {}
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Try different separators
            for separator in ['=', ':', ' ']:
                if separator in line:
                    parts = line.split(separator, 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        result[key] = value
                        break
            else:
                # If no separator found, treat as key with empty value
                result[line] = ""
        
        return result
    
    def get_meta_files_in_directory(self, directory: str) -> List[str]:
        """Get all meta files in a specific directory."""
        all_meta_files = self.find_meta_files()
        directory_meta_files = []
        
        for meta_file in all_meta_files:
            meta_dir = os.path.dirname(meta_file)
            if meta_dir == directory or meta_dir.startswith(directory + '/'):
                directory_meta_files.append(meta_file)
        
        return directory_meta_files
    
    def find_closest_meta_file(self, file_path: str) -> Optional[str]:
        """
        Find the closest api.meta file to a given file path.
        Searches up the directory tree but stays within repository boundary.
        """
        all_meta_files = self.find_meta_files()
        file_dir = os.path.dirname(file_path)
        
        # Start from the file's directory and go up, but stay within repo root
        current_dir = file_dir
        repo_root = str(self.root_path)
        
        while True:
            # Look for meta files in current directory
            for meta_file in all_meta_files:
                meta_dir = os.path.dirname(meta_file)
                if meta_dir == current_dir:
                    return meta_file
            
            # Stop if we've reached the repository root to avoid going outside repo boundary
            if os.path.abspath(current_dir) == os.path.abspath(repo_root):
                break
                
            # Move up one directory
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # Reached filesystem root
                break
            current_dir = parent_dir
        
        return None
    
    def print_meta_files_summary(self):
        """Print a summary of all found meta files."""
        meta_files = self.find_meta_files()
        
        print(f"\n=== API Meta Files Summary ===")
        print(f"Found {len(meta_files)} api.meta file(s):")
        
        for meta_file in meta_files:
            print(f"  📄 {meta_file}")
            
            # Try to read and show basic info
            content = self.read_meta_file(meta_file)
            if content:
                if isinstance(content, dict):
                    keys = list(content.keys())[:5]  # Show first 5 keys
                    print(f"     Keys: {keys}")
                    if len(content) > 5:
                        print(f"     ... and {len(content) - 5} more")
                else:
                    print(f"     Content type: {type(content)}")
            else:
                print("     ❌ Could not read file")
        
        print("=" * 30) 