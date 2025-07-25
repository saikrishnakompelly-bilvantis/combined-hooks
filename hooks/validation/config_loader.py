"""
Configuration Loader for API Validation

This module handles loading and parsing of validation configuration files.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Loads and manages validation configuration."""
    
    DEFAULT_CONFIG = {
        'file_types': {
            'extensions': ['.py', '.json'],
            'ignore_patterns': [
                '__pycache__',
                '.git',
                'node_modules',
                '.pytest_cache',
                'venv',
                '.venv',
                'target',
                'build',
                'dist'
            ]
        },
        'output': {
            'format': 'text',  # 'text' or 'json'
            'verbose': False
        },
        'pcf_rules': {
            # PCF-specific validation rules will be added here
            'enabled': True
        },
        'shp_ikp_rules': {
            # SHP/IKP-specific validation rules will be added here
            'enabled': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config loader with optional config file path."""
        self.config_path = config_path or self._find_config_file()
        self.config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return default config."""
        if self.config is not None:
            return self.config
        
        if self.config_path and os.path.exists(self.config_path):
            try:
                self.config = self._load_config_file(self.config_path)
                # Merge with defaults to ensure all keys exist
                self.config = self._merge_configs(self.DEFAULT_CONFIG, self.config)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                print("Using default configuration")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
        
        return self.config
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in current directory or parent directories."""
        config_names = [
            'api_validation.json',
            '.api_validation.json',
            'api_validation.yaml',
            'api_validation.yml',
            '.api_validation.yaml',
            '.api_validation.yml'
        ]
        
        current_dir = Path.cwd()
        
        # Search only in current directory to avoid git repository boundary issues
        for config_name in config_names:
            config_path = current_dir / config_name
            if config_path.exists():
                return str(config_path)
        
        return None
    
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON or YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if config_path.endswith('.json'):
            return json.loads(content) or {}
        elif config_path.endswith(('.yaml', '.yml')):
            return self._parse_simple_yaml(content) or {}
        else:
            raise ValueError(f"Unsupported config file format: {config_path}")
    
    def _parse_simple_yaml(self, content: str) -> Dict[str, Any]:
        """
        Parse simple YAML content without external dependencies.
        
        This is a basic parser that handles simple key-value pairs and nested objects.
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
    
    def _merge_configs(self, default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge custom config with default config."""
        result = default.copy()
        
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_default_config(self, output_path: str = 'api_validation.json'):
        """Save the default configuration to a file for reference."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=2)
        print(f"Default configuration saved to {output_path}") 