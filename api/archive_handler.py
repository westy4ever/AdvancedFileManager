# -*- coding: utf-8 -*-
import os
import zipfile
import tarfile
import gzip
import shutil
from .file_operations import FileOperationError

class ArchiveHandler:
    SUPPORTED_FORMATS = ['.zip', '.tar', '.tar.gz', '.tgz', '.gz']
    
    def __init__(self):
        self.current_archive = None
        self.archive_type = None
    
    def create_archive(self, sources, destination, archive_type='zip', compression=None):
        """Create archive from files/directories"""
        try:
            if archive_type == 'zip':
                return self._create_zip(sources, destination)
            elif archive_type in ['tar', 'tar.gz', 'tgz']:
                return self._create_tar(sources, destination, compression)
            else:
                raise FileOperationError(f"Unsupported archive type: {archive_type}")
        except Exception as e:
            raise FileOperationError(f"Archive creation failed: {str(e)}")
    
    def _create_zip(self, sources, destination):
        """Create ZIP archive"""
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zf:
            for source in sources:
                if os.path.isdir(source):
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source))
                            zf.write(file_path, arcname)
                else:
                    zf.write(source, os.path.basename(source))
        return True
    
    def _create_tar(self, sources, destination, compression):
        """Create TAR archive with optional compression"""
        mode = 'w'
        if compression == 'gz' or destination.endswith('.gz') or destination.endswith('.tgz'):
            mode = 'w:gz'
        elif compression == 'bz2':
            mode = 'w:bz2'
        
        with tarfile.open(destination, mode) as tf:
            for source in sources:
                tf.add(source, arcname=os.path.basename(source))
        return True
    
    def extract_archive(self, archive_path, destination, specific_files=None):
        """Extract archive contents"""
        try:
            if not os.path.exists(destination):
                os.makedirs(destination)
            
            if archive_path.endswith('.zip'):
                return self._extract_zip(archive_path, destination, specific_files)
            elif any(archive_path.endswith(ext) for ext in ['.tar', '.tar.gz', '.tgz', '.gz']):
                return self._extract_tar(archive_path, destination, specific_files)
            else:
                raise FileOperationError("Unknown archive format")
        except Exception as e:
            raise FileOperationError(f"Extraction failed: {str(e)}")
    
    def _extract_zip(self, archive_path, destination, specific_files=None):
        """Extract ZIP file"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            if specific_files:
                for file in specific_files:
                    zf.extract(file, destination)
            else:
                zf.extractall(destination)
        return True
    
    def _extract_tar(self, archive_path, destination, specific_files=None):
        """Extract TAR archive"""
        with tarfile.open(archive_path, 'r:*') as tf:
            if specific_files:
                for member in specific_files:
                    tf.extract(member, destination)
            else:
                tf.extractall(destination)
        return True
    
    def list_contents(self, archive_path):
        """List archive contents without extracting"""
        try:
            contents = []
            
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for info in zf.infolist():
                        contents.append({
                            'name': info.filename,
                            'size': info.file_size,
                            'compressed': info.compress_size,
                            'date': info.date_time,
                            'is_dir': info.is_dir()
                        })
            elif any(archive_path.endswith(ext) for ext in ['.tar', '.tar.gz', '.tgz']):
                with tarfile.open(archive_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        contents.append({
                            'name': member.name,
                            'size': member.size,
                            'date': member.mtime,
                            'is_dir': member.isdir()
                        })
            
            return contents
        except Exception as e:
            raise FileOperationError(f"Cannot list archive contents: {str(e)}")
    
    def test_archive(self, archive_path):
        """Test archive integrity"""
        try:
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    bad_file = zf.testzip()
                    return bad_file is None
            elif any(archive_path.endswith(ext) for ext in ['.tar', '.tar.gz', '.tgz']):
                with tarfile.open(archive_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        pass
                return True
            return False
        except:
            return False