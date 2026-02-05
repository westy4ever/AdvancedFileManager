# -*- coding: utf-8 -*-
import os
import shutil
import time
import json
from datetime import datetime, timedelta
from Components.config import config

# Import security manager
try:
    from ..utils.security import SecurityManager, SecurityError
    HAS_SECURITY = True
except ImportError:
    HAS_SECURITY = False

class TrashManager:
    """
    Trash/Recycle Bin functionality for safe file deletion
    """
    
    TRASH_INFO_FILE = ".trashinfo"
    
    def __init__(self, trash_path=None):
        self.trash_path = trash_path or config.plugins.advancedfilemanager.trash_path.value
        if HAS_SECURITY:
            self.security = SecurityManager()
        else:
            self.security = None
        self.ensure_trash_exists()
    
    def ensure_trash_exists(self):
        """Create trash directory if it doesn't exist"""
        if not os.path.exists(self.trash_path):
            try:
                os.makedirs(self.trash_path, mode=0o755)
            except Exception as e:
                raise TrashError(f"Cannot create trash directory: {e}")
    
    def trash(self, path):
        """
        Move file or directory to trash
        
        Args:
            path: Path to file/directory to trash
        
        Returns:
            str: Path in trash or None on failure
        """
        if not os.path.exists(path):
            raise TrashError(f"Path does not exist: {path}")
        
        # Security validation
        if self.security:
            try:
                validated_path = self.security.validate_path(path)
                is_safe, reason = self.security.is_safe_operation(path, operation='delete')
                if not is_safe:
                    raise TrashError(f"Security check failed: {reason}")
            except SecurityError as e:
                raise TrashError(f"Security error: {e}")
        
        # Generate unique name in trash
        original_name = os.path.basename(path)
        trash_name = self._generate_trash_name(original_name)
        trash_item_path = os.path.join(self.trash_path, trash_name)
        
        try:
            # Move to trash
            shutil.move(path, trash_item_path)
            
            # Create metadata file
            self._create_trash_info(trash_name, path)
            
            return trash_item_path
            
        except Exception as e:
            raise TrashError(f"Failed to move to trash: {e}")
    
    def restore(self, trash_name):
        """
        Restore file from trash to original location
        
        Args:
            trash_name: Name of item in trash
        
        Returns:
            str: Restored path or None on failure
        """
        trash_item_path = os.path.join(self.trash_path, trash_name)
        
        if not os.path.exists(trash_item_path):
            raise TrashError(f"Item not found in trash: {trash_name}")
        
        # Read original path from metadata
        original_path = self._get_original_path(trash_name)
        
        if not original_path:
            raise TrashError(f"Cannot determine original path for: {trash_name}")
        
        # Security validation of restore destination
        if self.security:
            try:
                validated_path = self.security.validate_path(original_path, allow_write=True)
                original_path = validated_path
            except SecurityError as e:
                raise TrashError(f"Cannot restore to forbidden location: {e}")
        
        # Check if original location exists
        if os.path.exists(original_path):
            # Generate unique name
            original_path = self._generate_unique_name(original_path)
        
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(original_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            
            # Move back to original location
            shutil.move(trash_item_path, original_path)
            
            # Remove metadata file
            info_path = os.path.join(self.trash_path, f"{trash_name}{self.TRASH_INFO_FILE}")
            if os.path.exists(info_path):
                os.remove(info_path)
            
            return original_path
            
        except Exception as e:
            raise TrashError(f"Failed to restore from trash: {e}")
    
    def delete_permanently(self, trash_name):
        """
        Permanently delete item from trash
        
        Args:
            trash_name: Name of item in trash
        
        Returns:
            bool: True on success
        """
        trash_item_path = os.path.join(self.trash_path, trash_name)
        
        if not os.path.exists(trash_item_path):
            raise TrashError(f"Item not found in trash: {trash_name}")
        
        try:
            if os.path.isdir(trash_item_path):
                shutil.rmtree(trash_item_path)
            else:
                os.remove(trash_item_path)
            
            # Remove metadata file
            info_path = os.path.join(self.trash_path, f"{trash_name}{self.TRASH_INFO_FILE}")
            if os.path.exists(info_path):
                os.remove(info_path)
            
            return True
            
        except Exception as e:
            raise TrashError(f"Failed to delete permanently: {e}")
    
    def list_trash(self):
        """
        List all items in trash
        
        Returns:
            list: List of dictionaries with trash item info
        """
        items = []
        
        try:
            for entry in os.listdir(self.trash_path):
                if entry.endswith(self.TRASH_INFO_FILE):
                    continue
                
                item_path = os.path.join(self.trash_path, entry)
                info = self._get_trash_info(entry)
                
                try:
                    stat = os.stat(item_path)
                    
                    items.append({
                        'trash_name': entry,
                        'original_path': info.get('original_path', 'Unknown'),
                        'deleted_date': info.get('deletion_date', 'Unknown'),
                        'size': stat.st_size,
                        'is_dir': os.path.isdir(item_path),
                        'path': item_path
                    })
                except (OSError, IOError):
                    continue
            
            # Sort by deletion date (newest first)
            items.sort(key=lambda x: x['deleted_date'], reverse=True)
            
        except Exception as e:
            print(f"Error listing trash: {e}")
        
        return items
    
    def empty_trash(self):
        """
        Empty trash completely
        
        Returns:
            tuple: (success_count, failed_items)
        """
        items = self.list_trash()
        success = 0
        failed = []
        
        for item in items:
            try:
                self.delete_permanently(item['trash_name'])
                success += 1
            except Exception as e:
                failed.append((item['trash_name'], str(e)))
        
        return success, failed
    
    def auto_cleanup(self, max_age_days=30):
        """
        Automatically delete old items from trash
        
        Args:
            max_age_days: Maximum age in days before auto-deletion
        
        Returns:
            tuple: (deleted_count, failed_items)
        """
        items = self.list_trash()
        deleted = 0
        failed = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for item in items:
            try:
                deletion_date_str = item['deleted_date']
                if deletion_date_str != 'Unknown':
                    deletion_date = datetime.strptime(deletion_date_str, "%Y-%m-%d %H:%M:%S")
                    if deletion_date < cutoff_date:
                        self.delete_permanently(item['trash_name'])
                        deleted += 1
            except Exception as e:
                failed.append((item['trash_name'], str(e)))
        
        return deleted, failed
    
    def get_size(self):
        """Get total size of trash in bytes"""
        total_size = 0
        
        try:
            for entry in os.listdir(self.trash_path):
                if entry.endswith(self.TRASH_INFO_FILE):
                    continue
                
                item_path = os.path.join(self.trash_path, entry)
                if os.path.isdir(item_path):
                    for dirpath, dirnames, filenames in os.walk(item_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            try:
                                total_size += os.path.getsize(fp)
                            except:
                                continue
                else:
                    try:
                        total_size += os.path.getsize(item_path)
                    except:
                        continue
                    
        except Exception as e:
            print(f"Error calculating trash size: {e}")
        
        return total_size
    
    def _generate_trash_name(self, original_name):
        """Generate unique name for trash"""
        timestamp = int(time.time())
        base_name, ext = os.path.splitext(original_name)
        
        # Sanitize base name
        base_name = base_name.replace('/', '_').replace('\\', '_')
        
        return f"{base_name}_{timestamp}{ext}"
    
    def _create_trash_info(self, trash_name, original_path):
        """Create metadata file for trashed item"""
        info = {
            'original_path': original_path,
            'deletion_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'trash_name': trash_name
        }
        
        info_path = os.path.join(self.trash_path, f"{trash_name}{self.TRASH_INFO_FILE}")
        
        try:
            with open(info_path, 'w') as f:
                json.dump(info, f)
        except Exception as e:
            print(f"Error creating trash info: {e}")
    
    def _get_trash_info(self, trash_name):
        """Read metadata for trashed item"""
        info_path = os.path.join(self.trash_path, f"{trash_name}{self.TRASH_INFO_FILE}")
        
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {}
    
    def _get_original_path(self, trash_name):
        """Get original path from metadata"""
        info = self._get_trash_info(trash_name)
        return info.get('original_path')
    
    def _generate_unique_name(self, path):
        """Generate unique name if target exists"""
        if not os.path.exists(path):
            return path
        
        base, ext = os.path.splitext(path)
        counter = 1
        
        while True:
            new_path = f"{base}_restored_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1
            if counter > 1000:  # Prevent infinite loop
                raise TrashError("Cannot generate unique filename")

class TrashError(Exception):
    """Trash operation error"""
    pass