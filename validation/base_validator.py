"""
Base Validator Class

This module provides the base class for all API validators.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseValidator(ABC):
    """Abstract base class for all API validators."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize validator with configuration."""
        self.config = config
        self.errors = []
        self.warnings = []
    
    @abstractmethod
    def validate_file(self, file_path: str, content: str) -> bool:
        """
        Validate a file against specific API rules.
        
        Args:
            file_path: Path to the file being validated
            content: Content of the file
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    def add_error(self, message: str, file_path: str, line_number: Optional[int] = None):
        """Add a validation error."""
        error_msg = f"{file_path}"
        if line_number:
            error_msg += f":{line_number}"
        error_msg += f" - {message}"
        self.errors.append(error_msg)
    
    def add_warning(self, message: str, file_path: str, line_number: Optional[int] = None):
        """Add a validation warning."""
        warning_msg = f"{file_path}"
        if line_number:
            warning_msg += f":{line_number}"
        warning_msg += f" - {message}"
        self.warnings.append(warning_msg)
    
    def get_errors(self) -> List[str]:
        """Get all validation errors."""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get all validation warnings."""
        return self.warnings.copy()
    
    def clear_results(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
    
    def is_enabled(self, validator_name: str) -> bool:
        """Check if a specific validator is enabled in config."""
        return self.config.get('validators', {}).get(validator_name, {}).get('enabled', True)
    
    def get_rule_config(self, validator_name: str, rule_name: str, default=None):
        """Get configuration for a specific rule."""
        return (self.config.get('validators', {})
                .get(validator_name, {})
                .get('rules', {})
                .get(rule_name, default))
    
    def should_validate_file(self, file_path: str) -> bool:
        """
        Check if a file should be validated based on its type and path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be validated, False otherwise
        """
        # This can be overridden by specific validators for file-type filtering
        return True 