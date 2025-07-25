"""Configuration settings for secret scanning."""

from typing import List, Tuple, Dict

# Entropy thresholds for different types of secrets
ENTROPY_THRESHOLDS = {
    'password': 3.0,      # Lower threshold for passwords
    'api_key': 4.5,       # Higher for API keys
    'token': 4.0,         # Medium for tokens
    'secret': 4.0,        # Medium for generic secrets
    'default': 4.0        # Default threshold
}

# FAKE_API_KEY = "sk-5f8TzR9wLuN1qXk7GbJpV0cYq4MhXsB3dA2eKrYvT6WjLzPu9NcQ"
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
    (r'(?i)password[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 6, 'require_entropy': True, 'threshold': 3.0}),
    (r'(?i)pass[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 6, 'require_entropy': True, 'threshold': 3.0}),
    (r'(?i)pwd[_\-\.]?\s*[=:]\s*[^\s]{6,}', 'Password Assignment', {'min_length': 6, 'require_entropy': True, 'threshold': 3.0}),
    
    # Generic Secrets - Medium entropy requirement
    (r'(?i)(secret|token|credential)[_\-\.]?\s*[=:]\s*[^\s]{8,}', 'Generic Secret', {'min_length': 8, 'require_entropy': True, 'threshold': 4.0}),
    
    # Database Connection Strings - No entropy check needed, pattern is sufficient
    (r'(?i)(jdbc|mongodb|postgresql|mysql).*:\/\/[^\/\s]+:[^\/\s@]+@[^\/\s]+', 'Database Connection String', {'require_entropy': False}),
    
    # Environment Variables - Check based on name
    (r'(?i)export\s+(\w+)\s*=\s*[^\s]{6,}', 'Environment Variable', {'min_length': 6, 'check_name': True}),
]

# File extensions to exclude from scanning
EXCLUDED_EXTENSIONS = {
    'zip', 'gz', 'tar', 'rar', '7z', 'exe', 'dll', 'so', 'dylib',
    'jar', 'war', 'ear', 'class', 'pyc', 'o', 'a', 'lib', 'obj',
    'bin', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico', 'mp3', 'mp4',
    'avi', 'mov', 'wmv', 'flv', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'ppt', 'pptx', 'ttf', 'otf', 'woff', 'woff2', 'eot', 'svg',
    'tif', 'tiff', 'ico', 'webp'
}

# Directories to exclude from scanning
EXCLUDED_DIRECTORIES = {
    'distribution', 'node_modules', 'vendor', 'build', 'dist',
    'reports', 'scan_results', '__pycache__', '.git'
}

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