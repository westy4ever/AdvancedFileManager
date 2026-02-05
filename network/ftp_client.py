# -*- coding: utf-8 -*-
import ftplib
import os
from io import BytesIO

class FTPClient:
    def __init__(self):
        self.ftp = None
        self.connected = False
        self.host = None
        self.current_path = '/'
    
    def connect(self, host, port=21, username='anonymous', password='', timeout=30):
        """Connect to FTP server"""
        try:
            self.ftp = ftplib.FTP(timeout=timeout)
            self.ftp.connect(host, port)
            self.ftp.login(username, password)
            self.connected = True
            self.host = host
            return True
        except Exception as e:
            raise FTPError(f"FTP connection failed: {str(e)}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass
        self.connected = False
        self.ftp = None
    
    def list_directory(self, path=None):
        """
        List directory contents
        
        Returns:
            list: List of file/directory dictionaries
        """
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            if path:
                self.ftp.cwd(path)
                self.current_path = path
            
            items = []
            self.ftp.retrlines('LIST', items.append)
            
            # Parse LIST output
            parsed_items = []
            for item in items:
                parts = item.split()
                if len(parts) >= 9:
                    is_dir = parts[0].startswith('d')
                    name = ' '.join(parts[8:])
                    size = parts[4] if not is_dir else '0'
                    
                    parsed_items.append({
                        'name': name,
                        'is_dir': is_dir,
                        'size': size,
                        'permissions': parts[0],
                        'date': ' '.join(parts[5:8])
                    })
            
            return parsed_items
            
        except Exception as e:
            raise FTPError(f"FTP list failed: {str(e)}")
    
    def download_file(self, remote_path, local_path, callback=None):
        """Download file from FTP"""
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            with open(local_path, 'wb') as f:
                if callback:
                    self.ftp.retrbinary(f'RETR {remote_path}', 
                                      lambda data: (f.write(data), callback(len(data))))
                else:
                    self.ftp.retrbinary(f'RETR {remote_path}', f.write)
            return True
        except Exception as e:
            raise FTPError(f"FTP download failed: {str(e)}")
    
    def upload_file(self, local_path, remote_path, callback=None):
        """Upload file to FTP"""
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            with open(local_path, 'rb') as f:
                if callback:
                    # Calculate file size for progress
                    f.seek(0, 2)
                    total_size = f.tell()
                    f.seek(0)
                    
                    def upload_callback(data):
                        callback(len(data))
                        return data
                    
                    self.ftp.storbinary(f'STOR {remote_path}', f, callback=upload_callback)
                else:
                    self.ftp.storbinary(f'STOR {remote_path}', f)
            return True
        except Exception as e:
            raise FTPError(f"FTP upload failed: {str(e)}")
    
    def delete_file(self, remote_path):
        """Delete file on FTP server"""
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            self.ftp.delete(remote_path)
            return True
        except Exception as e:
            raise FTPError(f"FTP delete failed: {str(e)}")
    
    def make_directory(self, path):
        """Create directory on FTP server"""
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            self.ftp.mkd(path)
            return True
        except Exception as e:
            raise FTPError(f"FTP mkdir failed: {str(e)}")
    
    def remove_directory(self, path):
        """Remove directory on FTP server"""
        if not self.connected:
            raise FTPError("Not connected")
        
        try:
            self.ftp.rmd(path)
            return True
        except Exception as e:
            raise FTPError(f"FTP rmdir failed: {str(e)}")

class FTPError(Exception):
    """FTP operation error"""
    pass