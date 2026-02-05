# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.Sources.StaticText import StaticText
from Components.config import config
from enigma import eServiceReference, getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import os

# Import our modules
from ..api.file_operations import FileOperationManager, FileOperationError
from ..api.archive_handler import ArchiveHandler
from ..api.search_engine import SearchEngine
from ..utils.security import SecurityManager, SecurityError
from ..utils.logger import Logger
from ..utils.helpers import format_size, format_date, get_file_icon, sanitize_filename
from ..ui.dual_pane import DualPaneLayout
from ..ui.context_menu import ContextMenu, ArchiveContextMenu

# Check for optional dependencies
try:
    from ..api.cache_manager import CacheManager
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False

try:
    from ..api.trash_manager import TrashManager, TrashError
    HAS_TRASH = True
except ImportError:
    HAS_TRASH = False

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
        <widget source="left_info" render="Label" position="15,575" size="575,20" font="Regular;16" foregroundColor="#888888" />
        
        <!-- Right Panel -->
        <eLabel position="605,60" size="585,520" backgroundColor="#2a2a2a" />
        <widget source="right_path" render="Label" position="610,65" size="575,25" font="Regular;20" foregroundColor="#00ffff" />
        <widget name="right_list" position="610,95" size="575,475" scrollbarMode="showOnDemand" />
        <widget source="right_info" render="Label" position="610,575" size="575,20" font="Regular;16" foregroundColor="#888888" />
        
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
        
        # Initialize optional managers
        if HAS_TRASH and config.plugins.advancedfilemanager.use_trash.value:
            try:
                self.trash_manager = TrashManager()
            except Exception as e:
                self.logger.error(f"Failed to initialize trash manager: {e}")
                self.trash_manager = None
        else:
            self.trash_manager = None
        
        if HAS_CACHE and config.plugins.advancedfilemanager.enable_cache.value:
            try:
                self.cache_manager = CacheManager()
            except Exception as e:
                self.logger.error(f"Failed to initialize cache manager: {e}")
                self.cache_manager = None
        else:
            self.cache_manager = None
        
        # UI State
        self.dual_pane = None
        self.context_menu = ContextMenu(session, self)
        
        # Setup UI
        self["title"] = StaticText("Advanced File Manager")
        self["status"] = StaticText("Ready")
        self["left_path"] = StaticText("/media")
        self["right_path"] = StaticText("/media")
        self["left_info"] = StaticText("")
        self["right_info"] = StaticText("")
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
            "Unknown file type: %s\n\nNo application associated with this file type." % ext,
            MessageBox.TYPE_INFO
        )
    
    def playVideo(self, path):
        """Play video file"""
        try:
            if config.plugins.advancedfilemanager.enable_media.value:
                from ..media.video_player import AdvancedVideoPlayer
                ref = eServiceReference(4097, 0, path)
                playlist = self.buildVideoPlaylist(path)
                self.session.open(AdvancedVideoPlayer, ref, file_path=path, playlist=playlist)
            else:
                # Use default player
                from Screens.MoviePlayer import MoviePlayer
                ref = eServiceReference(4097, 0, path)
                self.session.open(MoviePlayer, ref)
        except ImportError as e:
            self.logger.error(f"Cannot load video player: {e}")
            self.session.open(MessageBox, "Video player not available", MessageBox.TYPE_ERROR)
    
    def playAudio(self, path):
        """Play audio file"""
        try:
            from ..media.audio_player import AudioPlayer
            self.session.open(AudioPlayer, file_path=path)
        except ImportError as e:
            self.logger.error(f"Cannot load audio player: {e}")
            self.session.open(MessageBox, "Audio player not available", MessageBox.TYPE_ERROR)
    
    def viewImage(self, path):
        """View image file"""
        try:
            from ..media.image_viewer import ImageViewer
            self.session.open(ImageViewer, file_path=path)
        except ImportError as e:
            self.logger.error(f"Cannot load image viewer: {e}")
            self.session.open(MessageBox, "Image viewer not available", MessageBox.TYPE_ERROR)
    
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
        menu_items = [
            ("Extract Here", lambda: self.extractArchive(path, os.path.dirname(path))),
            ("View Contents", lambda: self.viewArchiveContents(path)),
            ("Test Archive", lambda: self.testArchive(path)),
        ]
        
        self.session.openWithCallback(
            lambda choice: choice[1]() if choice else None,
            ChoiceBox,
            "Archive Options",
            menu_items
        )
    
    def extractArchive(self, archive_path, destination):
        """Extract archive to destination"""
        try:
            self.archive_handler.extract_archive(archive_path, destination)
            self.dual_pane.refresh()
            self["status"].setText("Archive extracted successfully")
        except Exception as e:
            self.logger.error(f"Extract failed: {e}")
            self.session.open(MessageBox, f"Extract failed: {e}", MessageBox.TYPE_ERROR)
    
    def viewArchiveContents(self, archive_path):
        """View archive contents"""
        try:
            contents = self.archive_handler.list_contents(archive_path)
            text = "\n".join([item['name'] for item in contents])
            self.session.open(MessageBox, text, MessageBox.TYPE_INFO, title="Archive Contents")
        except Exception as e:
            self.logger.error(f"Cannot view archive: {e}")
            self.session.open(MessageBox, f"Cannot view archive: {e}", MessageBox.TYPE_ERROR)
    
    def testArchive(self, archive_path):
        """Test archive integrity"""
        try:
            result = self.archive_handler.test_archive(archive_path)
            if result:
                self.session.open(MessageBox, "Archive is valid", MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, "Archive is corrupted", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            self.session.open(MessageBox, f"Test failed: {e}", MessageBox.TYPE_ERROR)
    
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
            ("New Folder", self.createFolder),
            ("Search Files", self.searchFiles),
            ("Toggle Hidden Files", self.toggleView),
            ("Bookmarks", self.showBookmarks),
        ]
        
        # Add optional menu items
        if config.plugins.advancedfilemanager.enable_network.value:
            menu_items.append(("Network", self.showNetworkMenu))
        
        if self.trash_manager:
            menu_items.append(("Trash", self.showTrash))
        
        menu_items.append(("Settings", self.openSettings))
        
        self.session.openWithCallback(
            self.mainMenuCallback,
            ChoiceBox,
            "Main Menu",
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
            title="Enter folder name:",
            text="New Folder"
        )
    
    def createFolderCallback(self, name):
        """Handle folder creation"""
        if not name:
            return
        
        current_path = self.dual_pane.get_active_path()
        new_path = os.path.join(current_path, sanitize_filename(name))
        
        try:
            # Validate path before creating
            self.security.validate_path(new_path, allow_write=True)
            os.makedirs(new_path, exist_ok=True)
            self.dual_pane.refresh(self.dual_pane.active_panel)
            self["status"].setText("Created folder: %s" % name)
        except SecurityError as e:
            self.logger.error(f"Security error creating folder: {e}")
            self.session.open(MessageBox, f"Cannot create folder: {e}", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.logger.error(f"Error creating folder: {e}")
            self.session.open(MessageBox, f"Cannot create folder: {e}", MessageBox.TYPE_ERROR)
    
    def searchFiles(self):
        """Open search dialog"""
        self.session.openWithCallback(
            self.searchCallback,
            InputBox,
            title="Search for files:",
            text="*"
        )
    
    def searchCallback(self, pattern):
        """Handle search"""
        if pattern:
            current_path = self.dual_pane.get_active_path()
            self["status"].setText("Searching in %s..." % current_path)
            
            # Use search engine
            self.search_engine.search(
                current_path,
                pattern,
                options={'recursive': True}
            )
            
            self.session.open(
                MessageBox,
                "Search started. Results will be shown when complete.",
                MessageBox.TYPE_INFO,
                timeout=3
            )
    
    def toggleView(self):
        """Toggle between view modes"""
        current = config.plugins.advancedfilemanager.showhidden.value
        config.plugins.advancedfilemanager.showhidden.value = not current
        config.plugins.advancedfilemanager.showhidden.save()
        
        self.dual_pane.refresh()
        status = "Showing hidden files" if not current else "Hiding hidden files"
        self["status"].setText(status)
    
    def showBookmarks(self):
        """Show bookmarks"""
        self.session.open(MessageBox, "Bookmarks feature coming soon", MessageBox.TYPE_INFO)
    
    def showNetworkMenu(self):
        """Show network menu"""
        self.session.open(MessageBox, "Network features coming soon", MessageBox.TYPE_INFO)
    
    def showTrash(self):
        """Show trash contents"""
        if not self.trash_manager:
            self.session.open(MessageBox, "Trash is disabled", MessageBox.TYPE_INFO)
            return
        
        try:
            items = self.trash_manager.list_trash()
            if not items:
                self.session.open(MessageBox, "Trash is empty", MessageBox.TYPE_INFO)
            else:
                text = "\n".join([f"{item['trash_name']} ({format_size(item['size'])})" for item in items[:20]])
                if len(items) > 20:
                    text += f"\n... and {len(items) - 20} more items"
                self.session.open(MessageBox, text, MessageBox.TYPE_INFO, title="Trash Contents")
        except Exception as e:
            self.logger.error(f"Cannot show trash: {e}")
            self.session.open(MessageBox, f"Cannot show trash: {e}", MessageBox.TYPE_ERROR)
    
    def openSettings(self):
        """Open settings"""
        try:
            from .setup_wizard import SetupWizard
            self.session.open(SetupWizard)
        except ImportError as e:
            self.logger.error(f"Cannot open settings: {e}")
            self.session.open(MessageBox, "Settings not available", MessageBox.TYPE_ERROR)
    
    def copySelected(self):
        """Copy selected items to opposite panel"""
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
            self["status"].setText("No items selected")
            return
        
        if config.plugins.advancedfilemanager.confirm_overwrite.value:
            self.session.openWithCallback(
                lambda x: self.doCopy(selected, src_path, dst_path) if x else None,
                MessageBox,
                "Copy %d items to %s?" % (len(selected), dst_path),
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
                # Security check
                is_safe, reason = self.security.is_safe_operation(src, dst_path, 'copy')
                if not is_safe:
                    failed.append((src, reason))
                    continue
                
                dst = os.path.join(dst_path, os.path.basename(src))
                self.file_ops.copy(src, dst)
                success += 1
            except FileOperationError as e:
                failed.append((src, str(e)))
            except Exception as e:
                self.logger.error(f"Unexpected copy error: {e}")
                failed.append((src, str(e)))
        
        # Refresh
        self.dual_pane.refresh()
        
        # Status
        if failed:
            self["status"].setText("Copied %d/%d items (%d failed)" % (success, len(items), len(failed)))
            # Show first few errors
            if len(failed) <= 3:
                error_msg = "\n".join([f"{os.path.basename(item[0])}: {item[1]}" for item in failed])
                self.session.open(MessageBox, f"Copy errors:\n{error_msg}", MessageBox.TYPE_WARNING)
        else:
            self["status"].setText("Copied %d items successfully" % success)
    
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
            self["status"].setText("No items selected")
            return
        
        self.session.openWithCallback(
            lambda x: self.doMove(selected, src_path, dst_path) if x else None,
            MessageBox,
            "Move %d items to %s?" % (len(selected), dst_path),
            MessageBox.TYPE_YESNO
        )
    
    def doMove(self, items, src_path, dst_path):
        """Perform move operation"""
        success = 0
        failed = []
        
        for src in items:
            try:
                # Security check
                is_safe, reason = self.security.is_safe_operation(src, dst_path, 'move')
                if not is_safe:
                    failed.append((src, reason))
                    continue
                
                dst = os.path.join(dst_path, os.path.basename(src))
                self.file_ops.move(src, dst)
                success += 1
            except FileOperationError as e:
                failed.append((src, str(e)))
            except Exception as e:
                self.logger.error(f"Unexpected move error: {e}")
                failed.append((src, str(e)))
        
        # Clear selections
        self.dual_pane.deselect_all()
        self.dual_pane.refresh()
        
        if failed:
            self["status"].setText("Moved %d/%d items (%d failed)" % (success, len(items), len(failed)))
        else:
            self["status"].setText("Moved %d items" % success)
    
    def deleteSelected(self):
        """Delete selected items"""
        selected = self.dual_pane.get_active_selections()
        
        if not selected:
            current = self.getCurrentItem()
            if current and not current.get('is_parent'):
                selected = {current['path']}
        
        if not selected:
            self["status"].setText("No items selected")
            return
        
        if config.plugins.advancedfilemanager.confirm_delete.value:
            self.session.openWithCallback(
                lambda x: self.doDelete(selected) if x else None,
                MessageBox,
                "Delete %d items?" % len(selected),
                MessageBox.TYPE_YESNO
            )
        else:
            self.doDelete(selected)
    
    def doDelete(self, items):
        """Perform delete operation"""
        success = 0
        failed = []
        
        for path in items:
            try:
                # Security check
                is_safe, reason = self.security.is_safe_operation(path, operation='delete')
                if not is_safe:
                    failed.append((path, reason))
                    continue
                
                if self.trash_manager:
                    self.trash_manager.trash(path)
                else:
                    self.file_ops.delete(path, use_trash=False)
                success += 1
            except (FileOperationError, TrashError) as e:
                failed.append((path, str(e)))
            except Exception as e:
                self.logger.error(f"Unexpected delete error: {e}")
                failed.append((path, str(e)))
        
        # Clear selections
        self.dual_pane.deselect_all()
        self.dual_pane.refresh()
        
        if failed:
            self["status"].setText("Deleted %d/%d items (%d failed)" % (success, len(items), len(failed)))
        else:
            self["status"].setText("Deleted %d items" % success)
    
    def showFileInfo(self):
        """Show file information"""
        current = self.getCurrentItem()
        if not current:
            return
        
        try:
            info = self.file_ops.get_file_info(current['path'])
            
            text = []
            text.append("Name: %s" % info['name'])
            text.append("Path: %s" % info['path'])
            text.append("Size: %s" % format_size(info['size']))
            text.append("Modified: %s" % format_date(info['modified']))
            text.append("Permissions: %s" % info['permissions'])
            text.append("Type: %s" % ("Directory" if info['is_dir'] else "File"))
            
            if info.get('mime_type'):
                text.append("MIME Type: %s" % info['mime_type'])
            
            self.session.open(
                MessageBox,
                "\n".join(text),
                MessageBox.TYPE_INFO,
                title="File Information"
            )
            
        except FileOperationError as e:
            self.logger.error(f"Cannot get file info: {e}")
            self.session.open(MessageBox, f"Cannot get file info: {e}", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.logger.error(f"Unexpected error getting file info: {e}")
            self.session.open(MessageBox, f"Error: {e}", MessageBox.TYPE_ERROR)
    
    def getCurrentItem(self):
        """Get current item from active panel"""
        files = self.dual_pane.get_active_files()
        list_widget = self.dual_pane.get_active_list()
        
        try:
            index = list_widget.getSelectionIndex()
            if 0 <= index < len(files):
                return files[index]
        except:
            pass
        
        return None
    
    def moveUp(self):
        try:
            self.dual_pane.get_active_list().up()
            self.updateStatus()
        except:
            pass
    
    def moveDown(self):
        try:
            self.dual_pane.get_active_list().down()
            self.updateStatus()
        except:
            pass
    
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
        try:
            self.dual_pane.get_active_list().pageUp()
            self.updateStatus()
        except:
            pass
    
    def pageDown(self):
        try:
            self.dual_pane.get_active_list().pageDown()
            self.updateStatus()
        except:
            pass
    
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
        self["status"].setText("Refreshed")
    
    def updateStatus(self):
        """Update status bar"""
        try:
            panel = self.dual_pane.active_panel
            files = self.dual_pane.get_active_files()
            selections = self.dual_pane.get_active_selections()
            
            count = len([f for f in files if not f.get('is_parent')])
            sel_count = len(selections)
            
            status = "%s panel: %d items" % (panel.upper(), count)
            if sel_count > 0:
                status += " (%d selected)" % sel_count
            
            self["status"].setText(status)
            
            # Update panel info
            info_text = "%d items" % count
            if panel == 'left':
                self["left_info"].setText(info_text)
            else:
                self["right_info"].setText(info_text)
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def close(self):
        """Clean up and close"""
        try:
            # Save cache
            if self.cache_manager:
                try:
                    self.cache_manager.save_cache()
                except:
                    pass
            
            # Save last path
            try:
                config.plugins.advancedfilemanager.lastpath.value = self.dual_pane.left_path
                config.plugins.advancedfilemanager.save()
            except:
                pass
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            Screen.close(self)