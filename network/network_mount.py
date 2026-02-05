# -*- coding: utf-8 -*-
import os
import subprocess
import re
import json
from enum import Enum

class MountType(Enum):
    NFS = "nfs"
    CIFS = "cifs"
    SMB = "smb"
    AUTO = "auto"

class NetworkMountManager:
    """
    Manage network mounts (NFS, SMB/CIFS)
    Uses system mount commands
    """
    
    MOUNT_BASE = "/media/net"
    MOUNT_INFO_FILE = "/etc/enigma2/advancedfilemanager_mounts.json"
    
    def __init__(self):
        self.ensure_mount_base()
        self.mounts = self.load_mounts()
    
    def ensure_mount_base(self):
        """Create mount base directory if needed"""
        if not os.path.exists(self.MOUNT_BASE):
            try:
                os.makedirs(self.MOUNT_BASE, mode=0o755)
            except Exception as e:
                raise MountError(f"Cannot create mount base: {e}")
    
    def mount(self, host, share, mount_type=MountType.AUTO, username=None, password=None, options=None, mount_name=None):
        """
        Mount network share
        
        Args:
            host: Server hostname or IP
            share: Share name or path
            mount_type: Type of mount (NFS, CIFS, SMB, AUTO)
            username: Username for authentication
            password: Password for authentication
            options: Additional mount options dict
            mount_name: Local mount point name (auto-generated if None)
        
        Returns:
            str: Mount point path
        """
        # Auto-detect mount type if not specified
        if mount_type == MountType.AUTO:
            mount_type = self._detect_mount_type(host, share)
        
        # Generate mount point name
        if not mount_name:
            mount_name = f"{host}_{share.replace('/', '_')}"
        
        mount_point = os.path.join(self.MOUNT_BASE, mount_name)
        
        # Create mount point
        if not os.path.exists(mount_point):
            try:
                os.makedirs(mount_point, mode=0o755)
            except Exception as e:
                raise MountError(f"Cannot create mount point: {e}")
        
        # Check if already mounted
        if self.is_mounted(mount_point):
            return mount_point
        
        # Build mount command
        if mount_type == MountType.NFS:
            cmd = self._build_nfs_mount(host, share, mount_point, options)
        elif mount_type in [MountType.CIFS, MountType.SMB]:
            cmd = self._build_cifs_mount(host, share, mount_point, username, password, options)
        else:
            raise MountError(f"Unsupported mount type: {mount_type}")
        
        # Execute mount
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise MountError(f"Mount failed: {result.stderr}")
            
            # Save mount info
            self.mounts[mount_name] = {
                'host': host,
                'share': share,
                'type': mount_type.value,
                'mount_point': mount_point,
                'username': username,
                'options': options or {}
            }
            self.save_mounts()
            
            return mount_point
            
        except Exception as e:
            raise MountError(f"Mount error: {str(e)}")
    
    def unmount(self, mount_point_or_name):
        """
        Unmount network share
        
        Args:
            mount_point_or_name: Mount point path or mount name
        """
        # Resolve mount point
        if os.path.isabs(mount_point_or_name):
            mount_point = mount_point_or_name
            mount_name = os.path.basename(mount_point)
        else:
            mount_name = mount_point_or_name
            mount_point = os.path.join(self.MOUNT_BASE, mount_name)
        
        if not self.is_mounted(mount_point):
            # Remove from saved mounts even if not currently mounted
            if mount_name in self.mounts:
                del self.mounts[mount_name]
                self.save_mounts()
            return True
        
        try:
            result = subprocess.run(f"umount '{mount_point}'", shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try force unmount
                result = subprocess.run(f"umount -f '{mount_point}'", shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    raise MountError(f"Unmount failed: {result.stderr}")
            
            # Remove from saved mounts
            if mount_name in self.mounts:
                del self.mounts[mount_name]
                self.save_mounts()
            
            # Try to remove mount point
            try:
                os.rmdir(mount_point)
            except:
                pass
            
            return True
            
        except Exception as e:
            raise MountError(f"Unmount error: {str(e)}")
    
    def remount_all(self):
        """Remount all saved mounts (e.g., after reboot)"""
        results = []
        
        for mount_name, info in list(self.mounts.items()):
            try:
                mount_point = self.mount(
                    host=info['host'],
                    share=info['share'],
                    mount_type=MountType(info['type']),
                    username=info.get('username'),
                    options=info.get('options'),
                    mount_name=mount_name
                )
                results.append((mount_name, True, mount_point))
            except Exception as e:
                results.append((mount_name, False, str(e)))
        
        return results
    
    def unmount_all(self):
        """Unmount all network mounts"""
        results = []
        
        for mount_name in list(self.mounts.keys()):
            try:
                self.unmount(mount_name)
                results.append((mount_name, True, None))
            except Exception as e:
                results.append((mount_name, False, str(e)))
        
        return results
    
    def is_mounted(self, mount_point):
        """Check if path is currently mounted"""
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    if mount_point in line:
                        return True
            return False
        except:
            return False
    
    def get_mounts(self):
        """Get list of current mounts"""
        current_mounts = []
        
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].startswith(self.MOUNT_BASE):
                        current_mounts.append({
                            'device': parts[0],
                            'mount_point': parts[1],
                            'type': parts[2],
                            'options': parts[3] if len(parts) > 3 else ''
                        })
        except Exception as e:
            print(f"Error reading mounts: {e}")
        
        return current_mounts
    
    def get_saved_mounts(self):
        """Get saved mount configurations"""
        return self.mounts.copy()
    
    def _detect_mount_type(self, host, share):
        """Auto-detect mount type based on share format"""
        # NFS typically has export paths like /path/to/share
        if share.startswith('/') and ':' not in share:
            return MountType.NFS
        
        # SMB/CIFS typically has share names without leading slash
        return MountType.CIFS
    
    def _build_nfs_mount(self, host, share, mount_point, options):
        """Build NFS mount command"""
        opts = []
        
        if options:
            if 'version' in options:
                opts.append(f"vers={options['version']}")
            if 'rsize' in options:
                opts.append(f"rsize={options['rsize']}")
            if 'wsize' in options:
                opts.append(f"wsize={options['wsize']}")
        
        if not opts:
            opts = ["vers=3", "nolock"]
        
        opts_str = ','.join(opts)
        return f"mount -t nfs -o {opts_str} {host}:{share} '{mount_point}'"
    
    def _build_cifs_mount(self, host, share, mount_point, username, password, options):
        """Build CIFS/SMB mount command"""
        opts = []
        
        if username:
            opts.append(f"username={username}")
        else:
            opts.append("guest")
        
        if password:
            opts.append(f"password={password}")
        
        # Default options
        opts.extend(["iocharset=utf8", "sec=ntlm"])
        
        if options:
            if 'domain' in options:
                opts.append(f"domain={options['domain']}")
            if 'vers' in options:
                opts.append(f"vers={options['vers']}")
        
        opts_str = ','.join(opts)
        
        # Format share path
        if not share.startswith('/'):
            share = '/' + share
        
        return f"mount -t cifs -o {opts_str} //{host}{share} '{mount_point}'"
    
    def save_mounts(self):
        """Save mount configurations to file"""
        try:
            with open(self.MOUNT_INFO_FILE, 'w') as f:
                json.dump(self.mounts, f, indent=2)
        except Exception as e:
            print(f"Error saving mounts: {e}")
    
    def load_mounts(self):
        """Load mount configurations from file"""
        if os.path.exists(self.MOUNT_INFO_FILE):
            try:
                with open(self.MOUNT_INFO_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading mounts: {e}")
        
        return {}
    
    def browse_network(self, timeout=5):
        """
        Browse for network shares using various methods
        
        Returns:
            list: Discovered hosts and shares
        """
        discovered = []
        
        # Try SMB discovery with nmblookup/smbtree
        try:
            # Look for SMB hosts
            result = subprocess.run(
                "smbtree -N -b", 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # Parse smbtree output
                    match = re.match(r'\\\\([^\\]+)\\([^\\]+)', line.strip())
                    if match:
                        host, share = match.groups()
                        discovered.append({
                            'protocol': 'SMB',
                            'host': host,
                            'share': share,
                            'type': 'share'
                        })
        except:
            pass
        
        return discovered

class MountError(Exception):
    """Mount operation error"""
    pass