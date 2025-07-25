import sys
import os
import subprocess
import webbrowser
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, 
                            QFileDialog, QSplashScreen, QSizePolicy)
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon, QPixmap

# Immediately set the native UI environment variable for corporate builds
os.environ['APIGENIE_USE_NATIVE_UI'] = 'true'

# Global flags
use_native_ui = True
use_web_engine = False

from datetime import datetime
from urllib.parse import quote, urljoin
from urllib.request import pathname2url
import platform
import logging
import shutil
import time
import json

# Helper function for subprocess calls to prevent terminal windows
def run_subprocess(cmd, **kwargs):
    """Run a subprocess command with appropriate flags to hide console window on Windows."""
    if platform.system().lower() == 'windows':
        # Add CREATE_NO_WINDOW flag on Windows to prevent console window from appearing
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    
    return subprocess.run(cmd, **kwargs)

# Function to check if we're in a restricted environment
def is_restricted_environment():
    """Always return True for corporate builds to enforce native UI."""
    return True

class APIGenieApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_first_run = False
        self.check_first_run()
        self.setup_paths()
        
        # Check if we're in a restricted environment
        self.is_restricted_env = is_restricted_environment()
        
        # Check for required dependencies before proceeding
        if not self.check_dependencies():
            # Dependencies missing - the check_dependencies method will display appropriate errors
            sys.exit(1)
        
        # Create shortcut on first run
        if self.is_first_run:
            self.create_desktop_shortcut()
            
        self.initUI()

    def check_dependencies(self):
        """Check if all required dependencies are installed and configured."""
        # Check if Git is installed
        try:
            result = run_subprocess(['git', '--version'], capture_output=True, check=False, text=True)
            if result.returncode != 0:
                self.show_dependency_error("Git Not Found", "Git is not installed or not in your PATH. Please install Git and try again.")
                return False
                
            # Git is installed, check if username and email are configured
            username_result = run_subprocess(['git', 'config', '--global', 'user.name'], capture_output=True, check=False, text=True)
            email_result = run_subprocess(['git', 'config', '--global', 'user.email'], capture_output=True, check=False, text=True)
            
            if username_result.returncode != 0 or not username_result.stdout.strip():
                self.show_dependency_error("Git Configuration Missing", 
                                           "Git username is not configured. Please run:\n\n" +
                                           "git config --global user.name \"Your Name\"\n\n" +
                                           "Then restart the application.")
                return False
                
            if email_result.returncode != 0 or not email_result.stdout.strip():
                self.show_dependency_error("Git Configuration Missing", 
                                           "Git email is not configured. Please run:\n\n" +
                                           "git config --global user.email \"your.email@example.com\"\n\n" +
                                           "Then restart the application.")
                return False
                
        except FileNotFoundError:
            self.show_dependency_error("Git Not Found", "Git is not installed or not in your PATH. Please install Git and try again.")
            return False
            
        # Check Python version - this will always be available since we're running in Python
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
            self.show_dependency_error("Python Version Error", 
                                    f"Python 3.9 or higher is required. You're running {sys.version.split()[0]}.\n" +
                                    "Please upgrade Python and try again.")
            return False
            
        # All checks passed
        return True
        
    def show_dependency_error(self, title, message):
        """Show an error message for dependency issues."""
        QMessageBox.critical(self, title, message)
        print(f"ERROR: {title} - {message}")

    def setup_paths(self):
        # Get the application's root directory and set up paths
        if getattr(sys, 'frozen', False):
            # When frozen (built executable), resources are bundled in _MEIPASS
            self.assets_path = os.path.join(sys._MEIPASS, 'assets')
            self.hooks_source = os.path.join(sys._MEIPASS, 'hooks')
            self.validation_source = os.path.join(sys._MEIPASS, 'validation')
            self.app_path = sys._MEIPASS
        else:
            # When running from source
            self.app_path = os.path.dirname(os.path.abspath(__file__))
            
            # Set up asset paths
            self.assets_path = os.path.join(self.app_path, 'assets')
            
            # Set up hooks and validation paths
            self.hooks_source = os.path.join(self.app_path, 'hooks')
            self.validation_source = os.path.join(self.app_path, 'validation')
        
        # Set logo path
        self.logo_path = os.path.join(self.assets_path, 'logo.png')
        
        # Ensure the assets directory exists (only needed when running from source)
        if not getattr(sys, 'frozen', False):
            os.makedirs(self.assets_path, exist_ok=True)

    def initUI(self):
        self.setWindowTitle('APIGenie - API Validation Tool')
        
        # Load logo for window icon
        if os.path.exists(self.logo_path):
            icon = QIcon(self.logo_path)
            self.setWindowIcon(icon)
        
        # Set a smaller initial size and make window resizable
        self.setGeometry(200, 200, 600, 500)
        self.setMinimumSize(500, 400)
        
        # Allow window to resize automatically with content
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Always use native UI
        self.create_native_ui()

    def create_desktop_shortcut(self):
        """Create desktop shortcut based on the operating system."""
        try:
            # Get the path to the executable
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                if platform.system().lower() == 'darwin':
                    app_path = os.path.dirname(os.path.dirname(sys.executable))  # Get the .app bundle path
                else:
                    app_path = sys.executable
            else:
                # Running in development - don't create shortcut
                return

            desktop_path = Path.home() / "Desktop"
            os_type = platform.system().lower()
            
            if os_type == "windows":
                try:
                    import winshell
                    from win32com.client import Dispatch
                    
                    shortcut_path = desktop_path / "APIGenie.lnk"
                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(str(shortcut_path))
                    shortcut.Targetpath = app_path
                    shortcut.IconLocation = f"{app_path},0"
                    shortcut.save()
                except ImportError:
                    pass
                    
            elif os_type == "darwin":  # macOS
                try:
                    app_path = Path(app_path)
                    if app_path.suffix == '.app' or os.path.exists(str(app_path) + '.app'):
                        if not app_path.suffix == '.app':
                            app_path = Path(str(app_path) + '.app')
                        
                        alias_script = f'''
                        tell application "Finder"
                            make new alias file to POSIX file "{app_path}" at POSIX file "{desktop_path}"
                        end tell
                        '''
                        result = run_subprocess(['osascript', '-e', alias_script], capture_output=True, text=True)
                except Exception as e:
                    logging.error(f"Error creating macOS alias: {str(e)}")
                    
            elif os_type == "linux":
                try:
                    desktop_file = desktop_path / "APIGenie.desktop"
                    content = f"""[Desktop Entry]
Name=APIGenie
Exec="{app_path}"
Icon={app_path}
Type=Application
Categories=Utility;Development;
"""
                    desktop_file.write_text(content, encoding='utf-8')
                    os.chmod(desktop_file, 0o755)
                except Exception as e:
                    logging.error(f"Error creating Linux desktop entry: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Failed to create desktop shortcut: {str(e)}")

    def check_first_run(self):
        """Check if this is the first time the application is run using comprehensive detection."""
        apigenie_dir = os.path.expanduser('~/.apigenie')
        hooks_dir = os.path.join(apigenie_dir, 'hooks')
        config_file = os.path.join(apigenie_dir, 'config')
        
        # Start with assumption it's first run
        self.is_first_run = True
        
        # Check 1: Config file exists and contains installation status
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_content = f.read()
                    if 'installed=true' in config_content:
                        self.is_first_run = False
            except:
                pass
        
        # Check 2: Hooks directory exists and has files (backup detection)
        if self.is_first_run and os.path.exists(hooks_dir) and os.listdir(hooks_dir):
            try:
                # Check if essential hook files exist
                essential_hooks = ['pre-commit', 'pre-push']
                hooks_exist = all(os.path.exists(os.path.join(hooks_dir, hook)) for hook in essential_hooks)
                if hooks_exist:
                    self.is_first_run = False
            except:
                pass
        
        # Check 3: Git hooks path is set to our directory (backup detection)
        if self.is_first_run:
            try:
                hooks_path_result = run_subprocess(['git', 'config', '--global', '--get', 'core.hooksPath'],
                                                capture_output=True, text=True, check=False)
                if hooks_path_result.returncode == 0 and hooks_path_result.stdout.strip() == hooks_dir:
                    # Validation directory should also exist for complete installation
                    validation_dir = os.path.join(apigenie_dir, 'validation')
                    if os.path.exists(validation_dir):
                        self.is_first_run = False
            except:
                pass
        
        # Create config directory if it doesn't exist (for future installation)
        if not os.path.exists(apigenie_dir):
            try:
                os.makedirs(apigenie_dir, exist_ok=True)
            except:
                pass  # Fail silently if we can't create the directory

    def get_installation_status(self):
        """Get detailed installation status information."""
        apigenie_dir = os.path.expanduser('~/.apigenie')
        hooks_dir = os.path.join(apigenie_dir, 'hooks')
        validation_dir = os.path.join(apigenie_dir, 'validation')
        config_file = os.path.join(apigenie_dir, 'config')
        
        status = {
            'installed': False,
            'config_exists': False,
            'hooks_exist': False,
            'validation_exists': False,
            'git_configured': False,
            'details': []
        }
        
        # Check config file
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    if 'installed=true' in f.read():
                        status['config_exists'] = True
                        status['details'].append("✓ Config file exists")
                    else:
                        status['details'].append("⚠ Config file exists but no installation marker")
            except:
                status['details'].append("⚠ Config file exists but unreadable")
        else:
            status['details'].append("✗ Config file missing")
        
        # Check hooks directory
        if os.path.exists(hooks_dir):
            essential_hooks = ['pre-commit', 'pre-push']
            existing_hooks = [h for h in essential_hooks if os.path.exists(os.path.join(hooks_dir, h))]
            if len(existing_hooks) == len(essential_hooks):
                status['hooks_exist'] = True
                status['details'].append("✓ All hook files exist")
            elif existing_hooks:
                status['details'].append(f"⚠ Some hook files exist: {', '.join(existing_hooks)}")
            else:
                status['details'].append("⚠ Hooks directory exists but no hook files")
        else:
            status['details'].append("✗ Hooks directory missing")
        
        # Check validation directory
        if os.path.exists(validation_dir):
            status['validation_exists'] = True
            status['details'].append("✓ Validation system exists")
        else:
            status['details'].append("✗ Validation system missing")
        
        # Check git configuration
        try:
            hooks_path_result = run_subprocess(['git', 'config', '--global', '--get', 'core.hooksPath'],
                                            capture_output=True, text=True, check=False)
            if hooks_path_result.returncode == 0:
                configured_path = hooks_path_result.stdout.strip()
                if configured_path == hooks_dir:
                    status['git_configured'] = True
                    status['details'].append("✓ Git hooks path correctly configured")
            else:
                    status['details'].append(f"⚠ Git hooks path set to different location: {configured_path}")
        except:
            status['details'].append("✗ Unable to check Git configuration")
        
        # Determine overall installation status
        status['installed'] = (status['config_exists'] or status['hooks_exist']) and status['validation_exists']
        
        return status

    def get_hooks_path(self):
        """Get the correct hooks path whether running from source or frozen executable."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return Path(sys._MEIPASS) / 'hooks'
        else:
            # Running in development
            return Path(__file__).parent / 'hooks'

    def install_hooks(self):
        """Install Git hooks and necessary files."""
        try:
            # Recheck dependencies
            if not self.check_dependencies():
                return
                
            # Get the user's home directory
            home_dir = os.path.expanduser('~')
            apigenie_dir = os.path.join(home_dir, '.apigenie')
            hooks_dir = os.path.join(apigenie_dir, 'hooks')
            
            # Check if hooks are already installed
            config_file = os.path.join(apigenie_dir, 'config')
            is_already_installed = False
            
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        if 'installed=true' in content:
                            is_already_installed = True
                except:
                    pass
            
            # Also check if hooks directory exists and has files
            if not is_already_installed and os.path.exists(hooks_dir) and os.listdir(hooks_dir):
                is_already_installed = True
            
            # Also check if Git hooks path is set to our directory
            if not is_already_installed:
                hooks_path_result = run_subprocess(['git', 'config', '--global', '--get', 'core.hooksPath'],
                                                capture_output=True, text=True, check=False)
                if hooks_path_result.returncode == 0 and hooks_path_result.stdout.strip() == hooks_dir:
                    is_already_installed = True
            
            if is_already_installed:
                QMessageBox.information(self, "Already Installed", 
                                      "✓ APIGenie hooks are already installed!\n\n" +
                                          "To reinstall hooks, run the uninstall command first.")
                return
            
            # Create necessary directories
            os.makedirs(hooks_dir, exist_ok=True)
            validation_dir = os.path.join(apigenie_dir, 'validation')
            os.makedirs(validation_dir, exist_ok=True)
            
            # Get the correct source directories
            hooks_source = self.get_hooks_path()
            validation_source = Path(self.validation_source)
            
            if not hooks_source.exists():
                raise FileNotFoundError(f"Hooks source directory not found: {hooks_source}")
            
            if not validation_source.exists():
                raise FileNotFoundError(f"Validation source directory not found: {validation_source}")
            
            # Copy hook files
            for item in os.listdir(str(hooks_source)):
                source_file = hooks_source / item
                target_file = Path(hooks_dir) / item
                
                if source_file.is_dir():
                    shutil.copytree(str(source_file), str(target_file), dirs_exist_ok=True)
                else:
                    shutil.copy2(str(source_file), str(target_file))
                    # Make hook files executable
                    if item in ['pre-commit', 'pre-push', 'commit-msg']:
                        os.chmod(str(target_file), 0o755)
            
            # Copy validation directory
            shutil.copytree(str(validation_source), validation_dir, dirs_exist_ok=True)
            
            # Set up Git configuration
            try:
                # Remove any existing Git hooks configuration
                run_subprocess(['git', 'config', '--global', '--unset', 'core.hooksPath'], check=False)
                
                # Set up new Git hooks configuration
                run_subprocess(['git', 'config', '--global', 'core.hooksPath', hooks_dir], check=True)
                
                # Create a config file to store installation status
                config_file = os.path.join(apigenie_dir, 'config')
                with open(config_file, 'w') as f:
                    f.write(f'hooks_dir={hooks_dir}\n')
                    f.write('installed=true\n')
                
                # Handle successful installation
                self.is_first_run = False
                self.create_native_main_ui()
                
                # Update status display
                self.update_status_display()
                
                # Show success message
                QMessageBox.information(self, "Installation Successful", 
                                      "✓ APIGenie hooks have been successfully installed!\n\n" +
                                      "All your Git repositories will now validate API compliance automatically.")
                
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Error", f"Failed to configure Git hooks: {str(e)}")
                return
                
        except Exception as e:
            logging.error(f"Installation failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to install hooks: {str(e)}")
            return

    def uninstall_hooks(self):
        try:
            # Check if Git is installed before proceeding
            try:
                result = run_subprocess(['git', '--version'], capture_output=True, check=False, text=True)
                if result.returncode != 0:
                    self.show_dependency_error("Git Not Found", "Git is not installed or not in your PATH. Cannot uninstall hooks.")
                    return
            except FileNotFoundError:
                self.show_dependency_error("Git Not Found", "Git is not installed or not in your PATH. Cannot uninstall hooks.")
                return
                
            # Remove Git configurations
            run_subprocess(['git', 'config', '--global', '--unset', 'core.hooksPath'], check=False)
            
            # Remove .apigenie directory completely
            apigenie_dir = os.path.expanduser('~/.apigenie')
            if os.path.exists(apigenie_dir):
                shutil.rmtree(apigenie_dir)
            
            # Verify uninstallation
            if os.path.exists(apigenie_dir):
                raise Exception("Failed to remove .apigenie directory")
                
            hooks_path_result = run_subprocess(['git', 'config', '--global', '--get', 'core.hooksPath'],
                                            capture_output=True, text=True, check=False)
            if hooks_path_result.returncode == 0 and hooks_path_result.stdout.strip():
                raise Exception("Git hooks path still set")
                
            # Handle success
            self.is_first_run = True
            self.create_native_welcome_ui()
            
            # Update status display
            self.update_status_display()
            
            # Show success message
            QMessageBox.information(self, "Uninstallation Successful", 
                                  "✓ APIGenie hooks have been successfully removed!\n\n" +
                                  "Git repositories will no longer validate API compliance.")
            
        except Exception as e:
            QMessageBox.critical(self, "Uninstallation Failed", f"Unable to remove hooks:\n{str(e)}")

    def create_native_welcome_ui(self):
        """Create a native UI for first run welcome screen."""
        from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, 
                                    QLabel, QWidget, QTextBrowser)
        
        # Main container widget
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Add logo at top
        if os.path.exists(self.logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(self.logo_path)
            scaled_pixmap = pixmap.scaledToWidth(150)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(logo_label)
        
        # Add title
        title_label = QLabel("Welcome to APIGenie")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #07439C; margin: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Info text
        info_text = QTextBrowser()
        info_text.setOpenExternalLinks(True)
        info_text.setMaximumHeight(200)
        info_text.setHtml("""
        <div style='margin: 15px;'>
            <h3>API Validation Tool</h3>
            <p>APIGenie helps enforce API compliance standards by validating your API metadata files during Git commits.</p>
            <p>To get started, click the button below to install APIGenie's Git hooks.</p>
        </div>
        """)
        main_layout.addWidget(info_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 10)
        
        install_btn = QPushButton("Install Hooks")
        install_btn.setMinimumHeight(40)
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #07439C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #053278;
            }
        """)
        install_btn.clicked.connect(self.install_hooks)
        
        exit_btn = QPushButton("Exit")
        exit_btn.setMinimumHeight(40)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        exit_btn.clicked.connect(self.close)
        
        button_layout.addWidget(install_btn)
        button_layout.addWidget(exit_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status label at bottom
        self.status_label = QLabel("Ready to install API validation hooks")
        self.status_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        main_layout.addWidget(self.status_label)
        
        # Update status on load
        self.update_status_display()
        
        # Set the central widget
        self.setCentralWidget(container)
        
        # Set fixed window size to fit content
        self.setFixedSize(500, 500)
        self.setMinimumSize(500, 500)

    def create_native_main_ui(self):
        """Create a native UI for main screen after installation."""
        from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, 
                                    QLabel, QWidget, QTextBrowser)
        
        # Main container widget
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Add logo at top
        if os.path.exists(self.logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(self.logo_path)
            scaled_pixmap = pixmap.scaledToWidth(120)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(logo_label)
        
        # Add title
        title_label = QLabel("APIGenie - API Validation Tool")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #07439C; margin: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Info text
        info_text = QTextBrowser()
        info_text.setOpenExternalLinks(True)
        info_text.setMaximumHeight(250)
        info_text.setHtml("""
        <div style='margin: 15px;'>
            <h3>Hooks Installed Successfully</h3>
            <p>APIGenie is now monitoring your Git commits for API compliance.</p>
            <h4>How APIGenie Works:</h4>
            <ul>
                <li>Validates API metadata files during commits</li>
                <li>Enforces compliance with 20 standardization rules</li>
                <li>Shows interactive validation dialog for failures</li>
                <li>Allows justification entry with audit trail</li>
                <li>Works across all repositories automatically</li>
            </ul>
        </div>
        """)
        main_layout.addWidget(info_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 10)

        uninstall_btn = QPushButton("Uninstall Hooks")
        uninstall_btn.setMinimumHeight(40)
        uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        uninstall_btn.clicked.connect(self.uninstall_hooks)

        exit_btn = QPushButton("Exit")
        exit_btn.setMinimumHeight(40)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        exit_btn.clicked.connect(self.close)

        button_layout.addWidget(uninstall_btn)
        button_layout.addWidget(exit_btn)

        main_layout.addLayout(button_layout)

        # Status label at bottom
        self.status_label = QLabel("API validation hooks are active")
        self.status_label.setStyleSheet("color: green; font-style: italic; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        # Update status on load
        self.update_status_display()

        # Set the central widget
        self.setCentralWidget(container)

        # Set fixed window size to fit content
        self.setFixedSize(500, 550)
        self.setMinimumSize(500, 550)

    def update_status_display(self):
        """Update the status label with current installation status."""
        if hasattr(self, 'status_label'):
            status = self.get_installation_status()
            
            if status['installed']:
                if status['config_exists'] and status['hooks_exist'] and status['validation_exists'] and status['git_configured']:
                    self.status_label.setText("✓ Installation complete and fully configured")
                    self.status_label.setStyleSheet("color: green; font-style: italic; font-size: 12px;")
                else:
                    self.status_label.setText("⚠ Installation detected but may have issues (click Check Status)")
                    self.status_label.setStyleSheet("color: orange; font-style: italic; font-size: 12px;")
            else:
                self.status_label.setText("✗ No installation detected")
                self.status_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")

    def show_status_details(self):
        """Show detailed status information in a dialog."""
        status = self.get_installation_status()
        
        # Create detailed status message
        details_text = "APIGenie Installation Status\n" + "="*50 + "\n\n"
        
        if status['installed']:
            details_text += "Overall Status: ✓ INSTALLED\n\n"
        else:
            details_text += "Overall Status: ✗ NOT INSTALLED\n\n"
        
        details_text += "Component Details:\n"
        for detail in status['details']:
            details_text += f"  {detail}\n"
        
        # Add installation directory info
        apigenie_dir = os.path.expanduser('~/.apigenie')
        details_text += f"\nInstallation Directory: {apigenie_dir}\n"
        
        # Show in message box
        QMessageBox.information(
            self,
            "Installation Status Details", 
            details_text,
            QMessageBox.StandardButton.Ok
        )

    def create_native_ui(self):
        """Select the appropriate native UI based on first run status."""
        if self.is_first_run:
            self.create_native_welcome_ui()
        else:
            self.create_native_main_ui()

def install_hooks_cli():
    """Install hooks from command line without GUI."""
    try:
        print("Installing APIGenie hooks...")
        
        # Check Git installation
        try:
            result = run_subprocess(['git', '--version'], capture_output=True, check=False, text=True)
            if result.returncode != 0:
                print("ERROR: Git is not installed or not in your PATH. Please install Git and try again.")
                return False
        except FileNotFoundError:
            print("ERROR: Git is not installed or not in your PATH. Please install Git and try again.")
            return False
        
        # Check Git configuration
        username_result = run_subprocess(['git', 'config', '--global', 'user.name'], capture_output=True, check=False, text=True)
        email_result = run_subprocess(['git', 'config', '--global', 'user.email'], capture_output=True, check=False, text=True)
        
        if username_result.returncode != 0 or not username_result.stdout.strip():
            print("ERROR: Git username is not configured. Please run:")
            print("git config --global user.name \"Your Name\"")
            return False
            
        if email_result.returncode != 0 or not email_result.stdout.strip():
            print("ERROR: Git email is not configured. Please run:")
            print("git config --global user.email \"your.email@example.com\"")
            return False
        
        print("Dependencies check passed.")
        
        # Get source directories
        if getattr(sys, 'frozen', False):
            hooks_source = os.path.join(sys._MEIPASS, 'hooks')
            validation_source = os.path.join(sys._MEIPASS, 'validation')
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
            hooks_source = os.path.join(app_path, 'hooks')
            validation_source = os.path.join(app_path, 'validation')
        
        if not os.path.exists(hooks_source):
            print(f"ERROR: Hooks directory not found at {hooks_source}")
            return False
        
        if not os.path.exists(validation_source):
            print(f"ERROR: Validation directory not found at {validation_source}")
            return False
        
        # Check if already installed using comprehensive detection
        apigenie_dir = os.path.expanduser('~/.apigenie')
        hooks_dir = os.path.join(apigenie_dir, 'hooks')
        validation_dir = os.path.join(apigenie_dir, 'validation')
        config_file = os.path.join(apigenie_dir, 'config')
        
        # Check config file
        config_installed = False
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'installed=true' in content:
                        config_installed = True
            except:
                pass
        
        # Check hooks exist
        hooks_installed = False
        if os.path.exists(hooks_dir):
            essential_hooks = ['pre-commit', 'pre-push']
            hooks_installed = all(os.path.exists(os.path.join(hooks_dir, hook)) for hook in essential_hooks)
        
        # Check validation system
        validation_installed = os.path.exists(validation_dir)
        
        # Check git configuration
        git_configured = False
        try:
            hooks_path_result = run_subprocess(['git', 'config', '--global', '--get', 'core.hooksPath'],
                                            capture_output=True, text=True, check=False)
            if hooks_path_result.returncode == 0 and hooks_path_result.stdout.strip() == hooks_dir:
                git_configured = True
        except:
            pass
        
        # Determine if installed
        is_installed = (config_installed or hooks_installed) and validation_installed
        
        if is_installed:
            print("✓ APIGenie hooks are already installed!")
            if not config_installed:
                print("  Note: Config file missing but installation detected")
            if not hooks_installed:
                print("  Note: Some hook files may be missing")
            if not validation_installed:
                print("  Warning: Validation system missing")
            if not git_configured:
                print("  Warning: Git hooks path not configured correctly")
            return True
        
        # Create directories
        os.makedirs(hooks_dir, exist_ok=True)
        validation_dir = os.path.join(apigenie_dir, 'validation')
        os.makedirs(validation_dir, exist_ok=True)
        
        # Copy files
        print(f"Copying hooks from {hooks_source} to {hooks_dir}...")
        for item in os.listdir(hooks_source):
            src_path = os.path.join(hooks_source, item)
            dst_path = os.path.join(hooks_dir, item)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
                if item in ['pre-commit', 'pre-push', 'commit-msg']:
                    os.chmod(dst_path, 0o755)
        
        print(f"Copying validation from {validation_source} to {validation_dir}...")
        shutil.copytree(validation_source, validation_dir, dirs_exist_ok=True)
        
        # Configure Git
        print("Configuring Git...")
        run_subprocess(['git', 'config', '--global', 'core.hooksPath', hooks_dir], check=True)
        
        # Mark as installed
        with open(config_file, 'w') as f:
            f.write('installed=true\n')
        
        print("✓ APIGenie hooks installed successfully!")
        print("\nAPIGenie is now monitoring your Git commits for API compliance.")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to install hooks: {str(e)}")
        return False

def uninstall_hooks_cli():
    """Uninstall hooks from command line without GUI."""
    try:
        print("Uninstalling APIGenie hooks...")
        
        # Remove Git configuration
        run_subprocess(['git', 'config', '--global', '--unset', 'core.hooksPath'], check=False)
        
        # Remove .apigenie directory
        apigenie_dir = os.path.expanduser('~/.apigenie')
        if os.path.exists(apigenie_dir):
            shutil.rmtree(apigenie_dir)
            print("Removed .apigenie directory")
        
        print("✓ APIGenie hooks uninstalled successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to uninstall hooks: {str(e)}")
        return False

if __name__ == '__main__':
    # Check for CLI mode FIRST before importing any GUI components
    cli_mode = False
    
    # Check if any command line arguments indicate CLI mode
    for arg in sys.argv[1:]:
        if arg.lower() in ['/install', '--install', '/uninstall', '--uninstall', '-install', '-uninstall']:
            cli_mode = True
            break
    
    # Also check for help arguments
    for arg in sys.argv[1:]:
        if arg.lower() in ['/help', '--help', '-h', '/?']:
            cli_mode = True
            break
    
    if cli_mode:
        # CLI Mode - Handle without GUI
        print("APIGenie - API Validation Tool")
        print("Running in CLI mode...")
        
        # Determine action
        install_requested = False
        uninstall_requested = False
        help_requested = False
        
        for arg in sys.argv[1:]:
            if arg.lower() in ['/install', '--install', '-install']:
                install_requested = True
            elif arg.lower() in ['/uninstall', '--uninstall', '-uninstall']:
                uninstall_requested = True
            elif arg.lower() in ['/help', '--help', '-h', '/?']:
                help_requested = True
        
        if help_requested:
            print("\nUsage:")
            print("  APIGenie.exe /install    - Install hooks without GUI")
            print("  APIGenie.exe /uninstall  - Uninstall hooks without GUI")
            print("  APIGenie.exe /help       - Show this help message")
            print("  APIGenie.exe             - Open GUI interface")
            sys.exit(0)
        
        # Execute the requested action
        success = False
        
        if install_requested:
            success = install_hooks_cli()
        elif uninstall_requested:
            success = uninstall_hooks_cli()
        else:
            print("ERROR: No valid command specified.")
            print("Use /install, /uninstall, or /help")
            success = False
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
    
    # GUI Mode
    try:
        # Initialize QApplication
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Get application path
        if getattr(sys, 'frozen', False):
            app_path = sys._MEIPASS
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        # Get the logo path
        logo_path = os.path.join(app_path, 'assets', 'logo.png')
        
        # Show splash screen with logo if it exists
        splash = None
        if os.path.exists(logo_path):
            splash_pix = QPixmap(logo_path)
            if not splash_pix.isNull():
                splash = QSplashScreen(splash_pix)
                splash.show()
        
        # Initialize main window
        main = APIGenieApp()
        main.show()
        
        # Finish splash screen if it was shown
        if splash:
            splash.finish(main)
        
        # Start event loop
        exit_code = app.exec()
        sys.exit(exit_code)
        
    except Exception as e:
        try:
            if 'app' in locals():
                QMessageBox.critical(None, "Fatal Error", f"A fatal error occurred:\n\n{str(e)}")
        except:
            pass
        
        sys.exit(1)
