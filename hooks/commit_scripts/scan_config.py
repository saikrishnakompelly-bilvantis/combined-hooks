#!/usr/bin/env python3
"""Configuration module for Genie's secret scanning."""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import datetime
import shutil
import sys
import subprocess

# Configuration constants
CONFIG_FILENAME = ".genie_scan_config.json"
EXCLUSIONS_FILENAME = "exclusions.json"
DEFAULT_CONFIG = {
    "scan_mode": "diff",  # Options: "diff", "repo", "both"
    "scan_changed_lines_only": True,
    "last_updated": None
    # use_exclusions removed - now always enabled
}

def get_config_path():
    """Get the path to the configuration file."""
    home_dir = os.path.expanduser('~')
    genie_dir = os.path.join(home_dir, '.genie')
    return os.path.join(genie_dir, CONFIG_FILENAME)

def get_exclusions_path():
    """Get the path to the exclusions JSON file."""
    # First check if there's a local exclusions file in the repository
    local_path = os.path.join(os.getcwd(), EXCLUSIONS_FILENAME)
    if os.path.exists(local_path):
        return local_path
    
    # Fall back to the global exclusions file
    home_dir = os.path.expanduser('~')
    genie_dir = os.path.join(home_dir, '.genie')
    return os.path.join(genie_dir, EXCLUSIONS_FILENAME)

