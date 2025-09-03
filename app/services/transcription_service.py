"""
Audio Transcription Service
Handles all Whisper AI model operations and audio processing logic.
"""

import whisper
import threading
import os
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from app.setup.system_checker import ConfigManager


class TranscriptionThread(QThread):
    """Thread for handling audio transcription without blocking the UI."""
    
    transcription_done = Signal(object)  # Changed to object to pass full result
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def __init__(self, model, file_path):
        super().__init__()
        self.model = model
        self.file_path = file_path

    def run(self):
        try:
            import torch
            torch.set_num_threads(1)

            self.progress_update.emit("Analyzing audio file...")
            
            # Use word_timestamps=True to get precise word-level timing
            result = self.model.transcribe(self.file_path, word_timestamps=True)
            self.progress_update.emit("Processing sentences...")
            
            # Process the result to create sentence-level segments
            processed_result = self._create_sentence_segments(result)
            
            self.progress_update.emit("Transcription complete!")
            self.transcription_done.emit(processed_result)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _create_sentence_segments(self, whisper_result):
        """Create sentence-level segments from Whisper's word-level timestamps."""
        import re
        
        if 'segments' not in whisper_result:
            return whisper_result
        
        sentence_segments = []
        current_sentence = {
            'text': '',
            'words': [],
            'start': None,
            'end': None
        }
        
        for segment in whisper_result['segments']:
            if 'words' not in segment or not segment.get('words'):
                # If no word-level timestamps, treat the segment as a single sentence
                sentence_segments.append({
                    'text': segment.get('text', '').strip(),
                    'start': segment.get('start', 0),
                    'end': segment.get('end', 0),
                    'words': []
                })
                continue
            
            words = segment['words']
            for word in words:
                word_text = word.get('word', '').strip()
                if not word_text:
                    continue
                
                # Initialize sentence start time if this is the first word
                if current_sentence['start'] is None:
                    current_sentence['start'] = word['start']
                
                # Add word to current sentence
                current_sentence['words'].append(word)
                current_sentence['text'] += word_text
                current_sentence['end'] = word['end']
                
                # Check if this word ends with sentence-ending punctuation
                if re.search(r'[.!?。！？][\'"")]?$', word_text):
                    # Finalize current sentence
                    if current_sentence['text'].strip():
                        sentence_segments.append({
                            'text': current_sentence['text'].strip(),
                            'start': current_sentence['start'],
                            'end': current_sentence['end'],
                            'words': current_sentence['words']
                        })
                    
                    # Reset for next sentence
                    current_sentence = {
                        'text': '',
                        'words': [],
                        'start': None,
                        'end': None
                    }
                else:
                    # Add space after word unless it's punctuation
                    if not re.match(r'^[,;:)\]}"\'、，；：）】」』\']+$', word_text):
                        current_sentence['text'] += ' '
        
        # Add any remaining sentence
        if current_sentence['text'].strip():
            sentence_segments.append({
                'text': current_sentence['text'].strip(),
                'start': current_sentence['start'],
                'end': current_sentence['end'],
                'words': current_sentence['words']
            })
        
        # Return modified result with sentence-level segments
        result_copy = whisper_result.copy()
        result_copy['segments'] = sentence_segments
        return result_copy


