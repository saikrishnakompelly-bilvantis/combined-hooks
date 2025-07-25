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
import time
import webbrowser
import platform
 
# Change logging level to only show progress information, not info or error logs
logging.basicConfig(
    level=logging.WARNING,  # Changed from INFO to WARNING to hide info logs
    format='%(asctime)s - %(message)s'  # Simplified format to remove the log level
)
 
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))
 
from secretscan import SecretScanner
from utils import mask_secret
from secretscan import generate_html_report
try:
    from scan_config import should_scan_diff, should_scan_repo, should_scan_changed_lines_only
except ImportError:
    # If scan_config is not available, default to scanning both
    def should_scan_diff():
        return True
    def should_scan_repo():
        return True
    def should_scan_changed_lines_only():
        return True

# Helper function for subprocess calls to prevent terminal windows
def run_subprocess(cmd, **kwargs):
    """Run a subprocess command with appropriate flags to hide console window on Windows."""
    if platform.system().lower() == 'windows':
        # Add CREATE_NO_WINDOW flag on Windows to prevent console window from appearing
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    
    return subprocess.run(cmd, **kwargs)
 
def get_script_dir():
    return SCRIPT_DIR
 
def check_python():
    if sys.version_info[0] < 3:
        print("WARNING: Python3 is not installed. Push review functionality will not work.")
        sys.exit(1)
 
