"""
Validation Dialog UI

This module provides a tkinter-based GUI for displaying validation failures
and allowing users to choose whether to proceed with push or cancel.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import List, Dict, Any, Optional, Tuple
import textwrap


class ValidationDialog:
    """GUI dialog for handling validation failures during push."""
    
    def __init__(self, validation_results: Dict[str, Any], repo_path: str = None):
        """
        Initialize the validation dialog.
        
        Args:
            validation_results: Dictionary containing validation results with errors, warnings, etc.
            repo_path: Path to the git repository root (for git info)
        """
        self.validation_results = validation_results
        self.result = None  # Will be 'proceed', 'cancel', or None
        self.justification = ""
        self.root = None
        self.repo_path = repo_path
    
    def show_dialog(self) -> Tuple[str, str]:
        """
        Display the validation dialog and return user's choice.
        
        Returns:
            Tuple of (result, justification) where result is 'proceed' or 'cancel'
        """
        self.root = tk.Tk()
        self.root.title("API Validation Results")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Center the window
        self.root.geometry("+%d+%d" % (
            (self.root.winfo_screenwidth() / 2 - 400),
            (self.root.winfo_screenheight() / 2 - 300)
        ))
        
        self._create_widgets()
        self.root.mainloop()
        
        return self.result or 'cancel', self.justification
    
    def _create_widgets(self):
        """Create and layout all UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🚨 API Validation Failures Detected", 
            font=("Arial", 20, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Summary
        summary_text = self._create_summary_text()
        summary_label = ttk.Label(main_frame, text=summary_text, font=("Arial", 12))
        summary_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Validation results frame
        results_frame = ttk.LabelFrame(main_frame, text="Validation Details", padding="5")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Scrolled text for validation results
        self.results_text = scrolledtext.ScrolledText(
            results_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=20,
            font=("Consolas", 11)
        )
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Populate results
        self._populate_results()
        
        # Action frame
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        action_frame.columnconfigure(1, weight=1)

        # Buttons
        cancel_btn = ttk.Button(
            action_frame, 
            text="📝 Cancel Push & Fix Issues", 
            command=self._cancel_push,
            width=25
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 10))

        proceed_btn = ttk.Button(
            action_frame, 
            text="⚠️ Proceed (Download Required)", 
            command=self._proceed_with_justification_and_download,
            width=32
        )
        proceed_btn.grid(row=0, column=1, padx=(10, 0))

        # Make cancel the default focus
        cancel_btn.focus()
        
        # Bind Enter key to cancel (safer default)
        self.root.bind('<Return>', lambda e: self._cancel_push())
        self.root.bind('<Escape>', lambda e: self._cancel_push())
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._cancel_push)
    
    def _create_summary_text(self) -> str:
        """Create summary text for the validation results."""
        errors = self.validation_results.get('errors', [])
        warnings = self.validation_results.get('warnings', [])
        meta_files = self.validation_results.get('meta_files', [])
        
        summary = f"Found {len(errors)} error(s) and {len(warnings)} warning(s) "
        summary += f"across {len(meta_files)} api.meta file(s).\n\n"
        summary += "You can either fix the issues and push later, or proceed with a justification."
        
        return summary
    
    def _populate_results(self):
        """Populate the results text widget with detailed validation information."""
        self.results_text.delete(1.0, tk.END)
        
        # Meta files section
        meta_files = self.validation_results.get('meta_files', [])
        if meta_files:
            self.results_text.insert(tk.END, "📄 VALIDATED META FILES:\n")
            self.results_text.insert(tk.END, "=" * 50 + "\n")
            for meta_file in meta_files:
                self.results_text.insert(tk.END, f"  • {meta_file}\n")
            self.results_text.insert(tk.END, "\n")
        
        # Errors section
        errors = self.validation_results.get('errors', [])
        if errors:
            self.results_text.insert(tk.END, "❌ VALIDATION ERRORS:\n")
            self.results_text.insert(tk.END, "=" * 50 + "\n")
            for i, error in enumerate(errors, 1):
                # Wrap long error messages
                wrapped_error = textwrap.fill(f"{i}. {error}", width=90, 
                                            subsequent_indent="   ")
                self.results_text.insert(tk.END, wrapped_error + "\n\n")
        
        # Warnings section
        warnings = self.validation_results.get('warnings', [])
        if warnings:
            self.results_text.insert(tk.END, "⚠️ VALIDATION WARNINGS:\n")
            self.results_text.insert(tk.END, "=" * 50 + "\n")
            for i, warning in enumerate(warnings, 1):
                wrapped_warning = textwrap.fill(f"{i}. {warning}", width=90,
                                              subsequent_indent="   ")
                self.results_text.insert(tk.END, wrapped_warning + "\n\n")
        
        # Removed compliance rules reference section
        
        # Make text read-only
        self.results_text.config(state=tk.DISABLED)
    
    def _cancel_push(self):
        """Handle cancel push action."""
        self.result = 'cancel'
        self.root.destroy()
    
    def _proceed_with_justification(self):
        """(Removed: now handled by _proceed_with_justification_and_download)"""
        pass

    def _proceed_with_justification_and_download(self):
        """Handle proceed: prompt for justification, then download report, then proceed."""
        justification_dialog = JustificationDialog(self.root)
        justification = justification_dialog.get_justification()
        if not justification:
            return  # Stay in dialog if no justification
        self.justification = justification
        self._download_report(force_justification=True)
        self.result = 'proceed'
        self.root.destroy()

    def _download_report(self, force_justification=False):
        """Open a file dialog to save the full validation report, always using correct repo and justification."""
        import tkinter.filedialog
        import subprocess
        from datetime import datetime
        # If called from the old download button, prompt for justification if not set
        if not self.justification and not force_justification:
            justification_dialog = JustificationDialog(self.root)
            justification = justification_dialog.get_justification()
            if not justification:
                tk.messagebox.showwarning("Justification Required", "Please provide a justification to save the report.")
                return
            self.justification = justification
        # Try to get git info from the correct repo
        git_cwd = self.repo_path or None
        try:
            commit_id = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=git_cwd).stdout.strip()
        except Exception:
            commit_id = "(unknown)"
        try:
            branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True, check=True, cwd=git_cwd).stdout.strip()
        except Exception:
            branch = "(unknown)"
        try:
            user_name = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True, check=True, cwd=git_cwd).stdout.strip()
            user_email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True, check=True, cwd=git_cwd).stdout.strip()
        except Exception:
            user_name = "(unknown)"
            user_email = "(unknown)"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Ask user for file location
        default_filename = f"apigenie_validation_{commit_id[:7]}_{timestamp}.txt"
        file_path = tkinter.filedialog.asksaveasfilename(
            title="Save Validation Report",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            return  # User cancelled
        # Compose report
        justification = self.justification or "(not provided)"
        errors = self.validation_results.get('errors', [])
        warnings = self.validation_results.get('warnings', [])
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
        tk.messagebox.showinfo("Report Saved", f"Validation report saved to:\n{file_path}")


class JustificationDialog:
    """Dialog for collecting justification message."""
    
    def __init__(self, parent):
        """Initialize justification dialog."""
        self.parent = parent
        self.justification = ""
        self.dialog = None
    
    def get_justification(self) -> str:
        """Show justification dialog and return the justification text."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Justification Required")
        self.dialog.geometry("600x400")
        self.dialog.resizable(True, True)
        
        # Center relative to parent
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            (self.parent.winfo_x() + 100),
            (self.parent.winfo_y() + 100)
        ))
        
        self._create_justification_widgets()
        self.dialog.wait_window()
        
        return self.justification
    
    def _create_justification_widgets(self):
        """Create widgets for justification dialog."""
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="⚠️ Justification Required", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Instruction
        instruction = (
            "Please provide a justification for proceeding with validation failures.\n"
            "This message will be added to your commit message for audit purposes."
        )
        instruction_label = ttk.Label(main_frame, text=instruction, wraplength=550, font=("Arial", 11))
        instruction_label.pack(pady=(0, 15))
        
        # Text area frame
        text_frame = ttk.LabelFrame(main_frame, text="Justification Message", padding="5")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Justification text area
        self.justification_text = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            width=70, 
            height=10,
            font=("Arial", 12)
        )
        self.justification_text.pack(fill=tk.BOTH, expand=True)
        self.justification_text.focus()
        
        # Placeholder text
        placeholder = (
            "Example: Emergency hotfix required for production issue. "
            "Will address validation failures in follow-up commit."
        )
        self.justification_text.insert(tk.END, placeholder)
        self.justification_text.tag_add("placeholder", "1.0", tk.END)
        self.justification_text.tag_config("placeholder", foreground="gray")
        
        # Bind events to handle placeholder
        self.justification_text.bind("<FocusIn>", self._on_focus_in)
        self.justification_text.bind("<KeyPress>", self._on_key_press)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Buttons
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self._cancel_justification
        )
        cancel_btn.pack(side=tk.LEFT)
        
        proceed_btn = ttk.Button(
            button_frame, 
            text="Proceed with Push", 
            command=self._accept_justification
        )
        proceed_btn.pack(side=tk.RIGHT)
        
        # Bind Enter to accept (Ctrl+Enter)
        self.dialog.bind('<Control-Return>', lambda e: self._accept_justification())
        self.dialog.bind('<Escape>', lambda e: self._cancel_justification())
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel_justification)
    
    def _on_focus_in(self, event):
        """Handle focus in event to clear placeholder."""
        if self.justification_text.tag_ranges("placeholder"):
            self.justification_text.delete("1.0", tk.END)
            self.justification_text.tag_remove("placeholder", "1.0", tk.END)
    
    def _on_key_press(self, event):
        """Handle key press to remove placeholder formatting."""
        if self.justification_text.tag_ranges("placeholder"):
            self.justification_text.tag_remove("placeholder", "1.0", tk.END)
    
    def _cancel_justification(self):
        """Cancel justification dialog."""
        self.justification = ""
        self.dialog.destroy()
    
    def _accept_justification(self):
        """Accept justification and close dialog."""
        text = self.justification_text.get("1.0", tk.END).strip()
        
        # Check if it's just the placeholder
        if self.justification_text.tag_ranges("placeholder") or not text:
            messagebox.showwarning(
                "Justification Required", 
                "Please provide a meaningful justification message."
            )
            return
        
        if len(text) < 10:
            messagebox.showwarning(
                "Justification Too Short", 
                "Please provide a more detailed justification (at least 10 characters)."
            )
            return
        
        self.justification = text
        self.dialog.destroy()


def show_validation_dialog(validation_results: Dict[str, Any], repo_path: str = None) -> Tuple[str, str]:
    """
    Show validation dialog and return user's choice.
    
    Args:
        validation_results: Dictionary containing validation results
        repo_path: Path to the git repository root (for git info)
        
    Returns:
        Tuple of (result, justification) where result is 'proceed' or 'cancel'
    """
    try:
        dialog = ValidationDialog(validation_results, repo_path=repo_path)
        return dialog.show_dialog()
    except Exception as e:
        # Fallback to console if GUI fails
        print(f"GUI Error: {e}")
        print("Falling back to console mode...")
        return _console_fallback(validation_results)


def _console_fallback(validation_results: Dict[str, Any]) -> Tuple[str, str]:
    """Fallback console interface if GUI fails."""
    print("\n" + "="*60)
    print("🚨 API VALIDATION FAILURES DETECTED")
    print("="*60)
    
    errors = validation_results.get('errors', [])
    warnings = validation_results.get('warnings', [])
    
    print(f"\nFound {len(errors)} error(s) and {len(warnings)} warning(s)")
    
    if errors:
        print("\n❌ ERRORS:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    print("\nOptions:")
    print("1. Cancel push and fix issues")
    print("2. Proceed with justification")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == "1":
            return 'cancel', ''
        elif choice == "2":
            justification = input("Enter justification: ").strip()
            if justification:
                return 'proceed', justification
            else:
                print("Justification cannot be empty.")
        else:
            print("Invalid choice. Please enter 1 or 2.") 