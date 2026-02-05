# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime

def format_size(size_bytes):
    """
    Format byte size to human readable string
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    if size_bytes is None or size_bytes < 0:
        return "Unknown"
    
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

def format_date(timestamp, format_str="%Y-%m-%d %H:%M"):
    """
    Format Unix timestamp to readable date
    
    Args:
        timestamp: Unix timestamp
        format_str: Date format string
    
    Returns:
        str: Formatted date
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format_str)
    except:
        return "Unknown"

def human_readable_time(seconds):
    """
    Convert seconds to human readable duration
    
    Args:
        seconds: Time in seconds
    
    Returns:
        str: Formatted time (e.g., "1:30:45")
    """
    if seconds < 0:
        return "0:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def sanitize_filename(filename, replacement='_'):
    """
    Sanitize filename for safe filesystem usage
    
    Args:
        filename: Original filename
        replacement: Character to replace invalid chars with
    
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "unnamed"
    
    # Invalid characters in most filesystems
    invalid_chars = '<>:"/\\|?*'
    
    # Replace invalid characters
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Reserved Windows names
    reserved = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
        'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_upper = filename.upper()
    if name_upper in reserved or (name_upper.startswith(tuple(reserved)) and '.' not in name_upper):
        filename = f"_{filename}"
    
    # Trim whitespace
    filename = filename.strip(' .')
    
    # Ensure not empty
    if not filename:
        filename = "unnamed"
    
    # Limit length (255 is safe for most filesystems)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename

def get_file_icon(filename, is_dir=False, is_link=False):
    """
    Get appropriate icon/emoji for file type
    
    Args:
        filename: Filename
        is_dir: Whether it's a directory
        is_link: Whether it's a symlink
    
    Returns:
        str: Icon character
    """
    if is_link:
        return "🔗"
    
    if is_dir:
        return "📁"
    
    # Get extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Video files
    if ext in ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.m4v', '.mpg', '.mpeg', '.vob']:
        return "🎬"
    
    # Audio files
    if ext in ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus']:
        return "🎵"
    
    # Image files
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.raw']:
        return "🖼️"
    
    # Archive files
    if ext in ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.tgz', '.tar.gz']:
        return "📦"
    
    # Document files
    if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
        return "📄"
    
    # Spreadsheet files
    if ext in ['.xls', '.xlsx', '.csv', '.ods']:
        return "📊"
    
    # Code files
    if ext in ['.py', '.js', '.html', '.css', '.php', '.java', '.c', '.cpp', '.h', '.sh']:
        return "💻"
    
    # Executable files
    if ext in ['.exe', '.bin', '.sh', '.run', '.AppImage']:
        return "⚙️"
    
    # Default
    return "📄"

def split_path(path):
    """
    Split path into components
    
    Args:
        path: Full path
    
    Returns:
        list: Path components
    """
    components = []
    while True:
        head, tail = os.path.split(path)
        if tail:
            components.append(tail)
        if not head or head == path:
            if head:
                components.append(head)
            break
        path = head
    
    components.reverse()
    return components

def get_disk_usage(path):
    """
    Get disk usage statistics
    
    Args:
        path: Path to check
    
    Returns:
        dict: Total, used, free bytes and percentages
    """
    try:
        stat = os.statvfs(path)
        
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent_used': (used / total * 100) if total > 0 else 0,
            'percent_free': (free / total * 100) if total > 0 else 0
        }
    except Exception as e:
        return {
            'total': 0,
            'used': 0,
            'free': 0,
            'percent_used': 0,
            'percent_free': 0,
            'error': str(e)
        }

def calculate_transfer_time(size_bytes, speed_bps):
    """
    Calculate estimated transfer time
    
    Args:
        size_bytes: File size in bytes
        speed_bps: Transfer speed in bytes per second
    
    Returns:
        str: Human readable time estimate
    """
    if speed_bps <= 0:
        return "Unknown"
    
    seconds = size_bytes / speed_bps
    return human_readable_time(seconds)

def format_transfer_speed(bytes_per_second):
    """
    Format transfer speed
    
    Args:
        bytes_per_second: Speed in B/s
    
    Returns:
        str: Formatted speed (e.g., "1.5 MB/s")
    """
    return format_size(bytes_per_second) + "/s"

def is_binary_file(filepath, sample_size=1024):
    """
    Check if file is binary
    
    Args:
        filepath: Path to file
        sample_size: Bytes to sample
    
    Returns:
        bool: True if binary
    """
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(sample_size)
            if b'\x00' in chunk:
                return True
        return False
    except:
        return True

def get_mime_type(filename):
    """
    Guess MIME type from filename
    
    Args:
        filename: Filename
    
    Returns:
        str: MIME type
    """
    ext = os.path.splitext(filename)[1].lower()
    
    mime_types = {
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        
        # Video
        '.mp4': 'video/mp4',
        '.mkv': 'video/x-matroska',
        '.avi': 'video/x-msvideo',
        '.ts': 'video/mp2t',
        '.mov': 'video/quicktime',
        
        # Audio
        '.mp3': 'audio/mpeg',
        '.flac': 'audio/flac',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        
        # Archives
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',
        
        # Documents
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.xml': 'application/xml',
        '.json': 'application/json',
    }
    
    return mime_types.get(ext, 'application/octet-stream')