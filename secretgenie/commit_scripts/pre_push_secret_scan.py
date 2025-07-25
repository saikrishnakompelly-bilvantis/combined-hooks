#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import logging
from typing import List, Dict, Any
 
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
 
# Add the hooks directory to Python path
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))
 
from commit_scripts.secretscan import SecretScanner
 
def get_script_dir():
    """Get the directory where this script is located."""
    return SCRIPT_DIR
 
def check_python():
    """Check if Python is available."""
    if sys.version_info[0] < 3:
        print("WARNING: Python3 is not installed. Commit review functionality will not work.")
        sys.exit(1)
 
def check_git():
    """Check if Git is installed and configured."""
    try:
        subprocess.run(['git', '--version'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        show_message_box("Error: Git is not installed. Please install Git before proceeding.")
        sys.exit(1)
 
    # Check Git configuration
    try:
        username = subprocess.run(['git', 'config', '--global', 'user.name'],
                                check=True, capture_output=True, text=True).stdout.strip()
        email = subprocess.run(['git', 'config', '--global', 'user.email'],
                             check=True, capture_output=True, text=True).stdout.strip()
        
        if not username or not email:
            show_message_box('Error: Git global username and/or email is not set.\n'
                           'Please configure them using:\n'
                           'git config --global user.name "Your Name"\n'
                           'git config --global user.email "you@example.com"')
            sys.exit(1)
    except subprocess.CalledProcessError:
        show_message_box("Error: Git configuration check failed.")
        sys.exit(1)
 
def show_message_box(message):
    """Display a message box using Tkinter."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Genie GitHooks", message)
    root.destroy()
 
def get_user_confirmation(prompt):
    """Get user confirmation via Tkinter."""
    root = tk.Tk()
    root.withdraw()
    response = messagebox.askyesno("Genie GitHooks", prompt)
    root.destroy()
    return "Y" if response else "N"
 
def get_staged_files():
    """Get list of staged files."""
    try:
        logging.info("Getting staged files...")
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            check=True,
            capture_output=True,
            text=True
        )
        files = [f for f in result.stdout.strip().split('\n') if f]
        logging.info(f"Found {len(files)} staged files")
        return files
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting staged files: {e}")
        return []
 
def run_secret_scan():
    """Run the secret scanning script."""
    try:
        logging.info("Initializing secret scanner...")
        scanner = SecretScanner()
        
        logging.info("Scanning staged changes...")
        results = scanner.scan_staged_changes()
        
        logging.info(f"Found {len(results)} potential secrets")
        return results
    except Exception as e:
        logging.error(f"Secret scan failed: {str(e)}")
        return []
 
def create_window(title, width=800, height=600):
    """Create a centered window."""
    window = tk.Tk()
    window.title(title)
    
    # Get screen dimensions
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Calculate center position
    center_x = int(screen_width/2 - width/2)
    center_y = int(screen_height/2 - height/2)
    
    # Set window geometry
    window.geometry(f'{width}x{height}+{center_x}+{center_y}')
    
    # Make window resizable
    window.resizable(True, True)
    
    # Set minimum size
    window.minsize(400, 300)
    
    return window
 
class ValidationWindow:
    def __init__(self):
        self.results = {
            "secrets": {"proceed": False, "messages": {}, "global_message": ""}
        }
        self.windows = []
        self.ITEMS_PER_PAGE = 50  # Number of items to show per page
        self.current_page = 1
        self.justification_entries = []
        
    def create_items_list(self, parent: ttk.Frame, items: List[Dict[str, Any]], item_type: str) -> None:
        """Create a scrollable list of items with their details."""
        # Create a container frame for the scrollable area
        container_frame = ttk.Frame(parent)
        container_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        # Create canvas and scrollbar - use system default colors
        canvas = tk.Canvas(container_frame, height=350)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        
        # Use tk.Frame with system default background
        scrollable_frame = tk.Frame(canvas)
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create the window in the canvas with proper width
        # Use the parent's width minus padding for the scrollable frame
        parent.update_idletasks()  # Force geometry update
        canvas_width = parent.winfo_width() - 40  # Account for padding
        if canvas_width <= 0:  # Fallback if parent width not available yet
            canvas_width = 700
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add total count label
        count_label = ttk.Label(
            scrollable_frame,
            text=f"Total {item_type}s found: {len(items)}",
            font=('Helvetica', 12, 'bold')
        )
        count_label.pack(pady=5, padx=10, anchor="w")
        
        # Create a frame for each item
        for i, item in enumerate(items, 1):
            item_frame = ttk.Frame(scrollable_frame)
            item_frame.pack(fill="x", padx=10, pady=5, anchor="w")
            
            # File path and line number
            file_info = ttk.Label(
                item_frame,
                text=f"File: {item['file_path']}",
                font=('Helvetica', 10, 'bold')
            )
            file_info.pack(anchor="w", fill="x")
            
            if 'line_number' in item:
                line_info = ttk.Label(
                    item_frame,
                    text=f"Line {item['line_number']}",
                    font=('Helvetica', 9)
                )
                line_info.pack(anchor="w", fill="x")
            
            # Content preview
            if 'line' in item:
                content_frame = ttk.Frame(item_frame)
                content_frame.pack(fill="x", pady=2, anchor="w")
                
                content_label = ttk.Label(
                    content_frame,
                    text="Content:",
                    font=('Helvetica', 9, 'bold')
                )
                content_label.pack(side="left", anchor="nw")
                
                # Use Text widget instead of Label for better wrapping and display
                # Use a very light gray that works in both light and dark modes
                content_text = tk.Text(
                    content_frame, 
                    wrap=tk.WORD,
                    height=2,  # Show 2 lines by default
                    width=canvas_width-100,  # Allow most of the width
                    font=('Courier', 10),
                    relief=tk.FLAT,
                    padx=5,
                    pady=5
                )
                content_text.insert(tk.END, item['line'])
                content_text.config(state=tk.DISABLED)  # Make read-only
                content_text.pack(side="left", fill="x", expand=True, padx=5)
            
            # Add separator
            if i < len(items):
                ttk.Separator(scrollable_frame, orient="horizontal").pack(
                    fill="x", padx=10, pady=5
                )
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def show_questions_dialog(self, parent_window, items):
        """Show dialog for answering required questions."""
        dialog = tk.Toplevel(parent_window)
        dialog.title("Required Questions")
        dialog.transient(parent_window)
        dialog.grab_set()
        
        # Calculate size and position
        width = 600
        height = 400
        x = parent_window.winfo_x() + (parent_window.winfo_width() - width) // 2
        y = parent_window.winfo_y() + (parent_window.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(
            main_frame,
            text="If you believe the flagged contents are false positives, please mark it as Secret-Scanning-Report-update. "
                 "To do so, you please answer below questions that will be added to your commit message:",
            wraplength=550,
            justify=tk.LEFT,
            font=('Helvetica', 10)
        ).pack(pady=(0, 20))
        
        # Question 1
        ttk.Label(
            main_frame,
            text="1. Justification for the deviation from HSBC's policy:",
            wraplength=550,
            font=('Helvetica', 10, 'bold')
        ).pack(anchor="w", pady=(0, 5))
        
        justification_entry = ttk.Entry(main_frame)
        justification_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Question 2
        ttk.Label(
            main_frame,
            text="2. Confirmation that all the findings are validated and confirmed to be not adding the credentials/secrets in code:",
            wraplength=550,
            font=('Helvetica', 10, 'bold')
        ).pack(anchor="w", pady=(0, 5))
        
        confirmation_entry = ttk.Entry(main_frame)
        confirmation_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Result variable to store the answers
        result = {"proceed": False, "justification": "", "confirmation": ""}
        
        def validate_and_proceed():
            justification = justification_entry.get().strip()
            confirmation = confirmation_entry.get().strip()
            
            # Check minimum word count (10 words)
            if len(justification.split()) < 10 or len(confirmation.split()) < 10:
                messagebox.showerror(
                    "Validation Error",
                    "Each answer must contain at least 10 words."
                )
                return
            
            result["proceed"] = True
            result["justification"] = justification
            result["confirmation"] = confirmation
            dialog.quit()
        
        def on_cancel():
            result["proceed"] = False
            dialog.quit()
        
        # Buttons frame at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # Center-align buttons using a nested frame
        center_frame = ttk.Frame(button_frame)
        center_frame.pack(anchor=tk.CENTER)
        
        ttk.Button(
            center_frame, 
            text="Cancel", 
            command=on_cancel,
            padding=(10, 5)
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            center_frame, 
            text="Submit", 
            command=validate_and_proceed,
            padding=(10, 5)
        ).pack(side=tk.LEFT, padx=10)
        
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.mainloop()
        
        dialog.destroy()
        return result

    def show_validation_window(self, title, items, item_type):
        """Show validation window for either secrets or disallowed files."""
        if not items:
            return True
            
        # Reset pagination for new window
        self.current_page = 1
        
        root = create_window(title, width=900, height=700)  # Larger default window
        self.windows.append(root)
        
        # Create main container with padding
        main_container = ttk.Frame(root, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with warning at the top
        warning_frame = ttk.Frame(main_container)
        warning_frame.pack(fill=tk.X, pady=(0, 20))
        
        warning_label = ttk.Label(
            warning_frame,
            text="⚠️ WARNING ⚠️",
            font=('Helvetica', 14, 'bold')
        )
        warning_label.pack(pady=(0, 10))
        
        policy_text = ("You are about to violate HSBC's policy of not adding credential in the code. "
                       "\n"
                     "Should you decide to proceed, please proceed by clicking on \"Proceed\" button below. "
                     "Once you click on Proceed, you will be required to answer a few questions before continuing with the commit. "
                     "Please provide your responses in place of the following details in your commit comments. "
                     "These responses will be recorded in the MOD2 Catalyst dashboard.\n\n"
                     "Click \"Proceed\" to continue.")
        policy_label = ttk.Label(
            warning_frame,
            text=policy_text,
            wraplength=800,
            justify=tk.CENTER
        )
        policy_label.pack(pady=(0, 10))
        
        # Create content frame for the scrollable area - make it take more space
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create items list in the content frame
        self.create_items_list(content_frame, items, item_type)
        
        # Create button frame at the bottom
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Center-align buttons
        button_container = ttk.Frame(button_frame)
        button_container.pack(anchor=tk.CENTER)
        
        def on_proceed():
            # Show questions dialog
            result = self.show_questions_dialog(root, items)
            if not result["proceed"]:
                return
            
            # Store results with answers
            self.results["secrets"] = {
                "proceed": True,
                "messages": {
                    item['file_path']: {"classification": "reviewed"}
                    for item in items
                },
                "global_message": f"Justification: {result['justification']}\nConfirmation: {result['confirmation']}"
            }
            
            root.quit()
        
        def on_abort():
            self.results["secrets"] = {"proceed": False, "messages": {}, "global_message": ""}
            root.quit()
        
        # Create larger buttons
        ttk.Button(
            button_container, 
            text="Abort Commit", 
            command=on_abort,
            padding=(20, 10)  # Wider buttons
        ).pack(side=tk.LEFT, padx=20)
        
        ttk.Button(
            button_container, 
            text="Proceed", 
            command=on_proceed,
            padding=(20, 10)  # Wider buttons
        ).pack(side=tk.LEFT, padx=20)
        
        # Handle window close button (X)
        def on_window_close():
            on_abort()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_window_close)
        root.mainloop()
        
        # Clean up the window
        if root in self.windows:
            self.windows.remove(root)
        root.destroy()
        
        return self.results["secrets"]["proceed"]
 
    def show_abort_window(self):
        """Show the abort window."""
        root = create_window("Commit Aborted - Genie GitHooks", width=400, height=200)
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        warning_label = ttk.Label(
            main_frame,
            text="⚠️ Commit Aborted",
            font=('Helvetica', 16, 'bold')
        )
        warning_label.pack(pady=(0, 15))
        
        message_label = ttk.Label(
            main_frame,
            text="The commit has been aborted due to unresolved issues.\nPlease review and address the concerns before committing.",
            justify=tk.CENTER,
            wraplength=350
        )
        message_label.pack(pady=(0, 20))
        
        ok_button = ttk.Button(
            main_frame, 
            text="OK", 
            command=root.destroy,
            padding=(10, 5)
        )
        ok_button.pack()
        ok_button.pack_configure(anchor=tk.CENTER)
        
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.transient()
        root.grab_set()
        root.wait_window()
 
    def run_validation(self, secrets_data):
        """Run the validation process for secrets."""
        # Reset results at the start of validation
        self.results = {
            "secrets": {"proceed": False, "messages": {}, "global_message": ""}
        }
 
        if secrets_data:
            proceed = self.show_validation_window(
                "Secrets Found - Genie GitHooks",
                secrets_data,
                "secret"
            )
            if not proceed:
                self.show_abort_window()
                return False
 
        return True
 
def save_metadata(validation_results, secrets_data):
    """Save commit metadata for post-commit hook."""
    script_dir = get_script_dir()
    metadata_file = script_dir / ".commit_metadata.json"
    
    try:
        metadata = {
            "validation_results": validation_results,
            "secrets_found": secrets_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
 
    except Exception as e:
        print(f"Warning: Failed to save metadata: {str(e)}", file=sys.stderr)
 
def append_validation_messages():
    """Append validation messages to the commit message."""
    try:
        script_dir = get_script_dir()
        metadata_file = script_dir / ".commit_metadata.json"
        
        if not metadata_file.exists():
            return
            
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        validation_results = metadata.get("validation_results", {})
        
        # Collect messages for secrets
        messages = []
        result_data = validation_results.get("secrets", {})
        type_messages = result_data.get("messages", {})
        global_message = result_data.get("global_message", "")
        
        # If there are any true positives and a global message
        true_positives = [item for item, data in type_messages.items()
                        if data.get("classification") == "true_positive"]
        
        if true_positives and global_message:
            items_list = ", ".join(true_positives)
            messages.append(f"[SECRETS] {items_list}: {global_message}")
        
        if messages:
            # Read current commit message
            commit_msg_file = Path(sys.argv[1])
            with open(commit_msg_file, 'r') as f:
                current_msg = f.read()
            
            # Append validation messages
            with open(commit_msg_file, 'w') as f:
                f.write(current_msg.rstrip() + "\n\n" + "\n".join(messages))
                
    except Exception as e:
        print(f"Warning: Failed to append validation messages: {str(e)}", file=sys.stderr)
 
def main():
    try:
        logging.info("Starting pre-commit hook")
        check_python()
        check_git()
        
        staged_files = get_staged_files()
        if not staged_files:
            logging.info("No files staged for commit")
            show_message_box("No files staged for commit.")
            sys.exit(0)
        
        logging.info("Running secret scan...")
        secrets_data = run_secret_scan()
        
        if secrets_data:
            logging.info("Showing validation window...")
            validation = ValidationWindow()
            if not validation.run_validation(secrets_data):
                logging.info("Validation failed or was aborted")
                sys.exit(1)
            
            logging.info("Saving metadata...")
            save_metadata(validation.results, secrets_data)
            logging.info("Appending validation messages...")
            append_validation_messages()
        else:
            logging.info("No issues found, saving empty metadata")
            save_metadata({}, [])
        
        logging.info("Pre-commit hook completed successfully")
            
    except Exception as e:
        logging.error(f"Error in pre-commit hook: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
 
if __name__ == "__main__":
    main()