class ModelLoadingThread(QThread):
    """Thread for loading Whisper models with progress feedback."""
    
    progress_update = Signal(str)
    loading_complete = Signal(bool, str)
    
    def __init__(self, model_size, config_manager):
        super().__init__()
        self.model_size = model_size
        self.config_manager = config_manager
        self.model = None
    
    def run(self):
        try:
            self.progress_update.emit(f"Preparing to load {self.model_size} model...")
            
            # Set threading constraints before loading Whisper model
            import torch
            
            self.progress_update.emit("Configuring threading settings...")
            
            # Force single-threaded execution for all libraries
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            os.environ['KMP_AFFINITY'] = 'disabled'
            
            # Set PyTorch to single thread
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            
            # Disable OpenMP nested parallelism
            try:
                import ctypes
                # Try to disable OpenMP nesting at C level
                libomp = ctypes.CDLL("libomp.dylib", mode=ctypes.RTLD_GLOBAL)
                libomp.omp_set_nested(0)
            except:
                pass
            
            self.progress_update.emit(f"Downloading and loading {self.model_size} model...")
            self.progress_update.emit("This may take several minutes for the first download.")
            
            # Load the model (this will download if not cached)
            self.model = whisper.load_model(self.model_size)
            
            self.progress_update.emit("Model loaded successfully!")
            self.loading_complete.emit(True, f"Model '{self.model_size}' loaded successfully")
            
        except Exception as e:
            import traceback
            error_details = str(e)
            
            # Categorize different types of errors and provide helpful messages
            if "No module named" in error_details or "ImportError" in str(type(e)):
                error_msg = f"Missing dependencies for Whisper model. Please ensure all required packages are installed. Error: {error_details}"
            elif "Connection" in error_details or "Network" in error_details or "timeout" in error_details.lower():
                error_msg = f"Network error while downloading model '{self.model_size}'. Please check your internet connection and try again. Error: {error_details}"
            elif "Permission" in error_details or "Access" in error_details:
                error_msg = f"Permission denied while downloading/saving model '{self.model_size}'. Please check file permissions in the cache directory. Error: {error_details}"
            elif "No space" in error_details or "Disk" in error_details:
                error_msg = f"Insufficient disk space to download model '{self.model_size}'. Please free up space and try again. Error: {error_details}"
            elif "CUDA" in error_details or "GPU" in error_details:
                error_msg = f"GPU/CUDA error while loading model '{self.model_size}'. Falling back to CPU mode may help. Error: {error_details}"
            elif "corrupted" in error_details.lower() or "checksum" in error_details.lower():
                error_msg = f"Model file appears to be corrupted. Please clear the Whisper cache and try again. Error: {error_details}"
            else:
                error_msg = f"Failed to load model '{self.model_size}': {error_details}"
            
            # Log the full traceback for debugging
            full_traceback = traceback.format_exc()
            print(f"Model loading error traceback:\n{full_traceback}")
            
            self.progress_update.emit(f"Error: {error_msg}")
            self.loading_complete.emit(False, error_msg)


