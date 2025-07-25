#!/usr/bin/env python3
"""
API Validation Module

This module contains the core logic for validating code against API rules.
API identification logic:
- PCF: No SHP/IKP folder on root OR repo name contains "-decision-service-"
- SHP/IKP: SHP/IKP folder exists on root OR repo name contains "-ds-"

Only validates repos classified as PCF or SHP/IKP.
For these repos, looks for api.meta files to validate against.
Implements 20 compliance rules from compliance_rules.csv with updated values.
Features interactive UI for push operations with validation failures.
"""

import sys
import argparse
import subprocess
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from .config_loader import ConfigLoader
from .api_identifier import APIIdentifier
from .meta_file_finder import MetaFileFinder
from .validators.meta_validator import MetaValidator
from .git_utils import GitUtils


class APIValidator:
    """Main validator class that orchestrates all API validation rules."""
    
    def __init__(self, config_path: Optional[str] = None, repo_path: Optional[str] = None):
        """Initialize the validator with configuration."""
        self.repo_path = repo_path or os.getcwd()
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()
        self.api_identifier = APIIdentifier(self.repo_path)
        self.meta_finder = MetaFileFinder(self.repo_path)
        self.meta_validator = MetaValidator(self.config)
        self.git_utils = GitUtils(self.repo_path)
        self.errors = []
        self.warnings = []
        
        # Identify the API type for this repository
        self.api_type = self.api_identifier.identify_api_type()
        print(f"Detected API type: {self.api_type}")
        
        # Check if this repo should be validated
        if not self._should_validate_repo():
            print(f"Repository type '{self.api_type}' does not require API validation. Skipping...")
            self.skip_validation = True
        else:
            self.skip_validation = False
            # Find api.meta files for validation
            self.meta_files = self.meta_finder.find_meta_files()
            print(f"Found {len(self.meta_files)} api.meta file(s): {self.meta_files}")
    
    def _should_validate_repo(self) -> bool:
        """Check if this repository type should be validated."""
        valid_types = ['PCF', 'SHP', 'IKP', 'SHP/IKP']
        return self.api_type in valid_types
    
    def validate_staged_files(self) -> bool:
        """Validate only staged files for pre-commit hook."""
        if self.skip_validation:
            return True
            
        staged_files = self._get_staged_files()
        return self._validate_files(staged_files, mode='commit')
    
    def validate_commit_range(self, commit_range: str, interactive: bool = False) -> bool:
        """Validate files changed in a commit range for pre-push hook."""
        if self.skip_validation:
            return True
            
        changed_files = self._get_changed_files_in_range(commit_range)
        return self._validate_files(changed_files, mode='push', interactive=interactive)
    
    def validate_files(self, file_paths: List[str]) -> bool:
        """Validate specific files."""
        if self.skip_validation:
            return True
            
        return self._validate_files(file_paths, mode='manual')
    
    def _validate_files(self, file_paths: List[str], mode: str = 'manual', interactive: bool = False) -> bool:
        """Internal method to validate a list of files."""
        if not file_paths:
            print("No files to validate")
            return True
        
        print(f"Validating {len(file_paths)} files for {self.api_type} project...")
        
        # First, validate all api.meta files against compliance rules
        meta_validation_passed = self._validate_meta_files()
        
        # Filter files based on configuration
        filtered_files = self._filter_files_by_type(file_paths)
        
        validation_passed = meta_validation_passed
        
        for file_path in filtered_files:
            print(f"Validating: {file_path}")
            
            if not os.path.exists(file_path):
                continue
            
            file_content = self._read_file_content(file_path)
            if file_content is None:
                continue
            
            # Apply validation rules based on API type
            try:
                if self.api_type == "PCF":
                    validation_passed &= self._validate_pcf_file(file_path, file_content)
                elif self.api_type in ["SHP", "IKP", "SHP/IKP"]:
                    validation_passed &= self._validate_shp_ikp_file(file_path, file_content)
                else:
                    self.add_warning(f"Unknown API type: {self.api_type}, skipping validation", file_path)
            except Exception as e:
                self.errors.append(f"Validation error in {file_path}: {str(e)}")
                validation_passed = False
        
        # Collect meta validator errors
        self.errors.extend(self.meta_validator.get_errors())
        self.warnings.extend(self.meta_validator.get_warnings())
        
        # Handle validation results based on mode
        has_errors = len(self.errors) > 0
        if (not validation_passed or has_errors) and mode == 'push' and interactive:
            return self._handle_interactive_validation_failure()
        else:
            # Print results for non-interactive modes
            self._print_results()
            return validation_passed and len(self.errors) == 0
    
    def _handle_interactive_validation_failure(self) -> bool:
        """Handle validation failures in interactive mode (push with UI)."""
        print("\n🚨 Validation failures detected during push operation...")
        
        # Prepare validation results for UI
        validation_results = {
            'errors': self.errors,
            'warnings': self.warnings,
            'meta_files': self.meta_files,
            'api_type': self.api_type
        }
        
        # Show interactive dialog
        try:
            from .ui.validation_dialog import show_validation_dialog
            
            result, justification = show_validation_dialog(validation_results, repo_path=self.repo_path)
            
            if result == 'proceed':
                print("\n✅ User chose to proceed with validation failures")
                print(f"Justification: {justification}")
                
                # Append validation details to commit message
                success = self.git_utils.append_to_commit_message(
                    justification, 
                    self.errors, 
                    self.warnings
                )
                
                if success:
                    print("✅ Commit message updated with validation override details")
                    return True
                else:
                    print("❌ Failed to update commit message")
                    return False
            else:
                print("\n🛑 Push cancelled by user")
                return False
                
        except ImportError as e:
            print(f"⚠️ GUI not available ({e}), falling back to console mode")
            return self._handle_console_validation_failure()
        except Exception as e:
            print(f"❌ Error in interactive mode: {e}")
            print("Falling back to console mode")
            return self._handle_console_validation_failure()
    
    def _handle_console_validation_failure(self) -> bool:
        """Handle validation failures in console mode."""
        from .ui.validation_dialog import _console_fallback
        
        validation_results = {
            'errors': self.errors,
            'warnings': self.warnings,
            'meta_files': self.meta_files,
            'api_type': self.api_type
        }
        
        result, justification = _console_fallback(validation_results)
        
        if result == 'proceed':
            success = self.git_utils.append_to_commit_message(
                justification, 
                self.errors, 
                self.warnings
            )
            
            if success:
                print("✅ Commit message updated with validation override details")
                return True
            else:
                print("❌ Failed to update commit message")
                return False
        else:
            return False
    
    def _validate_meta_files(self) -> bool:
        """Validate all found api.meta files against compliance rules."""
        if not self.meta_files:
            # For PCF and SHP/IKP repositories, api.meta files are required
            if self.api_type in ['PCF', 'SHP', 'IKP', 'SHP/IKP']:
                self.add_error("No api.meta files found in repository - api.meta files are required for PCF and SHP/IKP projects", "repository")
                print("❌ No api.meta files found - this is required for PCF and SHP/IKP projects")
                return False
            else:
                self.add_warning("No api.meta files found in repository", "repository")
                print("⚠️  No api.meta files found - compliance validation skipped")
                return True
        
        print(f"\n🔍 Validating {len(self.meta_files)} api.meta file(s) against compliance rules...")
        
        validation_passed = True
        
        for meta_file in self.meta_files:
            print(f"  📄 Validating meta file: {meta_file}")
            
            meta_content = self.meta_finder.read_meta_file(meta_file)
            if meta_content is None:
                self.add_error(f"Could not read meta file: {meta_file}", meta_file)
                validation_passed = False
                continue
            
            # Validate against all 20 compliance rules
            file_validation_passed = self.meta_validator.validate_meta_content(meta_content, meta_file)
            if not file_validation_passed:
                validation_passed = False
                print(f"    ❌ Compliance validation failed for {meta_file}")
            else:
                print(f"    ✅ Compliance validation passed for {meta_file}")
        
        return validation_passed
    
    def _validate_pcf_file(self, file_path: str, content: str) -> bool:
        """Validate files for PCF projects."""
        print(f"  Applying PCF validation rules to {file_path}")
        
        # Check if this file is related to any api.meta files
        relevant_meta_files = self._find_relevant_meta_files(file_path)
        
        if relevant_meta_files:
            print(f"    Found relevant api.meta files: {relevant_meta_files}")
            # Meta files are already validated in _validate_meta_files()
            # Here you can add file-specific validation logic if needed
        else:
            print(f"    No relevant api.meta files found for {file_path}")
        
        # Add any PCF-specific file validation logic here
        # For example: validate that certain endpoints are implemented
        # validate code style, etc.
        
        return True
    
    def _validate_shp_ikp_file(self, file_path: str, content: str) -> bool:
        """Validate files for SHP/IKP projects."""
        print(f"  Applying SHP/IKP validation rules to {file_path}")
        
        # Check if this file is related to any api.meta files
        relevant_meta_files = self._find_relevant_meta_files(file_path)
        
        if relevant_meta_files:
            print(f"    Found relevant api.meta files: {relevant_meta_files}")
            # Meta files are already validated in _validate_meta_files()
            # Here you can add file-specific validation logic if needed
        else:
            print(f"    No relevant api.meta files found for {file_path}")
        
        # Add any SHP/IKP-specific file validation logic here
        # For example: validate specific SHP/IKP requirements
        
        return True
    
    def _find_relevant_meta_files(self, file_path: str) -> List[str]:
        """Find api.meta files that are relevant to the given file path."""
        relevant_files = []
        file_dir = os.path.dirname(file_path)
        
        for meta_file in self.meta_files:
            meta_dir = os.path.dirname(meta_file)
            
            # Check if the file is in the same directory or subdirectory as the meta file
            if file_dir.startswith(meta_dir) or meta_dir.startswith(file_dir):
                relevant_files.append(meta_file)
        
        return relevant_files
    
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
    
    def _get_staged_files(self) -> List[str]:
        """Get list of staged files from git."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    def _get_changed_files_in_range(self, commit_range: str) -> List[str]:
        """Get list of files changed in a commit range."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', commit_range],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    def _filter_files_by_type(self, file_paths: List[str]) -> List[str]:
        """Filter files based on extensions and patterns from config."""
        # Default to Python and JSON files if no config specified
        extensions = self.config.get('file_types', {}).get('extensions', ['.py', '.json'])
        ignore_patterns = self.config.get('file_types', {}).get('ignore_patterns', [])
        
        filtered_files = []
        for file_path in file_paths:
            # Check extension
            if any(file_path.endswith(ext) for ext in extensions):
                # Check ignore patterns
                if not any(pattern in file_path for pattern in ignore_patterns):
                    filtered_files.append(file_path)
        
        return filtered_files
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.errors.append(f"Could not read file {file_path}: {str(e)}")
            return None
    
    def _print_results(self):
        """Print validation results."""
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ No validation errors found")
    
    def print_compliance_summary(self):
        """Print a summary of compliance validation results."""
        print("\n📋 Compliance Validation Summary:")
        print(f"Meta files validated: {len(self.meta_files)}")
        
        meta_errors = self.meta_validator.get_errors()
        meta_warnings = self.meta_validator.get_warnings()
        
        print(f"Compliance errors: {len(meta_errors)}")
        print(f"Compliance warnings: {len(meta_warnings)}")
        
        if meta_errors:
            print("\n❌ Compliance Errors:")
            for error in meta_errors:
                print(f"  - {error}")
        
        if meta_warnings:
            print("\n⚠️  Compliance Warnings:")
            for warning in meta_warnings:
                print(f"  - {warning}")
        
        if not meta_errors and not meta_warnings:
            print("✅ All compliance rules passed!")


