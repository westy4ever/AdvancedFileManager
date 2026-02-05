# -*- coding: utf-8 -*-
import os
import re

class SecurityManager:
    """Security utilities for path validation and sanitization"""
    
    # Paths that should never be accessed
    FORBIDDEN_PATHS = [
        '/bin', '/sbin', '/usr/bin', '/usr/sbin',
        '/etc', '/proc', '/sys', '/dev',
        '/lib', '/lib64', '/usr/lib', '/usr/lib64',
        '/boot', '/var/log', '/var/spool'
    ]
    
    # Dangerous characters in filenames
    DANGEROUS_CHARS = ['<', '>', ':', '"', '|', '?', '*', '\x00']
    
    def validate_path(self, path, allow_write=False):
        """
        Validate path for security issues
        
        Args:
            path: Path to validate
            allow_write: Whether write operations are allowed
        
        Returns:
            Sanitized absolute path
        
        Raises:
            SecurityError: If path is invalid or forbidden
        """
        if not path or not isinstance(path, str):
            raise SecurityError("Invalid path type")
        
        # Normalize path
        try:
            real_path = os.path.realpath(path)
        except Exception as e:
            raise SecurityError(f"Path resolution failed: {e}")
        
        # Check for directory traversal
        if '..' in path.split(os.sep):
            # Additional check: ensure resolved path is within allowed base
            pass  # realpath handles this
        
        # Check forbidden paths
        for forbidden in self.FORBIDDEN_PATHS:
            if real_path.startswith(forbidden):
                raise SecurityError(f"Access denied to system path: {forbidden}")
        
        # Check for symlinks pointing to forbidden areas
        if os.path.islink(path):
            link_target = os.readlink(path)
            if not link_target.startswith('/'):
                link_target = os.path.join(os.path.dirname(path), link_target)
            
            # Recursively validate symlink target
            try:
                self.validate_path(link_target, allow_write)
            except SecurityError:
                raise SecurityError("Symlink points to forbidden location")
        
        return real_path
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe usage"""
        if not filename:
            return "unnamed"
        
        # Remove dangerous characters
        for char in self.DANGEROUS_CHARS:
            filename = filename.replace(char, '_')
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Prevent reserved names (Windows compatibility)
        reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                   'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                   'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 
                   'LPT7', 'LPT8', 'LPT9']
        
        name_upper = filename.upper()
        if name_upper in reserved:
            filename = f"_{filename}"
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        # Prevent empty filename
        if not filename or filename == '.':
            filename = 'unnamed'
        
        return filename
    
    def check_permissions(self, path, operation='read'):
        """
        Check if operation is permitted on path
        
        Args:
            path: Path to check
            operation: 'read', 'write', 'execute', 'delete'
        
        Returns:
            bool: True if permitted
        """
        try:
            path = self.validate_path(path, allow_write=(operation=='write'))
            
            if operation == 'read':
                return os.access(path, os.R_OK)
            elif operation == 'write':
                return os.access(path, os.W_OK)
            elif operation == 'execute':
                return os.access(path, os.X_OK)
            elif operation == 'delete':
                # Need write permission on parent directory
                parent = os.path.dirname(path)
                return os.access(parent, os.W_OK)
            
            return False
            
        except SecurityError:
            return False
    
    def is_safe_operation(self, src, dst=None, operation='copy'):
        """
        Check if file operation is safe to perform
        
        Args:
            src: Source path
            dst: Destination path (if applicable)
            operation: Type of operation
        
        Returns:
            (bool, str): (is_safe, reason_if_unsafe)
        """
        try:
            # Validate source
            src_real = self.validate_path(src)
            
            # Check source permissions
            if not self.check_permissions(src_real, 'read'):
                return False, "No read permission on source"
            
            # Validate and check destination if provided
            if dst:
                dst_real = self.validate_path(dst, allow_write=True)
                
                if not self.check_permissions(os.path.dirname(dst_real), 'write'):
                    return False, "No write permission on destination"
                
                # Prevent overwriting system files
                if os.path.exists(dst_real):
                    for forbidden in self.FORBIDDEN_PATHS:
                        if dst_real.startswith(forbidden):
                            return False, "Cannot overwrite system file"
            
            # Specific checks for operations
            if operation == 'delete':
                if not self.check_permissions(src_real, 'delete'):
                    return False, "No permission to delete"
            
            return True, "Safe"
            
        except SecurityError as e:
            return False, str(e)

class SecurityError(Exception):
    """Security violation exception"""
    pass