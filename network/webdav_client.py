# -*- coding: utf-8 -*-
import os
import io
from urllib.parse import urljoin, urlparse, quote
from xml.etree import ElementTree as ET

class WebDAVClient:
    """
    WebDAV client for cloud storage access
    """
    
    DAV_NS = "{DAV:}"
    
    def __init__(self):
        self.base_url = None
        self.username = None
        self.password = None
        self.connected = False
        self.current_path = '/'
        self.session = None
    
    def connect(self, url, username=None, password=None, timeout=30):
        """
        Connect to WebDAV server
        
        Args:
            url: WebDAV server URL (e.g., https://example.com/webdav)
            username: Authentication username
            password: Authentication password
            timeout: Request timeout
        """
        try:
            import requests
            
            self.session = requests.Session()
            self.session.timeout = timeout
            
            if username and password:
                self.session.auth = (username, password)
            
            # Test connection with PROPFIND on root
            response = self.session.request('PROPFIND', url, headers={'Depth': '0'})
            
            if response.status_code in [200, 207]:
                self.base_url = url.rstrip('/')
                self.username = username
                self.connected = True
                self.current_path = '/'
                return True
            else:
                raise WebDAVError(f"Connection failed: HTTP {response.status_code}")
                
        except ImportError:
            raise WebDAVError("Requests library not installed. Install python3-requests")
        except Exception as e:
            raise WebDAVError(f"WebDAV connection failed: {str(e)}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.session:
            self.session.close()
            self.session = None
        self.connected = False
    
    def list_directory(self, path=None):
        """
        List directory contents using PROPFIND
        
        Returns:
            list: List of file/directory dictionaries
        """
        if not self.connected:
            raise WebDAVError("Not connected")
        
        target_path = path or self.current_path
        url = self._make_url(target_path)
        
        try:
            headers = {'Depth': '1'}  # List immediate children
            response = self.session.request('PROPFIND', url, headers=headers)
            
            if response.status_code not in [200, 207]:
                raise WebDAVError(f"PROPFIND failed: HTTP {response.status_code}")
            
            return self._parse_propfind(response.content)
            
        except Exception as e:
            raise WebDAVError(f"List directory failed: {str(e)}")
    
    def _parse_propfind(self, xml_content):
        """Parse WebDAV PROPFIND response"""
        items = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for response in root.findall(f'{self.DAV_NS}response'):
                href = response.find(f'{self.DAV_NS}href')
                if href is None:
                    continue
                
                href_text = href.text
                
                # Skip current directory entry
                if href_text.endswith('/'):
                    name = href_text.rstrip('/').split('/')[-1]
                    if not name or name == self.current_path.strip('/').split('/')[-1]:
                        continue
                
                propstat = response.find(f'{self.DAV_NS}propstat')
                if propstat is None:
                    continue
                
                prop = propstat.find(f'{self.DAV_NS}prop')
                if prop is None:
                    continue
                
                # Parse properties
                resourcetype = prop.find(f'{self.DAV_NS}resourcetype')
                is_dir = resourcetype.find(f'{self.DAV_NS}collection') is not None
                
                getcontentlength = prop.find(f'{self.DAV_NS}getcontentlength')
                size = int(getcontentlength.text) if getcontentlength is not None else 0
                
                getlastmodified = prop.find(f'{self.DAV_NS}getlastmodified')
                modified = getlastmodified.text if getlastmodified is not None else ''
                
                displayname = prop.find(f'{self.DAV_NS}displayname')
                name = displayname.text if displayname is not None else os.path.basename(href_text)
                
                items.append({
                    'name': name,
                    'path': href_text,
                    'is_dir': is_dir,
                    'size': size,
                    'modified': modified
                })
            
            return items
            
        except Exception as e:
            raise WebDAVError(f"Parse error: {str(e)}")
    
    def download_file(self, remote_path, local_path, callback=None):
        """Download file from WebDAV"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        url = self._make_url(remote_path)
        
        try:
            response = self.session.get(url, stream=True)
            
            if response.status_code != 200:
                raise WebDAVError(f"Download failed: HTTP {response.status_code}")
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if callback and total_size > 0:
                            callback(downloaded, total_size)
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Download failed: {str(e)}")
    
    def upload_file(self, local_path, remote_path, callback=None):
        """Upload file to WebDAV"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        url = self._make_url(remote_path)
        total_size = os.path.getsize(local_path)
        
        try:
            with open(local_path, 'rb') as f:
                if callback:
                    class CallbackWrapper:
                        def __init__(self, file_obj, callback, total):
                            self.file_obj = file_obj
                            self.callback = callback
                            self.total = total
                            self.transferred = 0
                        
                        def read(self, size):
                            data = self.file_obj.read(size)
                            self.transferred += len(data)
                            self.callback(self.transferred, self.total)
                            return data
                    
                    wrapper = CallbackWrapper(f, callback, total_size)
                    response = self.session.put(url, data=wrapper)
                else:
                    response = self.session.put(url, data=f)
            
            if response.status_code not in [200, 201, 204]:
                raise WebDAVError(f"Upload failed: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Upload failed: {str(e)}")
    
    def delete(self, remote_path):
        """Delete file or directory"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        url = self._make_url(remote_path)
        
        try:
            response = self.session.delete(url)
            
            if response.status_code not in [200, 204]:
                raise WebDAVError(f"Delete failed: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Delete failed: {str(e)}")
    
    def create_directory(self, path):
        """Create directory (collection)"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        url = self._make_url(path)
        
        try:
            response = self.session.request('MKCOL', url)
            
            if response.status_code not in [200, 201]:
                raise WebDAVError(f"Create directory failed: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Create directory failed: {str(e)}")
    
    def move(self, src_path, dst_path):
        """Move/rename file or directory"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        src_url = self._make_url(src_path)
        dst_url = self._make_url(dst_path)
        
        try:
            headers = {'Destination': dst_url}
            response = self.session.request('MOVE', src_url, headers=headers)
            
            if response.status_code not in [200, 201, 204]:
                raise WebDAVError(f"Move failed: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Move failed: {str(e)}")
    
    def copy(self, src_path, dst_path):
        """Copy file or directory"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        src_url = self._make_url(src_path)
        dst_url = self._make_url(dst_path)
        
        try:
            headers = {'Destination': dst_url}
            response = self.session.request('COPY', src_url, headers=headers)
            
            if response.status_code not in [200, 201, 204]:
                raise WebDAVError(f"Copy failed: HTTP {response.status_code}")
            
            return True
            
        except Exception as e:
            raise WebDAVError(f"Copy failed: {str(e)}")
    
    def exists(self, path):
        """Check if resource exists"""
        if not self.connected:
            raise WebDAVError("Not connected")
        
        url = self._make_url(path)
        
        try:
            response = self.session.request('PROPFIND', url, headers={'Depth': '0'})
            return response.status_code in [200, 207]
        except:
            return False
    
    def _make_url(self, path):
        """Construct full URL from path"""
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # URL encode path components
        encoded_path = '/'.join(quote(segment, safe='') for segment in path.split('/'))
        
        return self.base_url + encoded_path

class WebDAVError(Exception):
    """WebDAV operation error"""
    pass