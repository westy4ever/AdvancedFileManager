# -*- coding: utf-8 -*-
import os
import re
import fnmatch
import threading
from threading import Thread, Event
from Components.config import config

class SearchEngine:
    def __init__(self):
        self.search_thread = None
        self.stop_event = Event()
        self.results = []
        self.progress_callback = None
    
    def search(self, path, pattern, options=None):
        """
        Advanced search with pattern matching and filters
        
        Options:
        - recursive: Search subdirectories (default: True)
        - case_sensitive: Case-sensitive matching (default: False)
        - regex: Use regex pattern (default: False)
        - file_types: List of extensions to include (default: None)
        - size_min: Minimum file size in bytes (default: None)
        - size_max: Maximum file size in bytes (default: None)
        - date_after: Modified after timestamp (default: None)
        - date_before: Modified before timestamp (default: None)
        - content_search: Search within file contents (default: False)
        """
        options = options or {}
        self.stop_event.clear()
        self.results = []
        
        self.search_thread = Thread(
            target=self._search_worker,
            args=(path, pattern, options)
        )
        self.search_thread.start()
    
    def _search_worker(self, path, pattern, options):
        """Background search worker"""
        recursive = options.get('recursive', True)
        case_sensitive = options.get('case_sensitive', False)
        use_regex = options.get('regex', False)
        file_types = options.get('file_types', [])
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            if recursive:
                for root, dirs, files in os.walk(path):
                    if self.stop_event.is_set():
                        break
                    
                    # Skip hidden directories if not showing hidden
                    if not config.plugins.advancedfilemanager.showhidden.value:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for filename in files:
                        if self.stop_event.is_set():
                            return
                        
                        if self._match_file(filename, pattern, use_regex, flags, file_types):
                            full_path = os.path.join(root, filename)
                            if self._match_filters(full_path, options):
                                self.results.append(full_path)
                                if self.progress_callback:
                                    self.progress_callback(full_path)
            else:
                for filename in os.listdir(path):
                    if self.stop_event.is_set():
                        break
                    
                    full_path = os.path.join(path, filename)
                    if os.path.isfile(full_path):
                        if self._match_file(filename, pattern, use_regex, flags, file_types):
                            if self._match_filters(full_path, options):
                                self.results.append(full_path)
                                if self.progress_callback:
                                    self.progress_callback(full_path)
        
        except Exception as e:
            print(f"Search error: {e}")
    
    def _match_file(self, filename, pattern, use_regex, flags, file_types):
        """Check if filename matches pattern"""
        # Check file type filter first
        if file_types:
            if not any(filename.lower().endswith(ext.lower()) for ext in file_types):
                return False
        
        if use_regex:
            return re.search(pattern, filename, flags) is not None
        else:
            if flags & re.IGNORECASE:
                return fnmatch.fnmatch(filename.lower(), pattern.lower())
            return fnmatch.fnmatch(filename, pattern)
    
    def _match_filters(self, filepath, options):
        """Apply additional filters (size, date)"""
        try:
            stat = os.stat(filepath)
            
            # Size filters
            size_min = options.get('size_min')
            if size_min is not None and stat.st_size < size_min:
                return False
            
            size_max = options.get('size_max')
            if size_max is not None and stat.st_size > size_max:
                return False
            
            # Date filters
            date_after = options.get('date_after')
            if date_after is not None and stat.st_mtime < date_after:
                return False
            
            date_before = options.get('date_before')
            if date_before is not None and stat.st_mtime > date_before:
                return False
            
            return True
        except:
            return False
    
    def stop(self):
        """Stop ongoing search"""
        self.stop_event.set()
        if self.search_thread:
            self.search_thread.join(timeout=1)
    
    def get_results(self):
        """Get current search results"""
        return self.results.copy()
    
    def is_running(self):
        """Check if search is active"""
        return self.search_thread and self.search_thread.is_alive()