class TranscriptionService:
    """Core transcription service that manages Whisper model and file validation."""
    
    def __init__(self):
        self.model = None
        self.config_manager = ConfigManager()
        self.model_loading_thread = None
        self.supported_formats = [
            ".mp3", ".wav", ".m4a", ".flac", ".aac", 
            ".ogg", ".wma", ".mp4", ".avi", ".mov"
        ]
    
    def load_model(self, model_size=None):
        """Load the Whisper model using configured model or specified size."""
        if model_size is None:
            model_size = self.config_manager.get_whisper_model()
        
        try:
            # Set threading constraints before loading Whisper model
            import os
            import torch
            
            # Force single-threaded execution for all libraries
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            os.environ['KMP_AFFINITY'] = 'disabled'
            
            # Set PyTorch to single thread
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            
            # Disable OpenMP nested parallelism
            try:
                import ctypes
                # Try to disable OpenMP nesting at C level
                libomp = ctypes.CDLL("libomp.dylib", mode=ctypes.RTLD_GLOBAL)
                libomp.omp_set_nested(0)
            except:
                pass
            
            self.model = whisper.load_model(model_size)
            return True, f"Model '{model_size}' loaded successfully"
        except Exception as e:
            return False, f"Failed to load model '{model_size}': {str(e)}"
    
    def load_model_async(self, callback):
        """Load model asynchronously."""
        def load():
            success, message = self.load_model()
            callback(success, message)
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def load_model_with_progress(self, progress_callback, completion_callback, model_size=None):
        """Load the Whisper model asynchronously with progress feedback and retry functionality.
        
        Args:
            progress_callback: Function to call with progress updates (str)
            completion_callback: Function to call when loading completes (bool, str)
            model_size: Size of the model to load (optional)
        """
        if model_size is None:
            model_size = self.config_manager.get_whisper_model()
        
        # Use the retry functionality for better error handling
        return self.load_model_with_retry(model_size, max_retries=3, 
                                        progress_callback=progress_callback, 
                                        completion_callback=completion_callback)
    
    def validate_file(self, file_path):
        """Validate if the file exists and is in a supported format."""
        import os
        
        if not file_path or not file_path.strip():
            return False, "No file selected."
        
        if not os.path.exists(file_path):
            return False, "File does not exist."
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.supported_formats:
            return False, f"Unsupported file format. Supported formats: {', '.join(self.supported_formats)}"
        
        return True, "File is valid."
    
    def get_file_info(self, file_path):
        """Get file information like size, name, and duration."""
        import os
        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            file_name = Path(file_path).name
            duration = self.get_audio_duration(file_path)
            return file_name, file_size, duration
        except Exception:
            return None, 0, 0
    
    def get_audio_duration(self, file_path):
        """Get audio duration in seconds."""
        try:
            # Try using mutagen first (lightweight)
            from mutagen import File
            audio_file = File(file_path)
            if audio_file is not None and hasattr(audio_file, 'info'):
                return float(audio_file.info.length)
        except ImportError:
            pass
        except Exception:
            pass
        
        try:
            # Fallback to librosa if mutagen fails
            import librosa
            duration = librosa.get_duration(path=file_path)
            return float(duration)
        except ImportError:
            pass
        except Exception:
            pass
        
        try:
            # Last resort: use ffprobe if available
            import subprocess
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', file_path
            ], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        
        # Default fallback
        return 60.0
    
    def create_transcription_thread(self, file_path):
        """Create a transcription thread for the given file."""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        return TranscriptionThread(self.model, file_path)
    
    def get_supported_formats_filter(self):
        """Get file dialog filter string for supported formats."""
        extensions = " ".join([f"*{ext}" for ext in self.supported_formats])
        return f"Audio/Video Files ({extensions});;All Files (*.*)"
    
    def clear_whisper_cache(self):
        """Clear Whisper model cache to fix corrupted downloads."""
        import shutil
        try:
            # Get Whisper cache directory
            cache_dir = os.path.expanduser("~/.cache/whisper")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                return True, "Whisper cache cleared successfully"
            else:
                return True, "No cache directory found"
        except Exception as e:
            return False, f"Failed to clear cache: {str(e)}"
    
    def load_model_with_retry(self, model_size=None, max_retries=3, progress_callback=None, completion_callback=None):
        """Load model with retry functionality for network errors."""
        if model_size is None:
            model_size = self.config_manager.get_whisper_model()
        
        def attempt_load(attempt):
            if progress_callback:
                progress_callback(f"Loading attempt {attempt + 1}/{max_retries}...")
            
            self.model_loading_thread = ModelLoadingThread(model_size, self.config_manager)
            
            def on_loading_complete(success, message):
                if success:
                    self.model = self.model_loading_thread.model
                    if completion_callback:
                        completion_callback(True, message)
                else:
                    # Check if this is a network error and we have retries left
                    is_network_error = any(keyword in message.lower() for keyword in 
                                         ['network', 'connection', 'timeout', 'download'])
                    
                    if is_network_error and attempt < max_retries - 1:
                        if progress_callback:
                            progress_callback(f"Network error, retrying in 2 seconds... ({attempt + 2}/{max_retries})")
                        # Retry after a short delay
                        import time
                        time.sleep(2)
                        attempt_load(attempt + 1)
                    else:
                        if completion_callback:
                            completion_callback(False, message)
            
            if progress_callback:
                self.model_loading_thread.progress_update.connect(progress_callback)
            self.model_loading_thread.loading_complete.connect(on_loading_complete)
            self.model_loading_thread.start()
        
        attempt_load(0)
        return self.model_loading_thread
    
    def get_troubleshooting_suggestions(self, error_message):
        """Get troubleshooting suggestions based on the error message."""
        suggestions = []
        
        if "network" in error_message.lower() or "connection" in error_message.lower():
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few minutes",
                "Consider using a different network if available"
            ])
        
        if "permission" in error_message.lower() or "access" in error_message.lower():
            suggestions.extend([
                "Check file permissions in your home directory",
                "Try running the application with appropriate permissions",
                "Ensure the cache directory is writable"
            ])
        
        if "space" in error_message.lower() or "disk" in error_message.lower():
            suggestions.extend([
                "Free up disk space (models can be 100MB-1GB+)",
                "Check available space in your home directory",
                "Consider using a smaller model size"
            ])
        
        if "corrupted" in error_message.lower() or "checksum" in error_message.lower():
            suggestions.extend([
                "Clear the Whisper model cache",
                "Try downloading the model again"
            ])
        
        if "cuda" in error_message.lower() or "gpu" in error_message.lower():
            suggestions.extend([
                "Try using CPU mode instead of GPU",
                "Update your GPU drivers",
                "Check CUDA installation if using GPU"
            ])
        
        # General suggestions
        suggestions.extend([
            "Try using a smaller model (e.g., 'tiny' or 'base')",
            "Restart the application",
            "Check the application logs for more details"
        ])
        
        return suggestions
