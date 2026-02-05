# -*- coding: utf-8 -*-
import os
import json
from enum import Enum

class RemoteType(Enum):
    FTP = "ftp"
    SFTP = "sftp"
    WEBDAV = "webdav"
    NFS = "nfs"
    SMB = "smb"

class RemoteConnection:
    """Represents a saved remote connection"""
    
    def __init__(self, name, remote_type, host, port=None, username=None, password=None, 
                 path='/', options=None):
        self.name = name
        self.type = remote_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password  # In production, use encryption!
        self.path = path
        self.options = options or {}
        self.client = None
        self.connected = False
    
    def connect(self):
        """Establish connection"""
        if self.type == RemoteType.FTP:
            from .ftp_client import FTPClient
            self.client = FTPClient()
            self.client.connect(
                self.host,
                self.port or 21,
                self.username,
                self.password
            )
        
        elif self.type == RemoteType.SFTP:
            from .sftp_client import SFTPClient
            self.client = SFTPClient()
            self.client.connect(
                self.host,
                self.port or 22,
                self.username,
                self.password
            )
        
        elif self.type == RemoteType.WEBDAV:
            from .webdav_client import WebDAVClient
            self.client = WebDAVClient()
            url = f"{'https' if self.options.get('ssl') else 'http'}://{self.host}:{self.port or 80}{self.path}"
            self.client.connect(url, self.username, self.password)
        
        self.connected = True
        return True
    
    def disconnect(self):
        """Close connection"""
        if self.client:
            self.client.disconnect()
            self.client = None
        self.connected = False
    
    def list_directory(self, path=None):
        """List directory contents"""
        if not self.connected:
            self.connect()
        return self.client.list_directory(path)
    
    def to_dict(self):
        """Serialize to dictionary"""
        return {
            'name': self.name,
            'type': self.type.value,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,  # Encrypt in production!
            'path': self.path,
            'options': self.options
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            name=data['name'],
            remote_type=RemoteType(data['type']),
            host=data['host'],
            port=data.get('port'),
            username=data.get('username'),
            password=data.get('password'),
            path=data.get('path', '/'),
            options=data.get('options', {})
        )

class RemoteBrowser:
    """
    Manage remote connections and browsing
    """
    
    CONFIG_FILE = "/etc/enigma2/advancedfilemanager_remotes.json"
    
    def __init__(self):
        self.connections = {}
        self.active_connection = None
        self.load_connections()
    
    def add_connection(self, connection):
        """
        Add new remote connection
        
        Args:
            connection: RemoteConnection object
        """
        self.connections[connection.name] = connection
        self.save_connections()
    
    def remove_connection(self, name):
        """Remove saved connection"""
        if name in self.connections:
            # Disconnect if active
            if self.active_connection == self.connections[name]:
                self.active_connection.disconnect()
                self.active_connection = None
            
            del self.connections[name]
            self.save_connections()
    
    def get_connection(self, name):
        """Get connection by name"""
        return self.connections.get(name)
    
    def list_connections(self):
        """List all saved connections"""
        return list(self.connections.values())
    
    def connect(self, name):
        """
        Connect to remote server
        
        Args:
            name: Connection name
        
        Returns:
            RemoteConnection: Connected client
        """
        if name not in self.connections:
            raise RemoteBrowserError(f"Connection not found: {name}")
        
        conn = self.connections[name]
        
        # Disconnect current if different
        if self.active_connection and self.active_connection != conn:
            self.active_connection.disconnect()
        
        if not conn.connected:
            conn.connect()
        
        self.active_connection = conn
        return conn
    
    def disconnect(self, name=None):
        """Disconnect from remote"""
        if name:
            if name in self.connections:
                self.connections[name].disconnect()
                if self.active_connection == self.connections[name]:
                    self.active_connection = None
        else:
            # Disconnect all
            for conn in self.connections.values():
                conn.disconnect()
            self.active_connection = None
    
    def browse(self, path=None):
        """
        Browse current remote directory
        
        Args:
            path: Directory path (None for current)
        
        Returns:
            list: Directory contents
        """
        if not self.active_connection:
            raise RemoteBrowserError("No active connection")
        
        return self.active_connection.list_directory(path)
    
    def transfer_file(self, remote_path, local_path, direction='download', callback=None):
        """
        Transfer file between local and remote
        
        Args:
            remote_path: Path on remote server
            local_path: Path on local system
            direction: 'download' or 'upload'
            callback: Progress callback function
        """
        if not self.active_connection:
            raise RemoteBrowserError("No active connection")
        
        client = self.active_connection.client
        
        if direction == 'download':
            return client.download_file(remote_path, local_path, callback)
        else:
            return client.upload_file(local_path, remote_path, callback)
    
    def save_connections(self):
        """Save connections to file"""
        try:
            data = {name: conn.to_dict() for name, conn in self.connections.items()}
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving connections: {e}")
    
    def load_connections(self):
        """Load connections from file"""
        if not os.path.exists(self.CONFIG_FILE):
            return
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                data = json.load(f)
            
            for name, conn_data in data.items():
                self.connections[name] = RemoteConnection.from_dict(conn_data)
                
        except Exception as e:
            print(f"Error loading connections: {e}")

class RemoteBrowserError(Exception):
    """Remote browser error"""
    pass