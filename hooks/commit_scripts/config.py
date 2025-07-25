"""Configuration settings for secret scanning."""

import os
import sys
from typing import List, Tuple, Dict, Set
import fnmatch

# Ensure the current directory is in the path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import scan_config if available
try:
    from scan_config import get_exclusion_patterns, load_exclusions
except ImportError:
    # Fallback functions if scan_config is not available
    def get_exclusion_patterns():
        return []
    
    def load_exclusions():
        return {
            "file_extensions": [],
            "directories": [],
            "additional_exclusions": []
        }

# Entropy thresholds for different types of secrets
ENTROPY_THRESHOLDS = {
    'password': 4.0,      # Lower threshold for passwords
    'api_key': 4.5,       # Higher for API keys
    'token': 4.0,         # Medium for tokens
    'secret': 4.0,        # Medium for generic secrets
    'default': 4.0        # Default threshold
}

# Patterns for detecting secrets with their specific requirements
PATTERNS: List[Tuple[str, str, Dict]] = [
    # AWS - High entropy requirement
    (r'(?i)aws[_\-\.]*(access|secret|key)[_\-\.]*\s*[=:]\s*[A-Za-z0-9/\+=]{16,}', 'AWS Credential', {'min_length': 16, 'require_entropy': True, 'threshold': 4.5}),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID', {'min_length': 20, 'require_entropy': True, 'threshold': 4.5}),
    
    # Private Keys - No entropy check needed, pattern is sufficient
    (r'(?i)-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)\s+PRIVATE\s+KEY-----[A-Za-z0-9/\+=\s]+-----END', 'Private Key', {'require_entropy': False}),
    (r'(?i)ssh-rsa\s+[A-Za-z0-9/\+=]{32,}', 'SSH Key', {'require_entropy': False}),
    
    # API Keys & Tokens - Medium entropy requirement
    (r'(?i)api[_\-\.]?key[_\-\.]*\s*[=:]\s*[A-Za-z0-9_\-]{8,}', 'API Key', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.=]{20,}', 'Bearer Token', {'min_length': 20, 'require_entropy': True, 'threshold': 4.0}),
    (r'ghp_[0-9a-zA-Z]{36}', 'GitHub Personal Access Token', {'require_entropy': False}),  # Pattern is specific enough
    (r'github_pat_[0-9a-zA-Z]{82}', 'GitHub Fine-grained PAT', {'require_entropy': False}),  # Pattern is specific enough
    (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key', {'require_entropy': False}),  # Pattern is specific enough
    (r'AIza[0-9A-Za-z\-_]{35}', 'Google API Key', {'require_entropy': False}),  # Pattern is specific enough
    
    # JWT Tokens - No entropy check needed, structure is sufficient
    (r'eyJ[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,}', 'JWT Token', {'require_entropy': False}),
    
    # Passwords - Lower entropy requirement
    (r'(?i)password[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    (r'(?i)pass[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    (r'(?i)pwd[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    
    # Generic Secrets - Medium entropy requirement
    (r'(?i)(secret|token|credential)[_\-\.]?\s*[=:]\s*[^\s]{8,}', 'Generic Secret', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    
    # Database Connection Strings - No entropy check needed, pattern is sufficient
    (r'(?i)(jdbc|mongodb|postgresql|mysql).*:\/\/[^\/\s]+:[^\/\s@]+@[^\/\s]+', 'Database Connection String', {'require_entropy': False}),
    
    # Environment Variables - Check based on name
    (r'(?i)export\s+(\w+)\s*=\s*[^\s]{6,}', 'Environment Variable', {'min_length': 6, 'check_name': True}),
]

# Load exclusions from configuration if available
def _load_exclusions() -> tuple:
    """
    Load exclusions from YAML file if available, otherwise use defaults.
    Returns tuple of (excluded_extensions, excluded_directories)
    """
    # Load exclusions from YAML - Exclusions are now mandatory, not optional
    exclusions = load_exclusions()
    
    # Extract file extensions (remove the asterisk and dot)
    extensions = set()
    for ext_pattern in exclusions.get('file_extensions', []):
        if ext_pattern.startswith('*.'):
            ext = ext_pattern[2:]
            extensions.add(ext)
        elif ext_pattern.startswith('*'):
            ext = ext_pattern[1:]
            extensions.add(ext)
    
    # Extract directory names (remove the ** and slashes)
    directories = set()
    for dir_pattern in exclusions.get('directories', []):
        if '/**' in dir_pattern:
            dir_name = dir_pattern.split('/**')[0]
            if dir_name.startswith('**/'):
                dir_name = dir_name[3:]
            directories.add(dir_name)
        elif dir_pattern.endswith('/'):
            dir_name = dir_pattern[:-1]
            if dir_name.startswith('**/'):
                dir_name = dir_name[3:]
            directories.add(dir_name)
        else:
            # Try to extract directory name from pattern
            parts = dir_pattern.replace('**/', '').replace('/', '')
            if parts:
                directories.add(parts)
    
    return extensions, directories

# File extensions to exclude from scanning - load from YAML if available
EXCLUDED_EXTENSIONS_DEFAULT = {
    'zip', 'gz', 'tar', 'rar', '7z', 'exe', 'dll', 'so', 'dylib',
    'jar', 'war', 'ear', 'class', 'pyc', 'o', 'a', 'lib', 'obj',
    'bin', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico', 'mp3', 'mp4',
    'avi', 'mov', 'wmv', 'flv', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'ppt', 'pptx', 'ttf', 'otf', 'woff', 'woff2', 'eot', 'svg',
    'tif', 'tiff', 'ico', 'webp',
    # Add new data file types
    'xlsx', 'xlsb', 'csv', 'tsv', 'json', 'xml', 'yaml', 'yml',
    'parquet', 'avro', 'orc'
}

# Directories to exclude from scanning - load from YAML if available
EXCLUDED_DIRECTORIES_DEFAULT = {
    'distribution', 'node_modules', 'vendor', 'build', 'dist',
    'reports', 'scan_results', '__pycache__', '.git',
    'test', 'tests', 'Test', 'Tests'  # Always exclude test directories
}

# Try to load exclusions, but fall back to defaults if there's an error
try:
    yaml_extensions, yaml_directories = _load_exclusions()
    EXCLUDED_EXTENSIONS = EXCLUDED_EXTENSIONS_DEFAULT.union(yaml_extensions)
    EXCLUDED_DIRECTORIES = EXCLUDED_DIRECTORIES_DEFAULT.union(yaml_directories)
except Exception as e:
    # If there's an error loading the exclusions, use the defaults
    print(f"Error loading exclusions: {e}. Using default exclusions.")
    EXCLUDED_EXTENSIONS = EXCLUDED_EXTENSIONS_DEFAULT
    EXCLUDED_DIRECTORIES = EXCLUDED_DIRECTORIES_DEFAULT

# Disallowed file extensions that might contain sensitive data
DISALLOWED_EXTENSIONS = {
    '.crt', '.cer', '.ca-bundle', '.p7b', '.p7c', '.p7s', '.pem',
    '.jceks', '.key', '.keystore', '.jks', '.p12', '.pfx'
}

# HTML report configuration
HTML_CONFIG = {
    'title': 'Genie - Secret Scan Results',
    'styles': {
        'primary_color': '#07439C',
        'error_color': '#d32f2f',
        'background_color': '#f5f5f5',
        'container_background': 'white',
        'header_background': '#f8f9fa',
    }
}

# Function to check if a file should be excluded based on exclusions
def should_exclude_file(file_path: str) -> bool:
    """
    Check if a file should be excluded from scanning based on its path.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if the file should be excluded, False otherwise
    """
    # First check against all exclusion patterns from the YAML file
    # This ensures glob patterns like **/*test*.* are properly evaluated
    for pattern in get_exclusion_patterns():
        if fnmatch.fnmatch(file_path, pattern):
            return True
    
    # Skip files with excluded extensions
    _, ext = os.path.splitext(file_path)
    if ext and ext.lower().lstrip('.') in EXCLUDED_EXTENSIONS:
        return True
    
    # Skip files in excluded directories
    path_parts = file_path.split(os.path.sep)
    for excluded_dir in EXCLUDED_DIRECTORIES:
        if excluded_dir in path_parts:
            return True
    
    # Check if the filename contains "test" or "Test"
    file_name = os.path.basename(file_path)
    if "test" in file_name.lower():
        return True
    
    # Special handling for txt and md files - only include if they have project-related content
    # This is a placeholder - the actual implementation would need to examine the file content
    # For now, we'll be conservative and scan txt/md files in case they contain secrets
    
    return False 