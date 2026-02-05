# -*- coding: utf-8 -*-
import os
import shutil
import threading
from enigma import eTimer
from Components.config import config

# Import security manager
from ..utils.security import SecurityManager, SecurityError

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
        self.security = SecurityManager()
        
    def validate_path(self, path):
        """Security: Validate and sanitize paths using SecurityManager"""
        try:
            return self.security.validate_path(path)
        except SecurityError as e:
            raise PermissionError(str(e))
    
    def copy(self, src, dst, overwrite=False):
        """Copy files or directories with progress tracking"""
        try:
            src = self.validate_path(src)
            dst = self.validate_path(dst)
            
            if not os.path.exists(src):
                raise PathNotFoundError(f"Source not found: {src}")
            
            if os.path.exists(dst) and not overwrite:
                raise FileOperationError(f"Destination exists: {dst}")
            
            # Additional security check
            is_safe, reason = self.security.is_safe_operation(src, dst, 'copy')
            if not is_safe:
                raise PermissionError(reason)
            
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dst)
                
            return True
            
        except SecurityError as e:
            raise PermissionError(f"Security error: {e}")
        except Exception as e:
            raise FileOperationError(f"Copy failed: {str(e)}")
    
    def move(self, src, dst):
        """Move files or directories"""
        try:
            src = self.validate_path(src)
            dst = self.validate_path(dst)
            
            # Security check
            is_safe, reason = self.security.is_safe_operation(src, dst, 'move')
            if not is_safe:
                raise PermissionError(reason)
            
            shutil.move(src, dst)
            return True
        except SecurityError as e:
            raise PermissionError(f"Security error: {e}")
        except Exception as e:
            raise FileOperationError(f"Move failed: {str(e)}")
    
    def rename(self, src, new_name):
        """Rename file or directory"""
        try:
            src = self.validate_path(src)
            dst = os.path.join(os.path.dirname(src), new_name)
            dst = self.validate_path(dst)
            
            # Security check
            is_safe, reason = self.security.is_safe_operation(src, dst, 'move')
            if not is_safe:
                raise PermissionError(reason)
            
            os.rename(src, dst)
            return True
        except SecurityError as e:
            raise PermissionError(f"Security error: {e}")
        except Exception as e:
            raise FileOperationError(f"Rename failed: {str(e)}")
    
    def delete(self, path, use_trash=None):
        """Delete with optional trash support"""
        try:
            path = self.validate_path(path)
            
            # Security check
            is_safe, reason = self.security.is_safe_operation(path, operation='delete')
            if not is_safe:
                raise PermissionError(reason)
            
            if use_trash is None:
                use_trash = config.plugins.advancedfilemanager.use_trash.value
            
            if use_trash:
                try:
                    from .trash_manager import TrashManager
                    trash = TrashManager()
                    return trash.trash(path)
                except ImportError:
                    # Fall back to direct delete if trash not available
                    use_trash = False
            
            if not use_trash:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return True
                
        except SecurityError as e:
            raise PermissionError(f"Security error: {e}")
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
        except SecurityError as e:
            raise PermissionError(f"Security error: {e}")
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