def main():
    """Main entry point for the API validator."""
    parser = argparse.ArgumentParser(description='API Validation Tool')
    parser.add_argument('--staged-files', action='store_true', 
                       help='Validate only staged files (for pre-commit hook)')
    parser.add_argument('--comprehensive', action='store_true', 
                       help='Run comprehensive validation (for pre-push hook)')
    parser.add_argument('--commit-range', type=str, 
                       help='Validate files in commit range (for pre-push hook)')
    parser.add_argument('--files', nargs='+', 
                       help='Specific files to validate')
    parser.add_argument('--config', type=str, 
                       help='Path to configuration file')
    parser.add_argument('--identify-only', action='store_true',
                       help='Only identify API type without validation')
    parser.add_argument('--find-meta', action='store_true',
                       help='Find and list all api.meta files')
    parser.add_argument('--compliance-only', action='store_true',
                       help='Only run compliance validation on api.meta files')
    parser.add_argument('--interactive', action='store_true',
                       help='Enable interactive mode for validation failures (used by pre-push hook)')
    parser.add_argument('--repo-path', type=str,
                       help='Path to the repository to validate (defaults to current directory)')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = APIValidator(args.config, args.repo_path)
    
    # If only identification is requested
    if args.identify_only:
        print(f"API Type: {validator.api_type}")
        print(f"Should validate: {not validator.skip_validation}")
        sys.exit(0)
    
    # If only meta file discovery is requested
    if args.find_meta:
        print(f"API Type: {validator.api_type}")
        if validator.skip_validation:
            print("Repository does not require API validation")
        else:
            print(f"Found api.meta files: {validator.meta_files}")
            for meta_file in validator.meta_files:
                content = validator.meta_finder.read_meta_file(meta_file)
                if content:
                    print(f"\nContent of {meta_file}:")
                    print(content)
        sys.exit(0)
    
    # If only compliance validation is requested
    if args.compliance_only:
        if validator.skip_validation:
            print("Repository does not require API validation")
            sys.exit(0)
        
        success = validator._validate_meta_files()
        validator.print_compliance_summary()
        sys.exit(0 if success else 1)
    
    # Determine validation mode
    success = True
    
    if args.staged_files:
        success = validator.validate_staged_files()
    elif args.commit_range:
        success = validator.validate_commit_range(args.commit_range, interactive=args.interactive)
    elif args.files:
        success = validator.validate_files(args.files)
    else:
        print("No validation mode specified. Use --help for options.")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 