# -*- coding: utf-8 -*-
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.config import config
import os

# Import helpers to avoid duplication
from ..utils.helpers import get_file_icon

class ContextMenu:
    """
    Dynamic context menu for file operations
    Shows relevant actions based on selection
    """
    
    # File type definitions (shared)
    ARCHIVE_EXTS = ['.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z', '.bz2']
    VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.m4v', '.mpg', '.mpeg', '.vob', '.wmv', '.flv', '.webm']
    AUDIO_EXTS = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus']
    IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.raw']
    
    def __init__(self, session, file_manager):
        self.session = session
        self.file_manager = file_manager
        self.current_selection = None
    
    def show(self, item=None, selected_items=None):
        """
        Show context menu
        
        Args:
            item: Single item under cursor (if no multi-selection)
            selected_items: List of selected items
        """
        self.current_selection = selected_items or ([item] if item else [])
        
        if not self.current_selection:
            return
        
        # Build menu based on selection
        menu_items = self.build_menu()
        
        self.session.openWithCallback(
            self.menu_callback,
            ChoiceBox,
            "Select action",
            menu_items
        )
    
    def build_menu(self):
        """Build menu items based on context"""
        items = []
        selection = self.current_selection
        
        # Single item vs multi-selection
        is_single = len(selection) == 1
        has_dirs = any(item.get('is_dir', False) for item in selection)
        has_files = any(not item.get('is_dir', False) for item in selection)
        
        # File operations
        if is_single and selection[0].get('is_parent'):
            # Parent directory - limited options
            items.append(("Refresh", self.action_refresh))
        else:
            # Open/View
            if is_single:
                if has_dirs:
                    items.append(("Open", self.action_open))
                else:
                    items.append(("View/Play", self.action_view))
            
            # Copy/Move
            items.append(("Copy", self.action_copy))
            items.append(("Move", self.action_move))
            
            if is_single:
                items.append(("Rename", self.action_rename))
            
            items.append(("Delete", self.action_delete))
            
            # Archive operations (files only)
            if has_files and not has_dirs:
                items.append(("Create Archive", self.action_create_archive))
            
            # Check if archive
            if is_single and self.is_archive(selection[0].get('name', '')):
                items.append(("Extract Archive", self.action_extract_archive))
            
            # Media operations
            if is_single and self.is_media(selection[0].get('name', '')):
                items.append(("Play with...", self.action_play_with))
                
                if self.is_video(selection[0].get('name', '')):
                    items.append(("Download Subtitles", self.action_download_subs))
            
            # Properties
            items.append(("Properties", self.action_properties))
            
            # Permissions (Unix)
            if is_single:
                items.append(("Permissions", self.action_permissions))
            
            # Bookmark
            items.append(("Add to Bookmarks", self.action_bookmark))
        
        return items
    
    @classmethod
    def is_archive(cls, filename):
        """Check if file is archive"""
        return any(filename.lower().endswith(ext) for ext in cls.ARCHIVE_EXTS)
    
    @classmethod
    def is_media(cls, filename):
        """Check if file is media"""
        return cls.is_video(filename) or cls.is_audio(filename) or cls.is_image(filename)
    
    @classmethod
    def is_video(cls, filename):
        """Check if file is video"""
        return any(filename.lower().endswith(ext) for ext in cls.VIDEO_EXTS)
    
    @classmethod
    def is_audio(cls, filename):
        """Check if file is audio"""
        return any(filename.lower().endswith(ext) for ext in cls.AUDIO_EXTS)
    
    @classmethod
    def is_image(cls, filename):
        """Check if file is image"""
        return any(filename.lower().endswith(ext) for ext in cls.IMAGE_EXTS)
    
    def menu_callback(self, choice):
        """Handle menu selection"""
        if choice:
            choice[1]()
    
    # Action implementations
    def action_open(self):
        """Open directory"""
        if self.current_selection:
            path = self.current_selection[0].get('path')
            if path and hasattr(self.file_manager, 'open_directory'):
                self.file_manager.open_directory(path)
    
    def action_view(self):
        """View file"""
        if self.current_selection:
            path = self.current_selection[0].get('path')
            if path and hasattr(self.file_manager, 'openFile'):
                self.file_manager.openFile(path)
    
    def action_copy(self):
        """Copy selected items"""
        if hasattr(self.file_manager, 'copySelected'):
            self.file_manager.copySelected()
    
    def action_move(self):
        """Move selected items"""
        if hasattr(self.file_manager, 'moveSelected'):
            self.file_manager.moveSelected()
    
    def action_rename(self):
        """Rename single item"""
        if self.current_selection:
            item = self.current_selection[0]
            self.session.openWithCallback(
                self.rename_callback,
                InputBox,
                title="New name:",
                text=item.get('name', '')
            )
    
    def rename_callback(self, new_name):
        """Handle rename input"""
        if new_name and self.current_selection:
            if hasattr(self.file_manager, 'file_ops'):
                try:
                    old_path = self.current_selection[0].get('path')
                    if old_path:
                        self.file_manager.file_ops.rename(old_path, new_name)
                        self.file_manager.dual_pane.refresh()
                except Exception as e:
                    self.session.open(MessageBox, f"Rename failed: {e}", MessageBox.TYPE_ERROR)
    
    def action_delete(self):
        """Delete selected items"""
        if hasattr(self.file_manager, 'deleteSelected'):
            self.file_manager.deleteSelected()
    
    def action_create_archive(self):
        """Create archive from selection"""
        self.session.openWithCallback(
            self.archive_callback,
            ChoiceBox,
            "Select archive format",
            [
                ("ZIP", "zip"),
                ("TAR.GZ", "tar.gz"),
                ("TAR", "tar")
            ]
        )
    
    def archive_callback(self, format_choice):
        """Handle archive format selection"""
        if format_choice and hasattr(self.file_manager, 'archive_handler'):
            try:
                format_type = format_choice[1]
                sources = [item.get('path') for item in self.current_selection if item.get('path')]
                
                # Ask for archive name
                self.session.openWithCallback(
                    lambda name: self.create_archive_with_name(sources, name, format_type) if name else None,
                    InputBox,
                    title="Archive name:",
                    text=f"archive.{format_type}"
                )
            except Exception as e:
                self.session.open(MessageBox, f"Archive creation failed: {e}", MessageBox.TYPE_ERROR)
    
    def create_archive_with_name(self, sources, name, format_type):
        """Create archive with given name"""
        try:
            current_path = self.file_manager.dual_pane.get_active_path()
            destination = os.path.join(current_path, name)
            
            self.file_manager.archive_handler.create_archive(sources, destination, format_type)
            self.file_manager.dual_pane.refresh()
            self.session.open(MessageBox, "Archive created successfully", MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            self.session.open(MessageBox, f"Archive creation failed: {e}", MessageBox.TYPE_ERROR)
    
    def action_extract_archive(self):
        """Extract archive"""
        if self.current_selection and hasattr(self.file_manager, 'handleArchive'):
            path = self.current_selection[0].get('path')
            if path:
                self.file_manager.handleArchive(path)
    
    def action_play_with(self):
        """Choose player for media"""
        self.session.open(MessageBox, "Play with feature coming soon", MessageBox.TYPE_INFO)
    
    def action_download_subs(self):
        """Download subtitles"""
        self.session.open(MessageBox, "Subtitle download feature coming soon", MessageBox.TYPE_INFO)
    
    def action_properties(self):
        """Show file properties"""
        if hasattr(self.file_manager, 'showFileInfo'):
            self.file_manager.showFileInfo()
    
    def action_permissions(self):
        """Change file permissions"""
        self.session.open(MessageBox, "Permissions feature coming soon", MessageBox.TYPE_INFO)
    
    def action_bookmark(self):
        """Add to bookmarks"""
        self.session.open(MessageBox, "Bookmark added", MessageBox.TYPE_INFO, timeout=2)
    
    def action_refresh(self):
        """Refresh directory"""
        if hasattr(self.file_manager, 'refreshCurrent'):
            self.file_manager.refreshCurrent()


class ArchiveContextMenu(ContextMenu):
    """Specialized context menu for archive files"""
    
    def build_menu(self):
        """Build archive-specific menu"""
        items = []
        
        items.append(("Extract Here", self.action_extract_here))
        items.append(("Extract to...", self.action_extract_to))
        items.append(("View Contents", self.action_view_contents))
        items.append(("Test Archive", self.action_test_archive))
        items.append(("Delete Archive", self.action_delete))
        
        return items
    
    def action_extract_here(self):
        """Extract to current directory"""
        if self.current_selection and hasattr(self.file_manager, 'archive_handler'):
            try:
                archive_path = self.current_selection[0].get('path')
                if archive_path:
                    destination = os.path.dirname(archive_path)
                    self.file_manager.archive_handler.extract_archive(archive_path, destination)
                    self.file_manager.dual_pane.refresh()
                    self.session.open(MessageBox, "Archive extracted successfully", MessageBox.TYPE_INFO, timeout=3)
            except Exception as e:
                self.session.open(MessageBox, f"Extraction failed: {e}", MessageBox.TYPE_ERROR)
    
    def action_extract_to(self):
        """Extract to specific directory"""
        self.session.open(MessageBox, "Extract to feature coming soon", MessageBox.TYPE_INFO)
    
    def action_view_contents(self):
        """View archive contents without extracting"""
        if self.current_selection and hasattr(self.file_manager, 'viewArchiveContents'):
            path = self.current_selection[0].get('path')
            if path:
                self.file_manager.viewArchiveContents(path)
    
    def action_test_archive(self):
        """Test archive integrity"""
        if self.current_selection and hasattr(self.file_manager, 'testArchive'):
            path = self.current_selection[0].get('path')
            if path:
                self.file_manager.testArchive(path)