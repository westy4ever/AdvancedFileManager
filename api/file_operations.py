# -*- coding: utf-8 -*-
import os
import shutil
import threading
from enigma import eTimer
from Components.config import config

class FileOperationError(Exception):
    """Custom exception for file operations"""
    pass

class PermissionError(FileOperationError):
    pass

class PathNotFoundError(FileOperationError):
    pass

class FileOperationManager:
    def __init__(self):
        self.current_operation = None
        self.operation_thread = None
        self.progress_callback = None
        self.error_callback = None
        
    def validate_path(self, path):
        """Security: Validate and sanitize paths"""
        if not path or not isinstance(path, str):
            raise PathNotFoundError("Invalid path")
        
        # Prevent directory traversal attacks
        real_path = os.path.realpath(path)
        blocked_paths = ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/proc', '/sys']
        
        for blocked in blocked_paths:
            if real_path.startswith(blocked):
                raise PermissionError(f"Access denied to system path: {path}")
        
        return real_path
    
    def copy(self, src, dst, overwrite=False):
        """Copy files or directories with progress tracking"""
        try:
            src = self.validate_path(src)
            dst = self.validate_path(dst)
            
            if not os.path.exists(src):
                raise PathNotFoundError(f"Source not found: {src}")
            
            if os.path.exists(dst) and not overwrite:
                raise FileOperationError(f"Destination exists: {dst}")
            
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dst)
                
            return True
            
        except Exception as e:
            raise FileOperationError(f"Copy failed: {str(e)}")
    
    def move(self, src, dst):
        """Move files or directories"""
        try:
            src = self.validate_path(src)
            dst = self.validate_path(dst)
            shutil.move(src, dst)
            return True
        except Exception as e:
            raise FileOperationError(f"Move failed: {str(e)}")
    
    def rename(self, src, new_name):
        """Rename file or directory"""
        try:
            src = self.validate_path(src)
            dst = os.path.join(os.path.dirname(src), new_name)
            dst = self.validate_path(dst)
            os.rename(src, dst)
            return True
        except Exception as e:
            raise FileOperationError(f"Rename failed: {str(e)}")
    
    def delete(self, path, use_trash=None):
        """Delete with optional trash support"""
        try:
            path = self.validate_path(path)
            
            if use_trash is None:
                use_trash = config.plugins.advancedfilemanager.use_trash.value
            
            if use_trash:
                from .trash_manager import TrashManager
                trash = TrashManager()
                return trash.trash(path)
            else:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return True
                
        except Exception as e:
            raise FileOperationError(f"Delete failed: {str(e)}")
    
    def batch_operation(self, items, operation, **kwargs):
        """Perform operations on multiple selected items"""
        results = []
        for item in items:
            try:
                if operation == "copy":
                    result = self.copy(item['src'], item['dst'], **kwargs)
                elif operation == "move":
                    result = self.move(item['src'], item['dst'])
                elif operation == "delete":
                    result = self.delete(item['path'])
                elif operation == "rename":
                    result = self.rename(item['src'], item['new_name'])
                
                results.append({'item': item, 'success': True, 'error': None})
            except FileOperationError as e:
                results.append({'item': item, 'success': False, 'error': str(e)})
        
        return results
    
    def get_file_info(self, path):
        """Get detailed file information"""
        try:
            path = self.validate_path(path)
            stat = os.stat(path)
            
            return {
                'name': os.path.basename(path),
                'path': path,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'permissions': oct(stat.st_mode)[-3:],
                'is_dir': os.path.isdir(path),
                'is_link': os.path.islink(path),
                'mime_type': self._get_mime_type(path)
            }
        except Exception as e:
            raise FileOperationError(f"Cannot get file info: {str(e)}")
    
    def _get_mime_type(self, path):
        """Simple MIME type detection"""
        ext = os.path.splitext(path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.mp3': 'audio/mpeg', '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska', '.avi': 'video/x-msvideo',
            '.zip': 'application/zip', '.tar': 'application/x-tar',
            '.gz': 'application/gzip'
        }
        return mime_types.get(ext, 'application/octet-stream')