def check_git():
    try:
        run_subprocess(['git', '--version'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        show_message_box("Error: Git is not installed. Please install Git before proceeding.")
        sys.exit(1)
 
    try:
        username = run_subprocess(['git', 'config', '--global', 'user.name'],
                                check=True, capture_output=True, text=True).stdout.strip()
        email = run_subprocess(['git', 'config', '--global', 'user.email'],
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
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Genie GitHooks", message)
    root.destroy()
 
def get_user_confirmation(prompt):
    root = tk.Tk()
    root.withdraw()
    response = messagebox.askyesno("Genie GitHooks", prompt)
    root.destroy()
    return "Y" if response else "N"
 
def get_last_pushed_commit():
    last_pushed_file = SCRIPT_DIR / ".last_pushed_commit"
    
    if not last_pushed_file.exists():
        return None
        
    try:
        with open(last_pushed_file, 'r') as f:
            commit_hash = f.read().strip()
            if commit_hash:
                return commit_hash
    except Exception as e:
        # Keep this warning as it's helpful for debugging
        logging.warning(f"Error reading last pushed commit: {e}")
    
    return None
    
def save_current_commit_as_pushed():
    try:
        head_cmd = ['git', 'rev-parse', 'HEAD']
        head_result = run_subprocess(
            head_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        head_commit = head_result.stdout.strip()
        
        if not head_commit:
            return False
            
        last_pushed_file = SCRIPT_DIR / ".last_pushed_commit"
        with open(last_pushed_file, 'w') as f:
            f.write(head_commit)
            
        return True
    except Exception as e:
        logging.error(f"Error saving current commit as pushed: {e}")
        return False
 
def get_pushed_files():
    try:
        last_pushed = get_last_pushed_commit()
        
        if last_pushed:
            try:
                diff_cmd = ['git', 'diff', '--name-only', f'{last_pushed}', 'HEAD']
                
                result = run_subprocess(
                    diff_cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )
                files = [f for f in result.stdout.strip().split('\n') if f]
                
                if files:
                    return files
            except subprocess.CalledProcessError:
                # Removed log statement
                pass
        
        rev_list_cmd = ['git', 'rev-list', '--count', '@{u}..HEAD']
        try:
            rev_count_output = run_subprocess(
                rev_list_cmd, 
                check=True, 
                capture_output=True, 
                text=True
            ).stdout.strip()
            
            rev_count = int(rev_count_output) if rev_count_output.isdigit() else 0
            
            if rev_count == 0:
                return []
        except subprocess.CalledProcessError:
            pass
        
        try:
            diff_cmd = ['git', 'diff', '--name-only', '@{u}..HEAD']
            result = run_subprocess(
                diff_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            files = [f for f in result.stdout.strip().split('\n') if f]
            
            if files:
                return files
        except subprocess.CalledProcessError:
            pass
        
        try:
            branch_result = run_subprocess(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            current_branch = branch_result.stdout.strip()
            
            remote_branch_exists = False
            try:
                check_remote = run_subprocess(
                    ['git', 'ls-remote', '--heads', 'origin', current_branch],
                    check=True,
                    capture_output=True,
                    text=True
                )
                remote_branch_exists = bool(check_remote.stdout.strip())
            except subprocess.CalledProcessError:
                remote_branch_exists = False
            
            if not remote_branch_exists:
                commit_count_cmd = ['git', 'rev-list', '--count', 'HEAD']
                commit_count_result = run_subprocess(
                    commit_count_cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )
                commit_count = int(commit_count_result.stdout.strip() or '0')
                
                if commit_count == 0:
                    return []
                
                all_files_cmd = ['git', 'ls-files']
                all_files_result = run_subprocess(
                    all_files_cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )
                return [f for f in all_files_result.stdout.strip().split('\n') if f]
        except Exception as e:
            # Removed error log
            pass
        
        # Last resort, get files in latest commit
        try:
            result = run_subprocess(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            files = [f for f in result.stdout.strip().split('\n') if f]
            return files
        except subprocess.CalledProcessError:
            pass
        
        # If all else fails, get all tracked files
        try:
            count_result = run_subprocess(
                ['git', 'ls-files', '--exclude-standard'],
                check=True,
                capture_output=True,
                text=True
            )
            return [f for f in count_result.stdout.strip().split('\n') if f]
        except Exception as e:
            # Removed error log
            return []
    except Exception as e:
        # Removed error log
        return []
 
def run_secret_scan_on_pushed_files():
    try:
        scanner = SecretScanner()
        pushed_files = get_pushed_files()
        
        if not pushed_files:
            return []
        
        # Check if we should scan only changed lines or entire files
        if should_scan_changed_lines_only():
            # Use the new scan_changed_lines method to only scan changed lines
            print("-  Scanning only changed lines in files...")
            results = scanner.scan_changed_lines(pushed_files)
        else:
            # Scan entire files
            print("-  Scanning entire files...")
            results = scanner.scan_files(pushed_files)
            
        # Replace info log with print to show only progress information
        if results:
            print(f"Scanning: Found {len(results)} potential secrets in {len(pushed_files)} files")
            
        return results
    except Exception as e:
        # Removed error log
        return []

def open_html_report(file_path):
    try:
        if not os.path.isfile(file_path):
            # Removed error log
            return False
            
        abs_path = os.path.abspath(file_path)
        file_uri = f"file://{abs_path}"
        
        time.sleep(0.5)
        success = webbrowser.open(file_uri)
        
        if not success:
            # Removed error log
            pass
            
        return success
    except Exception as e:
        # Removed error log
        return False
 
def create_window(title, width=800, height=600):
    window = tk.Tk()
    window.title(title)
    
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    center_x = int(screen_width/2 - width/2)
    center_y = int(screen_height/2 - height/2)
    
    window.geometry(f'{width}x{height}+{center_x}+{center_y}')
    window.resizable(True, True)
    window.minsize(400, 300)
    
    return window
 
class ValidationWindow:
    def __init__(self):
        self.results = {
            "secrets": {"proceed": False, "messages": {}, "global_message": ""}
        }
        self.windows = []
        self.ITEMS_PER_PAGE = 50
        self.current_page = 1
        self.justification_entries = []
        
    def create_items_list(self, parent: ttk.Frame, items: List[Dict[str, Any]], item_type: str) -> None:
        container_frame = ttk.Frame(parent)
        container_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        canvas = tk.Canvas(container_frame, height=350)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        parent.update_idletasks()
        canvas_width = parent.winfo_width() - 40
        if canvas_width <= 0:
            canvas_width = 700
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        count_label = ttk.Label(
            scrollable_frame,
            text=f"Total {item_type}s found: {len(items)}",
            font=('Helvetica', 12, 'bold')
        )
        count_label.pack(pady=5, padx=10, anchor="w")
        
        for i, item in enumerate(items, 1):
            item_frame = ttk.Frame(scrollable_frame)
            item_frame.pack(fill="x", padx=10, pady=5, anchor="w")
            
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
            
            if 'line' in item:
                content_frame = ttk.Frame(item_frame)
                content_frame.pack(fill="x", pady=2, anchor="w")
                
                content_label = ttk.Label(
                    content_frame,
                    text="Content:",
                    font=('Helvetica', 9, 'bold')
                )
                content_label.pack(side="left", anchor="nw")
                
                content_text = tk.Text(
                    content_frame, 
                    wrap=tk.WORD,
                    height=2,
                    width=canvas_width-100,
                    font=('Courier', 10),
                    relief=tk.FLAT,
                    padx=5,
                    pady=5
                )
                content_text.insert(tk.END, mask_secret(item['line']))
                content_text.config(state=tk.DISABLED)
                content_text.pack(side="left", fill="x", expand=True, padx=5)
            
            if i < len(items):
                ttk.Separator(scrollable_frame, orient="horizontal").pack(
                    fill="x", padx=10, pady=5
                )
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def show_questions_dialog(self, parent_window, items):
        dialog = tk.Toplevel(parent_window)
        dialog.title("Required Questions")
        dialog.transient(parent_window)
        dialog.grab_set()
        
        width = 600
        height = 400
        x = parent_window.winfo_x() + (parent_window.winfo_width() - width) // 2
        y = parent_window.winfo_y() + (parent_window.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            main_frame,
            text="If you believe the flagged contents are false positives, please mark it as Secret-Scanning-Report-update. "
                 "To do so, you please answer below questions that will be added as documentation:",
            wraplength=550,
            justify=tk.LEFT,
            font=('Helvetica', 10)
        ).pack(pady=(0, 20))
        
        ttk.Label(
            main_frame,
            text="1. Justification for the deviation from HSBC's policy:",
            wraplength=550,
            font=('Helvetica', 10, 'bold')
        ).pack(anchor="w", pady=(0, 5))
        
        justification_entry = ttk.Entry(main_frame)
        justification_entry.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            main_frame,
            text="2. Confirmation that all the findings are validated and confirmed to be not adding the credentials/secrets in code:",
            wraplength=550,
            font=('Helvetica', 10, 'bold')
        ).pack(anchor="w", pady=(0, 5))
        
        confirmation_entry = ttk.Entry(main_frame)
        confirmation_entry.pack(fill=tk.X, pady=(0, 15))
        
        result = {"proceed": False, "justification": "", "confirmation": ""}
        
        def validate_and_proceed():
            justification = justification_entry.get().strip()
            confirmation = confirmation_entry.get().strip()
            
            if len(justification) < 10 and len(confirmation) < 10:
                messagebox.showerror(
                    "Validation Error",
                    "Please provide a valid justification and confirmation."
                )
                return
            
            result["proceed"] = True
            result["justification"] = justification
            result["confirmation"] = confirmation
            dialog.quit()
        
        def on_cancel():
            result["proceed"] = False
            dialog.quit()
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
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
        if not items:
            return True
            
        self.current_page = 1
        
        root = create_window(title, width=900, height=700)
        self.windows.append(root)
        
        main_container = ttk.Frame(root, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)
        
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
                     "Once you click on Proceed, you will be required to answer a few questions before continuing with the push. "
                     "Please provide your responses in place of the following details. "
                     "These responses will be recorded in the MOD2 Catalyst dashboard.\n\n"
                     "Click \"Proceed\" to continue.")
        policy_label = ttk.Label(
            warning_frame,
            text=policy_text,
            wraplength=800,
            justify=tk.CENTER
        )
        policy_label.pack(pady=(0, 10))
        
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.create_items_list(content_frame, items, item_type)
        
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        button_container = ttk.Frame(button_frame)
        button_container.pack(anchor=tk.CENTER)
        
        def on_proceed():
            result = self.show_questions_dialog(root, items)
            if not result["proceed"]:
                return
            
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
        
        ttk.Button(
            button_container, 
            text="Abort Push", 
            command=on_abort,
            padding=(20, 10)
        ).pack(side=tk.LEFT, padx=20)
        
        ttk.Button(
            button_container, 
            text="Proceed", 
            command=on_proceed,
            padding=(20, 10)
        ).pack(side=tk.LEFT, padx=20)
        
        def on_window_close():
            on_abort()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_window_close)
        root.mainloop()
        
        if root in self.windows:
            self.windows.remove(root)
        root.destroy()
        
        return self.results["secrets"]["proceed"]
 
    def show_abort_window(self):
        root = create_window("Push Aborted - Genie GitHooks", width=400, height=200)
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        warning_label = ttk.Label(
            main_frame,
            text="⚠️ Push Aborted",
            font=('Helvetica', 16, 'bold')
        )
        warning_label.pack(pady=(0, 15))
        
        message_label = ttk.Label(
            main_frame,
            text="The push has been aborted due to unresolved issues.\nPlease review and address the concerns before pushing.",
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
    script_dir = get_script_dir()
    metadata_file = script_dir / ".push_metadata.json"
    
    try:
        metadata = {
            "validation_results": validation_results,
            "secrets_found": secrets_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
 
    except Exception as e:
        print(f"Warning: Failed to save metadata: {str(e)}", file=sys.stderr)

def record_push_information(validation_results):
    if not validation_results:
        return False
    
    messages = []
    result_data = validation_results.get("secrets", {})
    type_messages = result_data.get("messages", {})
    global_message = result_data.get("global_message", "")
    
    reviewed_items = [item for item, data in type_messages.items()
                    if data.get("classification") == "reviewed"]
    
    if reviewed_items and global_message:
        items_list = ", ".join(reviewed_items)
        messages.append(f"[SECRETS] {items_list}: {global_message}")
    
    if not messages:
        return False
    
    try:
        log_file = Path(get_script_dir()) / "push_validations.log"
        
        with open(log_file, 'a') as f:
            f.write(f"\n--- Push validation: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write("\n".join(messages) + "\n")
        
        return True
        
    except Exception as e:
        # Removed error log
        return False

def append_justification_to_commit(validation_results):
    """Append security justification messages to the latest commit message."""
    if not validation_results:
        return False
    
    # Extract the justification messages
    result_data = validation_results.get("secrets", {})
    global_message = result_data.get("global_message", "")
    
    if not global_message:
        return False
    
    try:
        # Get the current commit message
        get_message_cmd = ["git", "log", "-1", "--pretty=%B"]
        current_message = run_subprocess(
            get_message_cmd,
            check=True,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        # Prepare the new commit message with the justification
        justification_section = "\n\n[SECURITY JUSTIFICATION]\n" + global_message
        new_message = current_message + justification_section
        
        # Create a temporary file for the new commit message
        temp_file = SCRIPT_DIR / ".temp_commit_msg"
        with open(temp_file, 'w') as f:
            f.write(new_message)
        
        # Amend the commit with the new message
        amend_cmd = ["git", "commit", "--amend", "-F", str(temp_file)]
        run_subprocess(amend_cmd, check=True)
        
        # Delete the temporary file
        if temp_file.exists():
            temp_file.unlink()
        
        # Replace info log with progress print
        print("-  Added security justification to commit message")
        return True
        
    except Exception as e:
        # Removed error log
        return False

def generate_and_open_report(secrets_found):
    try:
        reports_dir = SCRIPT_DIR / ".push-reports"
        reports_dir.mkdir(exist_ok=True)
        
        scanner = SecretScanner()
        
        # Check scan configuration
        repo_secrets = []
        if should_scan_repo():
            # Replace info log with progress print
            print("-  Scanning entire repository...")
            repo_secrets = scanner.scan_repository()
        else:
            # Removed info log
            pass
        
        # Check if diff scan is enabled
        diff_secrets = []
        if should_scan_diff():
            # Replace info log with progress print
            print("-  Scanning changed files...")
            diff_secrets = secrets_found
        else:
            # Removed info log
            pass
        
        output_path = reports_dir / "scan-report.html"
        
        # Generate the report, passing repo_secrets directly
        success = generate_html_report(
            str(output_path),
            diff_secrets=diff_secrets,
            repo_secrets=repo_secrets,  # This now contains ALL repo secrets
            has_secrets=bool(diff_secrets or repo_secrets)
        )
        
        if not success:
            # Removed error log
            return False
            
        # Now add our custom table styling to fix column widths
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # CSS to fix table layout and prevent expanding based on content
            fixed_table_css = """
            <style>
                table { 
                    width: 100% !important; 
                    table-layout: fixed !important;
                }
                th, td { 
                    word-wrap: break-word !important;
                    overflow-wrap: break-word !important;
                    max-width: 100% !important;
                }
                th:nth-child(1), td:nth-child(1) { width: 5% !important; }
                th:nth-child(2), td:nth-child(2) { width: 25% !important; }
                th:nth-child(3), td:nth-child(3) { width: 10% !important; }
                th:nth-child(4), td:nth-child(4) { 
                    width: 60% !important;
                    white-space: pre-wrap !important;
                }
            </style>
            """
            
            # Insert our custom CSS after the existing styles
            if "</style>" in html_content:
                html_content = html_content.replace("</style>", "}</style>\n" + fixed_table_css)
            else:
                # If no style tag found, add it after the title
                html_content = html_content.replace("</title>", "</title>\n" + fixed_table_css)
            
            # Write the modified content back
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        except Exception as e:
            # Removed warning log
            # Continue anyway since the basic report was generated
            pass
        
        if open_html_report(str(output_path)):
            # Replace info log with progress print
            print("-  Generated scan report and opened in browser")
        
        return True
    except Exception as e:
        # Removed error log
        return False
 
def main():
    try:
        check_python()
        check_git()
        
        try:
            status_cmd = ['git', 'status', '-sb']
            status_output = run_subprocess(
                status_cmd,
                check=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            if "up to date" in status_output.lower() and "ahead" not in status_output:
                sys.exit(0)
        except Exception as e:
            # Removed warning log
            pass
        
        pushed_files = get_pushed_files()
        if not pushed_files:
            sys.exit(0)
        
        # Replace info log with progress print
        print(f"-  Running pre-push hook for {len(pushed_files)} files")
        
        # Check scan configuration
        secrets_data = []
        if should_scan_diff():
            secrets_data = run_secret_scan_on_pushed_files()
        else:
            # Removed info log
            pass
        
        validation_results = {}
        
        if secrets_data:
            validation = ValidationWindow()
            if not validation.run_validation(secrets_data):
                # Replace info log with progress print
                print("-  Push aborted by user during validation")
                sys.exit(1)
            
            validation_results = validation.results
            save_metadata(validation.results, secrets_data)
            record_push_information(validation_results)
            
            # Append justification to commit message if there are secrets
            append_justification_to_commit(validation_results)
        else:
            save_metadata({}, [])
            # Replace info log with progress print
            print("-  No secrets found in pushed files")
        
        generate_and_open_report(secrets_data)
        
        save_current_commit_as_pushed()
            
    except Exception as e:
        # Removed error log, replace with simple print without detailed error
        print("An error occurred during the pre-push hook", file=sys.stderr)
        sys.exit(1)
 
if __name__ == "__main__":
    main()