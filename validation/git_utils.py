"""
Git Utilities

This module provides utilities for interacting with git,
specifically for modifying commit messages during push operations.
"""

import subprocess
import tempfile
import os
from typing import List, Optional
from datetime import datetime


class GitUtils:
    """Utilities for git operations."""
    
    def __init__(self, repo_path: Optional[str] = None):
        """Initialize with optional repository path."""
        self.repo_path = repo_path or os.getcwd()
    
    def get_last_commit_message(self) -> str:
        """Get the message of the last commit."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%B'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get last commit message: {e}")
    
    def get_last_commit_hash(self) -> str:
        """Get the hash of the last commit."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get last commit hash: {e}")
    
    def amend_commit_message(self, new_message: str) -> bool:
        """
        Amend the last commit with a new message.
        Returns True if successful, False otherwise.
        """
        if not self._can_amend_commit():
            print("Cannot amend commit (may have uncommitted changes or other git state issues). Please commit or stash your changes and try again.")
            return False
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(new_message)
                temp_file = f.name
            try:
                subprocess.run(
                    ['git', 'commit', '--amend', '-F', temp_file],
                    check=True,
                    capture_output=True,
                    cwd=self.repo_path
                )
                return True
            finally:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
        except subprocess.CalledProcessError as e:
            print(f"Failed to amend commit message: {e}")
            return False

    def save_validation_details_local(self, justification: str, errors: List[str], warnings: List[str]):
        """
        Save the full validation details to a local file in the repo root (not committed).
        Includes commit id, branch, and GitHub user.
        """
        commit_id = self.get_last_commit_hash()
        short_commit_id = commit_id[:7] if commit_id else "unknown"
        branch = self.get_current_branch() or "(unknown)"
        # Get GitHub user from git config
        try:
            user_name = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True, check=True, cwd=self.repo_path).stdout.strip()
            user_email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True, check=True, cwd=self.repo_path).stdout.strip()
        except Exception:
            user_name = "(unknown)"
            user_email = "(unknown)"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f".apigenie_validation_{short_commit_id}_{timestamp}.txt"
        file_path = os.path.join(self.repo_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Validation Override Record\n")
            f.write("========================\n\n")
            f.write(f"Commit: {commit_id}\n")
            f.write(f"Branch: {branch}\n")
            f.write(f"GitHub User: {user_name} <{user_email}>\n")
            f.write(f"Timestamp: {timestamp}\n\n")
            f.write(f"JUSTIFICATION: {justification}\n\n")
            if errors:
                f.write(f"VALIDATION ERRORS ({len(errors)}):\n")
                for error in errors:
                    f.write(f"  - {error}\n")
                f.write("\n")
            if warnings:
                f.write(f"VALIDATION WARNINGS ({len(warnings)}):\n")
                for warning in warnings:
                    f.write(f"  - {warning}\n")
                f.write("\n")
            f.write("========================\n")
        print(f"Full validation details saved locally to {file_path} (not committed)")
    
    def _can_amend_commit(self) -> bool:
        """Check if the current git state allows amending the last commit (ignores untracked files)."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            # Ignore untracked files (lines starting with '??')
            lines = [line for line in result.stdout.splitlines() if not line.startswith('??')]
            if lines:
                return False
            subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                check=True,
                cwd=self.repo_path
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_validation_failure_appendix(
        self,
        justification: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> str:
        """
        Create a summary appendix for the commit message with validation override info.
        Only include counts, justification, and a reference to the local file.
        """
        appendix_parts = [
            "\n" + "="*50,
            "⚠️  VALIDATION OVERRIDE NOTICE",
            "="*50,
            "",
            f"JUSTIFICATION: {justification}",
            f"Validation errors: {len(errors)}",
            f"Validation warnings: {len(warnings)}",
            "",
            "Full validation details are saved locally in a file named .apigenie_validation_<commit_id>_<timestamp>.txt in the repo root (not committed).",
            "Review and address these issues in a follow-up commit.",
            "="*50
        ]
        return "\n".join(appendix_parts)
    
    def append_to_commit_message(
        self,
        justification: str,
        errors: List[str],
        warnings: List[str]
    ) -> bool:
        """
        Append validation failure details to the last commit message.
        Also save full details to a local file (not committed).
        """
        try:
            current_message = self.get_last_commit_message()
            appendix = self.create_validation_failure_appendix(justification, errors, warnings)
            new_message = current_message + appendix
            success = self.amend_commit_message(new_message)
            if success:
                self.save_validation_details_local(justification, errors, warnings)
            return success
        except Exception as e:
            print(f"Failed to append to commit message: {e}")
            return False
    
    def is_git_repository(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                check=True,
                cwd=self.repo_path
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_current_branch(self) -> Optional[str]:
        """Get the name of the current git branch."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False 