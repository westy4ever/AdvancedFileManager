# -*- coding: utf-8 -*-
import os
import time
import json
import hashlib
import threading
from collections import OrderedDict

class CacheManager:
    """
    File metadata cache manager for performance optimization
    Uses LRU (Least Recently Used) eviction policy
    """
    
    def __init__(self, max_size=1000, expire_time=300):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of cached items
            expire_time: Cache expiration time in seconds
        """
        self.max_size = max_size
        self.expire_time = expire_time
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.cache_file = "/tmp/afm_cache.json"
        
        # Load persistent cache
        self.load_cache()
    
    def _get_key(self, path):
        """Generate cache key from path"""
        return hashlib.md5(path.encode('utf-8')).hexdigest()
    
    def get(self, path):
        """
        Get cached metadata for path
        
        Returns:
            dict: Cached metadata or None if not found/expired
        """
        key = self._get_key(path)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check expiration
                if time.time() - entry['timestamp'] < self.expire_time:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return entry['data']
                else:
                    # Expired, remove
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    def set(self, path, data):
        """
        Cache metadata for path
        
        Args:
            path: File path
            data: Metadata dictionary to cache
        """
        key = self._get_key(path)
        
        with self.lock:
            # Remove oldest if at capacity
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[key] = {
                'path': path,
                'timestamp': time.time(),
                'data': data
            }
            self.cache.move_to_end(key)
    
    def invalidate(self, path):
        """Remove specific path from cache"""
        key = self._get_key(path)
        
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def invalidate_directory(self, directory):
        """Remove all entries under directory"""
        with self.lock:
            keys_to_remove = []
            for key, entry in self.cache.items():
                if entry['path'].startswith(directory):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
    
    def clear(self):
        """Clear all cached data"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'expire_time': self.expire_time
            }
    
    def save_cache(self):
        """Save cache to persistent storage"""
        try:
            with self.lock:
                # Only save non-expired entries
                valid_entries = {}
                current_time = time.time()
                
                for key, entry in self.cache.items():
                    if current_time - entry['timestamp'] < self.expire_time:
                        valid_entries[key] = entry
                
                with open(self.cache_file, 'w') as f:
                    json.dump(valid_entries, f)
                    
        except Exception as e:
            print(f"Cache save error: {e}")
    
    def load_cache(self):
        """Load cache from persistent storage"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    
                with self.lock:
                    self.cache = OrderedDict(data)
                    
        except Exception as e:
            print(f"Cache load error: {e}")
            self.cache = OrderedDict()
    
    def __del__(self):
        """Destructor - save cache on exit"""
        self.save_cache()