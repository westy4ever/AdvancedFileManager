# -*- coding: utf-8 -*-
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.config import config

class ContextMenu:
    """
    Dynamic context menu for file operations
    Shows relevant actions based on selection
    """
    
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
            _("Select action"),
            menu_items
        )
    
    def build_menu(self):
        """Build menu items based on context"""
        items = []
        selection = self.current_selection
        
        # Single item vs multi-selection
        is_single = len(selection) == 1
        has_dirs = any(item['is_dir'] for item in selection)
        has_files = any(not item['is_dir'] for item in selection)
        
        # File operations
        if is_single and selection[0].get('is_parent'):
            # Parent directory - limited options
            items.append((_("Refresh"), self.action_refresh))
            items.append((_("View"), self.action_view))
        
        else:
            # Open/View
            if is_single:
                if has_dirs:
                    items.append((_("Open"), self.action_open))
                else:
                    items.append((_("View/Play"), self.action_view))
            
            # Copy/Move
            items.append((_("Copy"), self.action_copy))
            items.append((_("Move"), self.action_move))
            
            if is_single:
                items.append((_("Rename"), self.action_rename))
            
            items.append((_("Delete"), self.action_delete))
            
            # Archive operations (files only)
            if has_files and not has_dirs:
                items.append((_("Create Archive"), self.action_create_archive))
            
            # Check if archive
            if is_single and self.is_archive(selection[0]['name']):
                items.append((_("Extract Archive"), self.action_extract_archive))
            
            # Media operations
            if is_single and self.is_media(selection[0]['name']):
                items.append((_("Play with..."), self.action_play_with))
                
                if self.is_video(selection[0]['name']):
                    items.append((_("Download Subtitles"), self.action_download_subs))
            
            # Properties
            items.append((_("Properties"), self.action_properties))
            
            # Permissions (Unix)
            if is_single:
                items.append((_("Permissions"), self.action_permissions))
            
            # Bookmark
            items.append((_("Add to Bookmarks"), self.action_bookmark))
        
        return items
    
    def is_archive(self, filename):
        """Check if file is archive"""
        archives = ['.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z']
        return any(filename.lower().endswith(ext) for ext in archives)
    
    def is_media(self, filename):
        """Check if file is media"""
        return self.is_video(filename) or self.is_audio(filename) or self.is_image(filename)
    
    def is_video(self, filename):
        exts = ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.m4v', '.mpg', '.mpeg']
        return any(filename.lower().endswith(ext) for ext in exts)
    
    def is_audio(self, filename):
        exts = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']
        return any(filename.lower().endswith(ext) for ext in exts)
    
    def is_image(self, filename):
        exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        return any(filename.lower().endswith(ext) for ext in exts)
    
    def menu_callback(self, choice):
        """Handle menu selection"""
        if choice:
            choice[1]()
    
    # Action implementations
    def action_open(self):
        """Open directory"""
        if self.current_selection:
            self.file_manager.open_directory(self.current_selection[0]['path'])
    
    def action_view(self):
        """View file"""
        if self.current_selection:
            self.file_manager.view_file(self.current_selection[0]['path'])
    
    def action_copy(self):
        """Copy selected items"""
        self.file_manager.copy_items(self.current_selection)
    
    def action_move(self):
        """Move selected items"""
        self.file_manager.move_items(self.current_selection)
    
    def action_rename(self):
        """Rename single item"""
        if self.current_selection:
            item = self.current_selection[0]
            self.session.openWithCallback(
                self.rename_callback,
                InputBox,
                title=_("New name:"),
                text=item['name']
            )
    
    def rename_callback(self, new_name):
        """Handle rename input"""
        if new_name:
            self.file_manager.rename_item(self.current_selection[0], new_name)
    
    def action_delete(self):
        """Delete selected items"""
        count = len(self.current_selection)
        self.session.openWithCallback(
            self.delete_callback,
            MessageBox,
            _("Delete %d items?") % count,
            MessageBox.TYPE_YESNO
        )
    
    def delete_callback(self, confirmed):
        """Handle delete confirmation"""
        if confirmed:
            self.file_manager.delete_items(self.current_selection)
    
    def action_create_archive(self):
        """Create archive from selection"""
        self.session.openWithCallback(
            self.archive_callback,
            ChoiceBox,
            _("Select archive format"),
            [
                ("ZIP", "zip"),
                ("TAR.GZ", "tar.gz"),
                ("TAR", "tar")
            ]
        )
    
    def archive_callback(self, format_choice):
        """Handle archive format selection"""
        if format_choice:
            format_type = format_choice[1]
            self.file_manager.create_archive(self.current_selection, format_type)
    
    def action_extract_archive(self):
        """Extract archive"""
        if self.current_selection:
            self.file_manager.extract_archive(self.current_selection[0]['path'])
    
    def action_play_with(self):
        """Choose player for media"""
        self.file_manager.play_with(self.current_selection[0]['path'])
    
    def action_download_subs(self):
        """Download subtitles"""
        if self.current_selection:
            from ..media.subtitle_manager import SubtitleManager
            sm = SubtitleManager()
            sm.download_subtitle(self.current_selection[0]['path'])
    
    def action_properties(self):
        """Show file properties"""
        if self.current_selection:
            self.file_manager.show_properties(self.current_selection[0])
    
    def action_permissions(self):
        """Change file permissions"""
        if self.current_selection:
            self.file_manager.change_permissions(self.current_selection[0])
    
    def action_bookmark(self):
        """Add to bookmarks"""
        if self.current_selection:
            self.file_manager.add_bookmark(self.current_selection[0]['path'])
    
    def action_refresh(self):
        """Refresh directory"""
        self.file_manager.refresh()


class ArchiveContextMenu(ContextMenu):
    """Specialized context menu for archive files"""
    
    def build_menu(self):
        """Build archive-specific menu"""
        items = []
        
        items.append((_("Extract Here"), self.action_extract_here))
        items.append((_("Extract to..."), self.action_extract_to))
        items.append((_("Extract Selected"), self.action_extract_selected))
        items.append((_("Test Archive"), self.action_test_archive))
        items.append((_("View Contents"), self.action_view_contents))
        items.append((_("Delete Archive"), self.action_delete))
        
        return items
    
    def action_extract_here(self):
        """Extract to current directory"""
        if self.current_selection:
            self.file_manager.extract_archive(
                self.current_selection[0]['path'],
                os.path.dirname(self.current_selection[0]['path'])
            )
    
    def action_extract_to(self):
        """Extract to specific directory"""
        # Would open directory browser
        pass
    
    def action_extract_selected(self):
        """Extract specific files from archive"""
        pass
    
    def action_test_archive(self):
        """Test archive integrity"""
        if self.current_selection:
            self.file_manager.test_archive(self.current_selection[0]['path'])
    
    def action_view_contents(self):
        """View archive contents without extracting"""
        if self.current_selection:
            self.file_manager.view_archive_contents(self.current_selection[0]['path'])