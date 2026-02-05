# -*- coding: utf-8 -*-
import os
import socket
from functools import partial

class SFTPClient:
    """
    Secure FTP client using SSH/SFTP protocol
    Requires paramiko library (python3-paramiko)
    """
    
    def __init__(self):
        self.ssh = None
        self.sftp = None
        self.connected = False
        self.host = None
        self.current_path = '/'
        self.username = None
    
    def connect(self, host, port=22, username=None, password=None, key_filename=None, timeout=30):
        """
        Connect to SFTP server
        
        Args:
            host: Server hostname or IP
            port: SSH port (default 22)
            username: SSH username
            password: SSH password (or None for key auth)
            key_filename: Path to private key file
            timeout: Connection timeout
        
        Returns:
            bool: True on success
        """
        try:
            import paramiko
            
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': timeout,
                'look_for_keys': True
            }
            
            if password:
                connect_kwargs['password'] = password
            if key_filename:
                connect_kwargs['key_filename'] = key_filename
            
            self.ssh.connect(**connect_kwargs)
            self.sftp = self.ssh.open_sftp()
            
            self.connected = True
            self.host = host
            self.username = username
            self.current_path = self.sftp.normalize('.')
            
            return True
            
        except ImportError:
            raise SFTPError("Paramiko library not installed. Install python3-paramiko")
        except Exception as e:
            raise SFTPError(f"SFTP connection failed: {str(e)}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
            self.sftp = None
        
        if self.ssh:
            try:
                self.ssh.close()
            except:
                pass
            self.ssh = None
        
        self.connected = False
    
    def list_directory(self, path=None):
        """
        List directory contents
        
        Returns:
            list: List of file/directory dictionaries
        """
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            if path:
                self.sftp.chdir(path)
                self.current_path = self.sftp.normalize('.')
            
            items = []
            for entry in self.sftp.listdir_attr('.'):
                items.append({
                    'name': entry.filename,
                    'is_dir': entry.st_mode & 0o40000 == 0o40000,  # S_IFDIR
                    'size': entry.st_size,
                    'permissions': oct(entry.st_mode)[-3:],
                    'modified': entry.st_mtime,
                    'owner': entry.st_uid,
                    'group': entry.st_gid
                })
            
            return items
            
        except Exception as e:
            raise SFTPError(f"List directory failed: {str(e)}")
    
    def change_directory(self, path):
        """Change working directory"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            self.sftp.chdir(path)
            self.current_path = self.sftp.normalize('.')
            return self.current_path
        except Exception as e:
            raise SFTPError(f"Change directory failed: {str(e)}")
    
    def get_current_directory(self):
        """Get current working directory"""
        return self.current_path
    
    def download_file(self, remote_path, local_path, callback=None):
        """
        Download file from SFTP server
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
            callback: Progress callback function(bytes_transferred, total_bytes)
        """
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            # Get file size for progress
            remote_stat = self.sftp.stat(remote_path)
            total_size = remote_stat.st_size
            
            if callback:
                def progress_callback(bytes_transferred, total):
                    callback(bytes_transferred, total_size)
                
                self.sftp.get(remote_path, local_path, callback=progress_callback)
            else:
                self.sftp.get(remote_path, local_path)
            
            return True
            
        except Exception as e:
            raise SFTPError(f"Download failed: {str(e)}")
    
    def upload_file(self, local_path, remote_path, callback=None):
        """
        Upload file to SFTP server
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            callback: Progress callback function(bytes_transferred, total_bytes)
        """
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            total_size = os.path.getsize(local_path)
            
            if callback:
                def progress_callback(bytes_transferred, total):
                    callback(bytes_transferred, total_size)
                
                self.sftp.put(local_path, remote_path, callback=progress_callback)
            else:
                self.sftp.put(local_path, remote_path)
            
            return True
            
        except Exception as e:
            raise SFTPError(f"Upload failed: {str(e)}")
    
    def delete_file(self, remote_path):
        """Delete file on server"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            self.sftp.remove(remote_path)
            return True
        except Exception as e:
            raise SFTPError(f"Delete failed: {str(e)}")
    
    def delete_directory(self, remote_path):
        """Remove directory on server"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            self.sftp.rmdir(remote_path)
            return True
        except Exception as e:
            raise SFTPError(f"Remove directory failed: {str(e)}")
    
    def create_directory(self, path):
        """Create directory on server"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            self.sftp.mkdir(path)
            return True
        except Exception as e:
            raise SFTPError(f"Create directory failed: {str(e)}")
    
    def rename(self, old_path, new_path):
        """Rename file or directory"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            self.sftp.rename(old_path, new_path)
            return True
        except Exception as e:
            raise SFTPError(f"Rename failed: {str(e)}")
    
    def stat(self, remote_path):
        """Get file statistics"""
        if not self.connected:
            raise SFTPError("Not connected")
        
        try:
            s = self.sftp.stat(remote_path)
            return {
                'size': s.st_size,
                'uid': s.st_uid,
                'gid': s.st_gid,
                'mode': s.st_mode,
                'atime': s.st_atime,
                'mtime': s.st_mtime
            }
        except Exception as e:
            raise SFTPError(f"Stat failed: {str(e)}")
    
    def is_connected(self):
        """Check connection status"""
        if not self.ssh or not self.sftp:
            return False
        
        # Test connection with noop
        try:
            self.sftp.stat('.')
            return True
        except:
            self.connected = False
            return False

class SFTPError(Exception):
    """SFTP operation error"""
    pass