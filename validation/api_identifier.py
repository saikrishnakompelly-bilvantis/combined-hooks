"""
API Identifier Module

This module identifies the type of API project based on specific rules:

PCF Projects:
- No folder named SHP or IKP on root, OR
- Repo name contains "-decision-service-"

SHP/IKP Projects:
- Folder named SHP or IKP exists on root, OR
- Repo name contains "-ds-"
"""

import os
import subprocess
from typing import Optional, List
from pathlib import Path


class APIIdentifier:
    """Identifies the type of API project based on folder structure and repo name."""
    
    def __init__(self, root_path: Optional[str] = None):
        """Initialize with optional root path (defaults to current directory)."""
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.repo_name = self._get_repo_name()
    
    def identify_api_type(self) -> str:
        """
        Identify API type based on the rules:
        
        General: No SHP/IKP folders AND doesn't contain "-decision-service-" (no validation)
        PCF: Contains "-decision-service-" (validate)
        SHP/IKP: Has SHP/IKP folders OR contains "-ds-" (validate)
        
        Returns:
            "General", "PCF", "SHP", "IKP", "SHP/IKP", or "UNKNOWN"
        """
        # Check for SHP/IKP folders on root
        shp_folder_exists = self._check_folder_exists("SHP")
        ikp_folder_exists = self._check_folder_exists("IKP")
        
        # Check repo name patterns
        is_decision_service = self._is_decision_service_repo()
        is_ds_repo = self._is_ds_repo()
        
        print(f"Repository name: {self.repo_name}")
        print(f"SHP folder exists: {shp_folder_exists}")
        print(f"IKP folder exists: {ikp_folder_exists}")
        print(f"Contains '-decision-service-': {is_decision_service}")
        print(f"Contains '-ds-': {is_ds_repo}")
        
        # Apply identification rules (order matters)
        if shp_folder_exists:
            return "SHP"
        elif ikp_folder_exists:
            return "IKP"
        elif is_ds_repo:
            # If -ds- pattern but no folders, could be either SHP or IKP
            # Return generic identifier for now
            return "SHP/IKP"
        elif is_decision_service:
            return "PCF"
        elif not shp_folder_exists and not ikp_folder_exists and not is_decision_service:
            # No SHP/IKP folders and no decision service pattern = General repository
            return "General"
        else:
            return "UNKNOWN"
    
    def _check_folder_exists(self, folder_name: str) -> bool:
        """Check if a specific folder exists in the root directory."""
        folder_path = self.root_path / folder_name
        return folder_path.exists() and folder_path.is_dir()
    
    def _get_repo_name(self) -> Optional[str]:
        """Get the repository name from git remote or directory name."""
        try:
            # Try to get repo name from git remote
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.root_path
            )
            
            remote_url = result.stdout.strip()
            if remote_url:
                # Extract repo name from URL
                # Handle both SSH and HTTPS URLs
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                
                repo_name = remote_url.split('/')[-1]
                return repo_name
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback to directory name
        return self.root_path.name
    
    def _is_decision_service_repo(self) -> bool:
        """Check if repo name contains '-decision-service-' pattern."""
        if not self.repo_name:
            return False
        return '-decision-service-' in self.repo_name.lower()
    
    def _is_ds_repo(self) -> bool:
        """Check if repo name contains '-ds-' pattern."""
        if not self.repo_name:
            return False
        return '-ds-' in self.repo_name.lower()
    
    def get_root_folders(self) -> List[str]:
        """Get list of all folders in the root directory."""
        try:
            return [item.name for item in self.root_path.iterdir() 
                   if item.is_dir() and not item.name.startswith('.')]
        except Exception:
            return []
    
    def print_identification_details(self):
        """Print detailed information about the identification process."""
        print("=== API Type Identification Details ===")
        print(f"Root path: {self.root_path}")
        print(f"Repository name: {self.repo_name}")
        print(f"Root folders: {self.get_root_folders()}")
        print(f"SHP folder exists: {self._check_folder_exists('SHP')}")
        print(f"IKP folder exists: {self._check_folder_exists('IKP')}")
        print(f"Contains '-decision-service-': {self._is_decision_service_repo()}")
        print(f"Contains '-ds-': {self._is_ds_repo()}")
        print(f"Identified type: {self.identify_api_type()}")
        print("=" * 40) 