# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.MoviePlayer import MoviePlayer  # Added this import
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.config import config
from enigma import eServiceReference, getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import os

# Import our modules
from ..api.file_operations import FileOperationManager, FileOperationError
from ..api.archive_handler import ArchiveHandler
from ..api.search_engine import SearchEngine
from ..api.cache_manager import CacheManager
from ..api.trash_manager import TrashManager, TrashError
from ..utils.security import SecurityManager, SecurityError
from ..utils.logger import Logger
from ..utils.helpers import format_size, format_date, get_file_icon, sanitize_filename
from ..ui.dual_pane import DualPaneLayout
from ..ui.context_menu import ContextMenu, ArchiveContextMenu

class AdvancedFileManager(Screen):
    skin = """
    <screen name="AdvancedFileManager" position="center,center" size="1200,700" title="Advanced File Manager">
        <!-- Header -->
        <eLabel position="0,0" size="1200,50" backgroundColor="#1a1a1a" />
        <widget source="title" render="Label" position="20,10" size="600,30" font="Regular;24" foregroundColor="#ffffff" />
        <widget source="status" render="Label" position="640,10" size="540,30" font="Regular;20" foregroundColor="#aaaaaa" halign="right" />
        
        <!-- Left Panel -->
        <eLabel position="10,60" size="585,520" backgroundColor="#2a2a2a" />
        <widget source="left_path" render="Label" position="15,65" size="575,25" font="Regular;20" foregroundColor="#00ffff" />
        <widget name="left_list" position="15,95" size="575,475" scrollbarMode="showOnDemand" />
        <widget name="left_info" position="15,575" size="575,20" font="Regular;16" foregroundColor="#888888" />
        
        <!-- Right Panel -->
        <eLabel position="605,60" size="585,520" backgroundColor="#2a2a2a" />
        <widget source="right_path" render="Label" position="610,65" size="575,25" font="Regular;20" foregroundColor="#00ffff" />
        <widget name="right_list" position="610,95" size="575,475" scrollbarMode="showOnDemand" />
        <widget name="right_info" position="610,575" size="575,20" font="Regular;16" foregroundColor="#888888" />
        
        <!-- Bottom Control Bar -->
        <eLabel position="0,600" size="1200,100" backgroundColor="#1a1a1a" />
        
        <!-- Color Buttons -->
        <widget source="key_red" render="Label" position="20,610" size="280,30" font="Regular;20" foregroundColor="#ff4444" halign="center" />
        <widget source="key_green" render="Label" position="320,610" size="280,30" font="Regular;20" foregroundColor="#44ff44" halign="center" />
        <widget source="key_yellow" render="Label" position="620,610" size="280,30" font="Regular;20" foregroundColor="#ffff44" halign="center" />
        <widget source="key_blue" render="Label" position="920,610" size="280,30" font="Regular;20" foregroundColor="#4444ff" halign="center" />
        
        <!-- Help Text -->
        <widget source="help" render="Label" position="20,650" size="1160,40" font="Regular;18" foregroundColor="#666666" halign="center" valign="center" />
    </screen>
    """
    
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        # Initialize managers
        self.logger = Logger("FileManager")
        self.security = SecurityManager()
        self.file_ops = FileOperationManager()
        self.archive_handler = ArchiveHandler()
        self.search_engine = SearchEngine()
        self.trash_manager = TrashManager() if config.plugins.advancedfilemanager.use_trash.value else None
        self.cache_manager = CacheManager() if config.plugins.advancedfilemanager.enable_cache.value else None
        
        # UI State
        self.dual_pane = None
        self.context_menu = ContextMenu(session, self)
        
        # Setup UI
        self["title"] = StaticText("Advanced File Manager")
        self["status"] = StaticText("Ready")
        self["left_path"] = StaticText("/media")
        self["right_path"] = StaticText("/media")
        self["left_info"] = Label("")
        self["right_info"] = Label("")
        self["help"] = StaticText("OK: Open | Menu: Context | Info: Properties | Red: Delete | Green: Copy | Yellow: Move | Blue: Menu")
        
        # Color buttons
        self["key_red"] = StaticText("Delete (F8)")
        self["key_green"] = StaticText("Copy (F5)")
        self["key_yellow"] = StaticText("Move (F6)")
        self["key_blue"] = StaticText("Menu")
        
        # Create dual pane layout
        self.dual_pane = DualPaneLayout(
            session, 
            self,
            left_path=config.plugins.advancedfilemanager.lastpath.value,
            right_path="/media"
        )
        
        # Actions
        self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "MovieSelectionActions", "HelpActions", "NumberActions"],
        {
            "ok": self.okPressed,
            "back": self.close,
            "up": self.moveUp,
            "down": self.moveDown,
            "left": self.moveLeft,
            "right": self.moveRight,
            "pageUp": self.pageUp,
            "pageDown": self.pageDown,
            "red": self.deleteSelected,
            "green": self.copySelected,
            "yellow": self.moveSelected,
            "blue": self.showMainMenu,
            "menu": self.showContextMenu,
            "info": self.showFileInfo,
            "nextBouquet": self.switchPanel,
            "prevBouquet": self.switchPanel,
            "1": self.selectAll,
            "2": self.invertSelection,
            "3": self.deselectAll,
            "0": self.refreshCurrent,
        }, -1)
        
        # Initial refresh
        self.onLayoutFinish.append(self.layoutFinished)
    
    def layoutFinished(self):
        """Called when layout is ready"""
        self.dual_pane.refresh()
        self.updateStatus()
    
    def okPressed(self):
        """Handle OK button"""
        current_item = self.getCurrentItem()
        
        if not current_item:
            return
        
        if current_item['is_dir'] or current_item.get('is_parent'):
            # Navigate into directory
            self.dual_pane.load_directory(
                self.dual_pane.active_panel,
                current_item['path']
            )
            self.updateStatus()
        else:
            # Open file
            self.openFile(current_item['path'])
    
    def openFile(self, path):
        """Open file with appropriate handler"""
        ext = os.path.splitext(path)[1].lower()
        
        # Video files
        video_exts = ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.m4v', '.mpg', '.mpeg', '.vob', '.wmv', '.flv', '.webm']
        if ext in video_exts:
            self.playVideo(path)
            return
        
        # Audio files
        audio_exts = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus']
        if ext in audio_exts:
            self.playAudio(path)
            return
        
        # Image files
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.raw']
        if ext in image_exts:
            self.viewImage(path)
            return
        
        # Archives
        archive_exts = ['.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z', '.bz2']
        if ext in archive_exts:
            self.handleArchive(path)
            return
        
        # Unknown file type
        self.session.open(
            MessageBox,
            _("Unknown file type: %s\n\nNo application associated with this file type.") % ext,
            MessageBox.TYPE_INFO
        )
    
    def playVideo(self, path):
        """Play video file"""
        if not config.plugins.advancedfilemanager.enable_media.value:
            # Use default player
            ref = eServiceReference(4097, 0, path)
            self.session.open(MoviePlayer, ref)
            return
        
        # Use advanced video player
        from ..media.video_player import AdvancedVideoPlayer
        
        ref = eServiceReference(4097, 0, path)
        playlist = self.buildVideoPlaylist(path)
        
        self.session.open(AdvancedVideoPlayer, ref, file_path=path, playlist=playlist)
    
    def playAudio(self, path):
        """Play audio file"""
        from ..media.audio_player import AudioPlayer
        self.session.open(AudioPlayer, file_path=path)
    
    def viewImage(self, path):
        """View image file"""
        from ..media.image_viewer import ImageViewer
        self.session.open(ImageViewer, file_path=path)
    
    def buildVideoPlaylist(self, current_file):
        """Build playlist of video files in directory"""
        directory = os.path.dirname(current_file)
        video_exts = ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.m4v', '.mpg', '.mpeg', '.vob', '.wmv', '.flv', '.webm']
        
        try:
            files = sorted([f for f in os.listdir(directory) 
                           if os.path.splitext(f)[1].lower() in video_exts])
            
            playlist = [os.path.join(directory, f) for f in files]
            return playlist
        except:
            return [current_file]
    
    def handleArchive(self, path):
        """Handle archive file"""
        self.session.openWithCallback(
            self.archiveCallback,
            ArchiveContextMenu,
            path,
            self.archive_handler
        )
    
    def archiveCallback(self, action):
        """Handle archive menu action"""
        if action:
            action()
    
    def showContextMenu(self):
        """Show context menu for current item"""
        current_item = self.getCurrentItem()
        selected_items = self.dual_pane.get_selected_items()
        
        if selected_items:
            self.context_menu.show(selected_items=selected_items)
        elif current_item:
            self.context_menu.show(item=current_item)
    
    def showMainMenu(self):
        """Show main application menu"""
        menu_items = [
            (_("New Folder"), self.createFolder),
            (_("Search Files"), self.searchFiles),
            (_("View"), self.toggleView),
            (_("Bookmarks"), self.showBookmarks),
            (_("Remote Connections"), self.showRemoteConnections),
            (_("Network Mounts"), self.showNetworkMounts),
            (_("Trash"), self.showTrash),
            (_("Settings"), self.openSettings),
        ]
        
        self.session.openWithCallback(
            self.mainMenuCallback,
            ChoiceBox,
            _("Main Menu"),
            menu_items
        )
    
    def mainMenuCallback(self, choice):
        """Handle main menu selection"""
        if choice:
            choice[1]()
    
    def createFolder(self):
        """Create new folder"""
        current_path = self.dual_pane.get_active_path()
        
        self.session.openWithCallback(
            self.createFolderCallback,
            InputBox,
            title=_("Enter folder name:"),
            text="New Folder"
        )
    
    def createFolderCallback(self, name):
        """Handle folder creation"""
        if not name:
            return
        
        current_path = self.dual_pane.get_active_path()
        new_path = os.path.join(current_path, sanitize_filename(name))
        
        try:
            os.makedirs(new_path, exist_ok=True)
            self.dual_pane.refresh(self.dual_pane.active_panel)
            self["status"].setText(_("Created folder: %s") % name)
        except Exception as e:
            self.session.open(
                MessageBox,
                _("Cannot create folder: %s") % str(e),
                MessageBox.TYPE_ERROR
            )
    
    def searchFiles(self):
        """Open search dialog"""
        self.session.openWithCallback(
            self.searchCallback,
            InputBox,
            title=_("Search for files:"),
            text="*"
        )
    
    def searchCallback(self, pattern):
        """Handle search"""
        if pattern:
            current_path = self.dual_pane.get_active_path()
            self["status"].setText(_("Searching in %s...") % current_path)
            
            # Use search engine
            self.search_engine.search(
                current_path,
                pattern,
                options={'recursive': True}
            )
            
            # Show results (would need a results screen)
            self.session.open(
                MessageBox,
                _("Search started. Results will be shown when complete."),
                MessageBox.TYPE_INFO,
                timeout=3
            )
    
    def toggleView(self):
        """Toggle between view modes"""
        # Toggle hidden files
        current = config.plugins.advancedfilemanager.showhidden.value
        config.plugins.advancedfilemanager.showhidden.value = not current
        config.plugins.advancedfilemanager.showhidden.save()
        
        self.dual_pane.refresh()
        status = _("Showing hidden files") if not current else _("Hiding hidden files")
        self["status"].setText(status)
    
    def showBookmarks(self):
        """Show bookmarks"""
        # Would open bookmark manager
        pass
    
    def showRemoteConnections(self):
        """Show remote connection manager"""
        from ..network.remote_browser import RemoteBrowser
        browser = RemoteBrowser()
        # Would open remote browser screen
        pass
    
    def showNetworkMounts(self):
        """Show network mount manager"""
        from ..network.network_mount import NetworkMountManager
        mount_mgr = NetworkMountManager()
        # Would open mount manager screen
        pass
    
    def showTrash(self):
        """Show trash contents"""
        if not self.trash_manager:
            self.session.open(
                MessageBox,
                _("Trash is disabled. Enable it in settings."),
                MessageBox.TYPE_INFO
            )
            return
        
        items = self.trash_manager.list_trash()
        # Would open trash browser screen
        pass
    
    def openSettings(self):
        """Open settings"""
        from .setup_wizard import SetupWizard
        self.session.open(SetupWizard)
    
    def copySelected(self):
        """Copy selected items to opposite panel"""
        src_panel = self.dual_pane.active_panel
        dst_panel = "right" if src_panel == "left" else "left"
        
        src_path = self.dual_pane.get_active_path()
        dst_path = self.dual_pane.right_path if src_panel == "left" else self.dual_pane.left_path
        
        selected = self.dual_pane.get_active_selections()
        
        if not selected:
            # Copy current item
            current = self.getCurrentItem()
            if current and not current.get('is_parent'):
                selected = {current['path']}
        
        if not selected:
            self["status"].setText(_("No items selected"))
            return
        
        # Confirm if needed
        if config.plugins.advancedfilemanager.confirm_overwrite.value:
            self.session.openWithCallback(
                lambda x: self.doCopy(selected, src_path, dst_path) if x else None,
                MessageBox,
                _("Copy %d items to %s?") % (len(selected), dst_path),
                MessageBox.TYPE_YESNO
            )
        else:
            self.doCopy(selected, src_path, dst_path)
    
    def doCopy(self, items, src_path, dst_path):
        """Perform copy operation"""
        success = 0
        failed = []
        
        for src in items:
            try:
                dst = os.path.join(dst_path, os.path.basename(src))
                self.file_ops.copy(src, dst)
                success += 1
            except FileOperationError as e:
                failed.append((src, str(e)))
        
        # Refresh
        self.dual_pane.refresh()
        
        # Status
        if failed:
            self["status"].setText(_("Copied %d/%d items (%d failed)") % (success, len(items), len(failed)))
        else:
            self["status"].setText(_("Copied %d items successfully") % success)
    
    def moveSelected(self):
        """Move selected items"""
        src_panel = self.dual_pane.active_panel
        dst_panel = "right" if src_panel == "left" else "left"
        
        src_path = self.dual_pane.get_active_path()
        dst_path = self.dual_pane.right_path if src_panel == "left" else self.dual_pane.left_path
        
        selected = self.dual_pane.get_active_selections()
        
        if not selected:
            current = self.getCurrentItem()
            if current and not current.get('is_parent'):
                selected = {current['path']}
        
        if not selected:
            self["status"].setText(_("No items selected"))
            return
        
        self.session.openWithCallback(
            lambda x: self.doMove(selected, src_path, dst_path) if x else None,
            MessageBox,
            _("Move %d items to %s?") % (len(selected), dst_path),
            MessageBox.TYPE_YESNO
        )
    
    def doMove(self, items, src_path, dst_path):
        """Perform move operation"""
        success = 0
        
        for src in items:
            try:
                dst = os.path.join(dst_path, os.path.basename(src))
                self.file_ops.move(src, dst)
                success += 1
            except FileOperationError as e:
                self.logger.error(f"Move failed: {e}")
        
        # Clear selections
        self.dual_pane.deselect_all()
        self.dual_pane.refresh()
        
        self["status"].setText(_("Moved %d items") % success)
    
    def deleteSelected(self):
        """Delete selected items"""
        selected = self.dual_pane.get_active_selections()
        
        if not selected:
            current = self.getCurrentItem()
            if current and not current.get('is_parent'):
                selected = {current['path']}
        
        if not selected:
            self["status"].setText(_("No items selected"))
            return
        
        if config.plugins.advancedfilemanager.confirm_delete.value:
            self.session.openWithCallback(
                lambda x: self.doDelete(selected) if x else None,
                MessageBox,
                _("Delete %d items?") % len(selected),
                MessageBox.TYPE_YESNO
            )
        else:
            self.doDelete(selected)
    
    def doDelete(self, items):
        """Perform delete operation"""
        success = 0
        
        for path in items:
            try:
                if self.trash_manager:
                    self.trash_manager.trash(path)
                else:
                    self.file_ops.delete(path, use_trash=False)
                success += 1
            except (FileOperationError, TrashError) as e:
                self.logger.error(f"Delete failed: {e}")
        
        # Clear selections
        self.dual_pane.deselect_all()
        self.dual_pane.refresh()
        
        self["status"].setText(_("Deleted %d items") % success)
    
    def showFileInfo(self):
        """Show file information"""
        current = self.getCurrentItem()
        if not current:
            return
        
        try:
            info = self.file_ops.get_file_info(current['path'])
            
            text = []
            text.append(_("Name: %s") % info['name'])
            text.append(_("Path: %s") % info['path'])
            text.append(_("Size: %s") % format_size(info['size']))
            text.append(_("Modified: %s") % format_date(info['modified']))
            text.append(_("Permissions: %s") % info['permissions'])
            text.append(_("Type: %s") % (_("Directory") if info['is_dir'] else _("File")))
            
            if info.get('mime_type'):
                text.append(_("MIME Type: %s") % info['mime_type'])
            
            self.session.open(
                MessageBox,
                "\n".join(text),
                MessageBox.TYPE_INFO,
                title=_("File Information")
            )
            
        except FileOperationError as e:
            self.session.open(
                MessageBox,
                _("Cannot get file info: %s") % str(e),
                MessageBox.TYPE_ERROR
            )
    
    def getCurrentItem(self):
        """Get current item from active panel"""
        files = self.dual_pane.get_active_files()
        list_widget = self.dual_pane.get_active_list()
        index = list_widget.getSelectionIndex()
        
        if 0 <= index < len(files):
            return files[index]
        return None
    
    def moveUp(self):
        self.dual_pane.get_active_list().up()
        self.updateStatus()
    
    def moveDown(self):
        self.dual_pane.get_active_list().down()
        self.updateStatus()
    
    def moveLeft(self):
        if self.dual_pane.active_panel == 'right':
            self.dual_pane.switch_panel()
        else:
            self.okPressed()
    
    def moveRight(self):
        if self.dual_pane.active_panel == 'left':
            self.dual_pane.switch_panel()
        else:
            self.okPressed()
    
    def pageUp(self):
        self.dual_pane.get_active_list().pageUp()
        self.updateStatus()
    
    def pageDown(self):
        self.dual_pane.get_active_list().pageDown()
        self.updateStatus()
    
    def switchPanel(self):
        self.dual_pane.switch_panel()
        self.updateStatus()
    
    def selectAll(self):
        self.dual_pane.select_all()
        self.updateStatus()
    
    def deselectAll(self):
        self.dual_pane.deselect_all()
        self.updateStatus()
    
    def invertSelection(self):
        self.dual_pane.invert_selection()
        self.updateStatus()
    
    def refreshCurrent(self):
        self.dual_pane.refresh(self.dual_pane.active_panel)
        self["status"].setText(_("Refreshed"))
    
    def updateStatus(self):
        """Update status bar"""
        panel = self.dual_pane.active_panel
        files = self.dual_pane.get_active_files()
        selections = self.dual_pane.get_active_selections()
        
        count = len([f for f in files if not f.get('is_parent')])
        sel_count = len(selections)
        
        status = _("%s panel: %d items") % (panel.upper(), count)
        if sel_count > 0:
            status += _(" (%d selected)") % sel_count
        
        self["status"].setText(status)
        
        # Update panel info
        info_text = _("%d items") % count
        if panel == 'left':
            self["left_info"].setText(info_text)
        else:
            self["right_info"].setText(info_text)
    
    def close(self):
        """Clean up and close"""
        # Save cache
        if self.cache_manager:
            self.cache_manager.save_cache()
        
        # Save last path
        config.plugins.advancedfilemanager.lastpath.value = self.dual_pane.left_path
        config.plugins.advancedfilemanager.save()
        
        Screen.close(self)