def get_default_exclusions_path():
    """Get the path to the default exclusions file included with Genie."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, EXCLUSIONS_FILENAME)

def load_config():
    """Load configuration from file or use defaults."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            # Ensure all required fields exist
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception:
            pass
    
    # If we reached here, either the file doesn't exist or there was an error
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file."""
    # Update last modified time
    config["last_updated"] = datetime.datetime.now().isoformat()
    
    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)
    
    # Create directory if it doesn't exist
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Always ensure the exclusions file exists since exclusions are mandatory
        ensure_exclusions_file_exists()
            
        return True
    except Exception:
        return False

def ensure_exclusions_file_exists():
    """Ensure the exclusions file exists, creating it from defaults if needed."""
    exclusions_path = get_exclusions_path()
    
    # If user's exclusions file doesn't exist, copy the default
    if not os.path.exists(exclusions_path):
        default_path = get_default_exclusions_path()
        if os.path.exists(default_path):
            # Create the destination directory if needed
            dest_dir = os.path.dirname(exclusions_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            # Copy the default file
            shutil.copy2(default_path, exclusions_path)
        else:
            # Create an empty exclusions file if default doesn't exist
            create_default_exclusions(exclusions_path)

def create_default_exclusions(path):
    """Create a default exclusions file at the specified path."""
    default_exclusions = {
        "file_extensions": [
            "*.jar", "*.war", "*.ear", "*.pyc", "*.class", 
            "*.log", "*.tmp", "*.DS_Store", "*.pdf",
            "*.png", "*.jpg", "*.jpeg", "*.gif",
            "*.xlsx", "*.xlsb", "*.xls", "*.csv",
            "**/*test*.*", "**/*Test*.*"  # Files with "test" anywhere in the name
        ],
        "directories": [
            "**/node_modules/**", "**/dist/**", "**/build/**",
            "**/target/**", "**/.git/**", "**/test/**", "**/tests/**",
            "**/Test/**", "**/Tests/**", "**/*test*/**", "**/*Test*/**"  # Expanded patterns for test directories
        ],
        "additional_exclusions": []
    }
    
    # Create the directory if it doesn't exist
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    
    # Write the default exclusions as JSON instead of YAML
    with open(path, 'w') as f:
        json.dump(default_exclusions, f, indent=2)

def load_exclusions():
    """Load exclusions from the JSON file."""
    exclusions_path = get_exclusions_path()
    
    if not os.path.exists(exclusions_path):
        ensure_exclusions_file_exists()
    
    if os.path.exists(exclusions_path):
        try:
            with open(exclusions_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading exclusions: {e}")
    
    # Return default exclusions if unable to load
    return {
        "file_extensions": [],
        "directories": [],
        "additional_exclusions": []
    }

def get_scan_mode():
    """Get the current scan mode."""
    config = load_config()
    return config.get("scan_mode", "both")

def should_scan_diff():
    """Check if diff scanning is enabled."""
    mode = get_scan_mode()
    return mode in ["diff", "both"]

def should_scan_repo():
    """Check if repository scanning is enabled."""
    mode = get_scan_mode()
    return mode in ["repo", "both"]

def should_scan_changed_lines_only():
    """Check if only changed lines should be scanned instead of entire files."""
    config = load_config()
    return config.get("scan_changed_lines_only", True)

def should_use_exclusions():
    """Check if exclusions are enabled. Always returns True since exclusions are mandatory."""
    return True  # Exclusions are now always enabled

def get_exclusion_patterns():
    """Get all exclusion patterns combined into a single list."""
    # Always get exclusions since they're mandatory now
    exclusions = load_exclusions()
    patterns = []
    
    # Add file extensions
    patterns.extend(exclusions.get("file_extensions", []))
    
    # Add directories
    patterns.extend(exclusions.get("directories", []))
    
    # Add additional exclusions
    patterns.extend(exclusions.get("additional_exclusions", []))
    
    return patterns

class ScanConfigUI:
    """UI for configuring scan options."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Genie - Scan Configuration")
        self.root.geometry("800x800")
        self.root.resizable(True, True)
        
        # Center the window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - 800/2)
        center_y = int(screen_height/2 - 600/2)
        self.root.geometry(f'+{center_x}+{center_y}')
        
        # Create frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add header
        header_label = ttk.Label(
            self.main_frame,
            text="Genie Scan Configuration",
            font=('Helvetica', 16, 'bold')
        )
        header_label.pack(pady=(0, 20))
        
        # Add description
        description = ttk.Label(
            self.main_frame,
            text="Configure how Genie scans your repositories for secrets.\nSettings will apply to all Git operations.",
            justify=tk.CENTER,
            wraplength=400
        )
        description.pack(pady=(0, 20))
        
        # Load current configuration
        self.config = load_config()
        self.scan_mode = tk.StringVar(value=self.config.get("scan_mode", "both"))
        
        # Create notebook with tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.scan_tab = ttk.Frame(self.notebook, padding=10)
        # Exclusions tab commented out as requested
        # self.exclusions_tab = ttk.Frame(self.notebook, padding=10)
        
        self.notebook.add(self.scan_tab, text="Scan Settings")
        # Exclusions tab not added to the notebook as requested
        # self.notebook.add(self.exclusions_tab, text="Exclusions")
        
        # Populate scan tab
        self.setup_scan_tab()
        
        # Exclusions tab setup commented out as requested
        # self.setup_exclusions_tab()
        
        # Button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Save and Exit button
        save_exit_button = ttk.Button(
            button_frame,
            text="Save and Exit",
            command=self.save_and_exit
        )
        save_exit_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.root.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            self.main_frame,
            text="",
            foreground="blue"
        )
        self.status_label.pack(pady=(10, 0))
    
    def setup_scan_tab(self):
        """Set up the scan settings tab."""
        # Scan mode frame
        scan_mode_frame = ttk.LabelFrame(self.scan_tab, text="Scan Mode", padding=10)
        scan_mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Scan mode options
        ttk.Radiobutton(
            scan_mode_frame,
            text="Scan changes only (recommended)\nOnly scan files that have been modified since last push.",
            variable=self.scan_mode,
            value="diff",
            padding=5
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Radiobutton(
            scan_mode_frame,
            text="Scan entire repository\nPerform a comprehensive scan of all files in the repository.",
            variable=self.scan_mode,
            value="repo",
            padding=5
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Radiobutton(
            scan_mode_frame,
            text="Scan both\nScan both changed files and the entire repository.",
            variable=self.scan_mode,
            value="both",
            padding=5
        ).pack(anchor=tk.W, pady=5)
        
        # Changed lines only option - COMMENTED OUT per request
        # changed_lines_frame = ttk.LabelFrame(self.scan_tab, text="Scanning Depth", padding=10)
        # changed_lines_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Add variable for changed lines only option - Still need this for functionality
        self.changed_lines_only = tk.BooleanVar(value=self.config.get("scan_changed_lines_only", True))
        
        # ttk.Checkbutton(
        #     changed_lines_frame,
        #     text="Scan only changed lines (recommended)\nOnly scan the specific lines that have been modified, rather than entire files.",
        #     variable=self.changed_lines_only,
        #     padding=5
        # ).pack(anchor=tk.W, pady=5)
        
        # Add explanatory text
        # ttk.Label(
        #     changed_lines_frame,
        #     text="Scanning only changed lines improves performance and reduces false positives.",
        #     wraplength=400,
        #     font=('Helvetica', 9, 'italic')
        # ).pack(anchor=tk.W, pady=5)
        
        # Exclusions notification frame - COMMENTED OUT per request
        # exclusions_frame = ttk.LabelFrame(self.scan_tab, text="Exclusions", padding=10)
        # exclusions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Notify that exclusions are always enabled
        # ttk.Label(
        #     exclusions_frame,
        #     text="Exclusions are always enabled to prevent scanning of certain files and directories.",
        #     wraplength=400
        # ).pack(anchor=tk.W, pady=5)
        
        # View/Edit exclusions button
        # ttk.Button(
        #     exclusions_frame,
        #     text="View Exclusions",
        #     command=self.open_exclusions
        # ).pack(anchor=tk.W, pady=5)
        
        # Current configuration summary - COMMENTED OUT per request
        # config_frame = ttk.LabelFrame(self.scan_tab, text="Current Configuration Summary", padding=10)
        # config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # self.config_description = ttk.Label(
        #     config_frame,
        #     text=self.get_config_description(),
        #     wraplength=500,
        #     justify=tk.LEFT
        # )
        # self.config_description.pack(anchor=tk.W, pady=5)
        
        # Removed duplicate button frame as per request
        # Button frame
        # button_frame = ttk.Frame(self.scan_tab)
        # button_frame.pack(fill=tk.X, padx=10, pady=20)
        
        # Save button
        # save_button = ttk.Button(
        #     button_frame,
        #     text="Save Configuration",
        #     command=self.save_and_exit
        # )
        # save_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        # cancel_button = ttk.Button(
        #     button_frame,
        #     text="Cancel",
        #     command=self.root.destroy
        # )
        # cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Add notebook to select scan tab by default
        self.notebook.select(self.scan_tab)
    
    def save_and_exit(self):
        """Save configuration and exit."""
        # Update config with current UI values
        self.config["scan_mode"] = self.scan_mode.get()
        self.config["scan_changed_lines_only"] = self.changed_lines_only.get()
        
        # Save configuration
        if save_config(self.config):
            messagebox.showinfo(
                "Configuration Saved",
                "Your scan configuration has been saved successfully."
            )
            self.root.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to save configuration. Please try again."
            )
    
    def get_config_description(self):
        """Get a human-readable description of the current configuration."""
        mode = self.scan_mode.get()
        changed_lines_only = self.changed_lines_only.get()
        
        if mode == "diff":
            mode_desc = "Scanning changes only"
        elif mode == "repo":
            mode_desc = "Scanning entire repository"
        else:
            mode_desc = "Scanning both changes and entire repository"
        
        lines_desc = "Scanning only changed lines" if changed_lines_only else "Scanning entire files"
        
        return f"{mode_desc}\n{lines_desc}\nExclusions: Always enabled"

    def open_exclusions(self):
        """Open the exclusions file in the default editor."""
        exclusions_path = get_exclusions_path()
        
        # Ensure the file exists before trying to edit it
        ensure_exclusions_file_exists()
        
        # Try to open with the default application
        if os.path.exists(exclusions_path):
            try:
                if sys.platform == 'win32':
                    os.startfile(exclusions_path)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.call(('open', exclusions_path))
                else:  # Linux and other Unix-like
                    subprocess.call(('xdg-open', exclusions_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open the exclusions file: {e}")
                
    def run(self):
        """Run the UI."""
        self.root.mainloop()


def main():
    """Main function for running the configuration UI."""
    # If arguments are passed, process them
    if len(sys.argv) > 1:
        if sys.argv[1] == "--edit-exclusions":
            # Just open the exclusions file for editing
            # Since we're hiding the exclusions tab, we'll still allow direct editing
            # of the exclusions file through this command line option
            exclusions_path = get_exclusions_path()
            ensure_exclusions_file_exists()
            
            try:
                if sys.platform == 'win32':
                    os.startfile(exclusions_path)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.call(('open', exclusions_path))
                else:  # Linux and other Unix-like
                    subprocess.call(('xdg-open', exclusions_path))
            except Exception as e:
                print(f"Error opening exclusions file: {e}")
            return
    
    # Otherwise, show the UI
    config_ui = ScanConfigUI()
    config_ui.run()


if __name__ == "__main__":
    main() 