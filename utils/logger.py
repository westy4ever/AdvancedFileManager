# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime
from Components.config import config

class Logger:
    """Configurable logging system for the file manager"""
    
    LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    def __init__(self, name="AdvancedFileManager", level=None):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set level from config or parameter
        if level is None:
            level = getattr(config.plugins.advancedfilemanager, 'log_level', 'INFO')
        
        self.logger.setLevel(self.LEVELS.get(level, logging.INFO))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers"""
        # Log file path
        log_dir = "/tmp"
        log_file = os.path.join(log_dir, f"{self.name.lower()}.log")
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Console handler (for debugging)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)
    
    def log_operation(self, operation, details, success=True):
        """Log file operation with details"""
        status = "SUCCESS" if success else "FAILED"
        self.info(f"[{status}] {operation}: {details}")
    
    def get_log_path(self):
        """Return path to log file"""
        return os.path.join("/tmp", f"{self.name.lower()}.log")
    
    def clear_logs(self):
        """Clear log file"""
        try:
            log_path = self.get_log_path()
            if os.path.exists(log_path):
                with open(log_path, 'w'):
                    pass
                return True
        except Exception as e:
            self.error(f"Failed to clear logs: {e}")
        return False