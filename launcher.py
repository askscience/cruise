#!/usr/bin/env python3
"""
Transcriber Application Launcher

This script serves as the main entry point for the transcriber application.
It checks if this is the first run and shows the welcome screen if needed,
otherwise launches the main application directly.
"""

import sys
import os
import multiprocessing

# Ensure we are running inside the project's virtual environment to avoid
# system Python picking up incompatible global packages (e.g., NumPy/Torch)
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, 'transcriber_env', 'bin', 'python')
    # If a local venv exists and current interpreter is not from it, re-exec
    if os.path.exists(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)
except Exception:
    # If anything goes wrong, continue with current interpreter
    pass

# Set environment variables to prevent threading conflicts and segmentation faults
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['KMP_AFFINITY'] = 'disabled'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['QT_MAC_WANTS_LAYER'] = '1'

# Disable OpenMP before any imports
try:
    import ctypes
    # Try to disable OpenMP nesting at C level before any library loads
    try:
        libomp = ctypes.CDLL("libomp.dylib", mode=ctypes.RTLD_GLOBAL)
        libomp.omp_set_nested(0)
        libomp.omp_set_max_active_levels(1)
    except:
        try:
            # Alternative library names
            libomp = ctypes.CDLL("libgomp.dylib", mode=ctypes.RTLD_GLOBAL)
            libomp.omp_set_nested(0)
        except:
            pass
except:
    pass

from PySide6.QtWidgets import QApplication

# Add the current directory to the Python path
# Handle cases where __file__ might not be defined (e.g., when run via exec())
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback to current working directory if __file__ is not defined
    script_dir = os.getcwd()
sys.path.insert(0, script_dir)

from app.setup.welcome_screen import WelcomeScreen
from app.setup.system_checker import ConfigManager
from app.utils.translation_manager import get_translation_manager


def main():
    """Main application launcher."""
    # Set start method for multiprocessing to 'spawn' for safety on macOS
    if sys.platform == 'darwin':
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass

    app = QApplication(sys.argv)
    
    # Initialize translation system early
    translation_manager = get_translation_manager()
    
    # Check if setup has been completed
    config_manager = ConfigManager()
    
    if not config_manager.is_setup_completed():
        # Show welcome screen
        welcome = WelcomeScreen()
        welcome.setup_completed.connect(lambda: launch_main_app(app))
        welcome.show()
    else:
        # Launch main app directly
        launch_main_app(app)
    
    sys.exit(app.exec())


def launch_main_app(app):
    """Launch the main transcriber application."""
    try:
        from app.main.main_gui import AudioTranscriberGUI
        
        # Close any existing windows
        for widget in app.allWidgets():
            if hasattr(widget, 'close'):
                widget.close()
        
        # Create and show main application
        main_window = AudioTranscriberGUI()
        main_window.show()
        
    except ImportError as e:
        print(f"Error importing main application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()