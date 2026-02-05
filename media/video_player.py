# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config
from enigma import eTimer, eServiceReference, iPlayableService, iServiceInformation, getDesktop
from ServiceReference import ServiceReference
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarNotifications
from Screens.MoviePlayer import MoviePlayer
import os
import json

# Import our logger and subtitle manager
from ..utils.logger import Logger
from .subtitle_manager import SubtitleManager

class AdvancedVideoPlayer(MoviePlayer):
    """
    Enhanced video player with advanced subtitle controls and file manager integration
    """
    
    skin = """
    <screen name="AdvancedVideoPlayer" position="0,0" size="1920,1080" title="Video Player" flags="wfNoBorder">
        <!-- Subtitle Display Area -->
        <widget name="subtitle_label" position="200,900" size="1520,120" font="Regular;32" foregroundColor="#ffffff" 
                backgroundColor="#000000" transparent="1" halign="center" valign="center" zPosition="10" />
        
        <!-- OSD Control Bar -->
        <eLabel position="200,800" size="1520,200" backgroundColor="#000000" transparent="1" zPosition="5" />
        
        <!-- Progress Bar -->
        <widget source="progress" render="Slider" position="300,850" size="1320,15" borderWidth="2" 
                backgroundColor="#333333" foregroundColor="#00ff00" zPosition="6" />
        
        <!-- Time Display -->
        <widget source="current_time" render="Label" position="300,880" size="150,30" font="Regular;24" 
                foregroundColor="#ffffff" zPosition="6" />
        <widget source="total_time" render="Label" position="1470,880" size="150,30" font="Regular;24" 
                foregroundColor="#ffffff" halign="right" zPosition="6" />
        
        <!-- File Info -->
        <widget source="filename" render="Label" position="300,920" size="1000,30" font="Regular;26" 
                foregroundColor="#ffffff" zPosition="6" />
        
        <!-- Subtitle Status -->
        <widget source="subtitle_status" render="Label" position="300,960" size="800,25" font="Regular;20" 
                foregroundColor="#ffff00" zPosition="6" />
        
        <!-- Control Hints -->
        <widget source="controls" render="Label" position="300,1000" size="1320,25" font="Regular;18" 
                foregroundColor="#aaaaaa" halign="center" zPosition="6" />
    </screen>
    """
    
    def __init__(self, session, service, file_path=None, playlist=None, subtitles=None):
        # Initialize parent MoviePlayer
        MoviePlayer.__init__(self, session, service)
        
        self.session = session
        self.service = service
        self.current_file = file_path or service.getPath()
        self.playlist = playlist or []
        self.current_index = 0
        self.logger = Logger("VideoPlayer")
        
        # Subtitle management
        self.subtitle_manager = subtitles or SubtitleManager()
        self.subtitle_delay = 0
        self.subtitle_enabled = True
        self.external_subtitle_loaded = False
        
        # Player state
        self.is_osd_visible = True
        self.osd_hide_timer = eTimer()
        self.osd_hide_timer.callback.append(self.hide_osd)
        
        # UI Elements
        self["subtitle_label"] = Label("")
        self["progress"] = Slider(0, 100)
        self["current_time"] = Label("0:00:00")
        self["total_time"] = Label("0:00:00")
        self["filename"] = Label(os.path.basename(self.current_file))
        self["subtitle_status"] = Label("Subtitles: None")
        self["controls"] = Label("")
        
        # Additional actions for file manager integration
        self["filemanager_actions"] = HelpableActionMap(self, "AdvancedVideoPlayerActions",
        {
            "subtitle_delay_plus": (self.subtitle_delay_plus, _("Increase subtitle delay")),
            "subtitle_delay_minus": (self.subtitle_delay_minus, _("Decrease subtitle delay")),
            "subtitle_toggle": (self.toggle_subtitles, _("Toggle subtitles on/off")),
            "subtitle_download": (self.download_subtitles, _("Download subtitles online")),
            "subtitle_sync_reset": (self.reset_subtitle_delay, _("Reset subtitle synchronization")),
            "show_playlist": (self.show_playlist, _("Show playlist")),
            "next_file": (self.next_file, _("Next file")),
            "prev_file": (self.prev_file, _("Previous file")),
            "delete_file": (self.delete_current_file, _("Delete current file")),
            "file_info": (self.show_file_info, _("Show file information")),
            "toggle_osd": (self.toggle_osd, _("Toggle on-screen display")),
        }, prio=-1)
        
        # Override some MoviePlayer actions
        self["MoviePlayerActions"] = ActionMap(["MoviePlayerActions"],
        {
            "leavePlayer": self.leavePlayer,
            "movieMenu": self.show_video_menu,
        }, prio=-2)
        
        # Event tracking
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
            iPlayableService.evUpdatedInfo: self.__updatedInfo,
            iPlayableService.evUpdatedEventInfo: self.__updatedEventInfo,
            iPlayableService.evStart: self.__serviceStarted,
            iPlayableService.evEOF: self.__serviceEnded,
        })
        
        # Initialize subtitle system
        self.init_subtitles()
        
        # Start OSD hide timer
        self.osd_hide_timer.start(5000, True)
        
        # Update control hints
        self.update_control_hints()
    
    def init_subtitles(self):
        """Initialize subtitle system for current video"""
        # Try to load external subtitles
        if self.subtitle_manager.load_subtitle(self.current_file):
            self.external_subtitle_loaded = True
            sub_path = self.subtitle_manager.current_subtitle
            self["subtitle_status"].setText(f"Subtitles: {os.path.basename(sub_path)}")
            self.logger.info(f"Loaded external subtitle: {sub_path}")
        else:
            # Check for embedded subtitles
            self.check_embedded_subtitles()
        
        # Apply initial delay
        self.apply_subtitle_delay()
    
    def check_embedded_subtitles(self):
        """Check for embedded subtitles in current service"""
        service = self.session.nav.getCurrentService()
        if service:
            subtitle = service.subtitle()
            if subtitle:
                sublist = subtitle.getSubtitleList()
                if sublist:
                    self["subtitle_status"].setText(f"Subtitles: Embedded ({len(sublist)} tracks)")
                else:
                    self["subtitle_status"].setText("Subtitles: None")
            else:
                self["subtitle_status"].setText("Subtitles: None")
    
    def subtitle_delay_plus(self):
        """Increase subtitle delay by 100ms"""
        self.subtitle_delay += 100
        self.apply_subtitle_delay()
        self.show_osd()
        self["subtitle_status"].setText(f"Subtitle Delay: +{self.subtitle_delay}ms")
        self.logger.info(f"Subtitle delay increased to {self.subtitle_delay}ms")
    
    def subtitle_delay_minus(self):
        """Decrease subtitle delay by 100ms"""
        self.subtitle_delay -= 100
        self.apply_subtitle_delay()
        self.show_osd()
        self["subtitle_status"].setText(f"Subtitle Delay: {self.subtitle_delay}ms")
        self.logger.info(f"Subtitle delay decreased to {self.subtitle_delay}ms")
    
    def reset_subtitle_delay(self):
        """Reset subtitle delay to 0"""
        self.subtitle_delay = 0
        self.apply_subtitle_delay()
        self.show_osd()
        self["subtitle_status"].setText("Subtitle Delay: Reset")
        self.logger.info("Subtitle delay reset")
    
    def apply_subtitle_delay(self):
        """Apply current subtitle delay to player"""
        self.subtitle_manager.delay = self.subtitle_delay
        
        # For embedded subtitles, use Enigma2's subtitle delay if available
        service = self.session.nav.getCurrentService()
        if service:
            subtitle = service.subtitle()
            if subtitle and hasattr(subtitle, 'setSubtitleDelay'):
                subtitle.setSubtitleDelay(self.subtitle_delay)
    
    def toggle_subtitles(self):
        """Toggle subtitles on/off"""
        self.subtitle_enabled = not self.subtitle_enabled
        
        service = self.session.nav.getCurrentService()
        if service:
            subtitle = service.subtitle()
            if subtitle:
                if self.subtitle_enabled:
                    subtitle.enableSubtitles(True)
                    self["subtitle_status"].setText("Subtitles: Enabled")
                else:
                    subtitle.enableSubtitles(False)
                    self["subtitle_status"].setText("Subtitles: Disabled")
        
        self.show_osd()
        self.logger.info(f"Subtitles {'enabled' if self.subtitle_enabled else 'disabled'}")
    
    def download_subtitles(self):
        """Download subtitles from online sources"""
        self.session.openWithCallback(
            self.subtitle_download_callback,
            MessageBox,
            _("Search for subtitles online?\nThis requires internet connection."),
            MessageBox.TYPE_YESNO
        )
    
    def subtitle_download_callback(self, confirmed):
        """Handle subtitle download confirmation"""
        if confirmed:
            # Show language selection
            languages = [
                ("eng", _("English")),
                ("spa", _("Spanish")),
                ("fre", _("French")),
                ("ger", _("German")),
                ("ita", _("Italian")),
                ("por", _("Portuguese")),
                ("rus", _("Russian")),
                ("ara", _("Arabic")),
            ]
            
            self.session.openWithCallback(
                self.subtitle_language_selected,
                ChoiceBox,
                _("Select subtitle language"),
                languages
            )
    
    def subtitle_language_selected(self, selection):
        """Handle language selection for subtitles"""
        if selection:
            lang_code = selection[0]
            self.search_subtitles_online(lang_code)
    
    def search_subtitles_online(self, language):
        """Search and download subtitles from online database"""
        self.session.open(
            MessageBox,
            _("Searching for subtitles...\nLanguage: ") + language,
            MessageBox.TYPE_INFO,
            timeout=3
        )
        
        self.logger.info(f"Subtitle search initiated for language: {language}")
    
    def __updatedInfo(self):
        """Called when service info is updated"""
        self.update_progress()
        self.update_time_display()
    
    def __updatedEventInfo(self):
        """Called when event info is updated"""
        pass
    
    def __serviceStarted(self):
        """Called when playback starts"""
        self.logger.info(f"Playback started: {self.current_file}")
        self.init_subtitles()
    
    def __serviceEnded(self):
        """Called when playback ends"""
        self.logger.info("Playback ended")
        # Auto-play next file if in playlist
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self.next_file()
    
    def update_progress(self):
        """Update progress bar"""
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            if seek:
                length = seek.getLength()
                position = seek.getPlayPosition()
                
                if length[0] == 0 and position[0] == 0:
                    len_secs = length[1] // 90000
                    pos_secs = position[1] // 90000
                    
                    if len_secs > 0:
                        progress = int((pos_secs / len_secs) * 100)
                        self["progress"].setValue(progress)
    
    def update_time_display(self):
        """Update time display labels"""
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            if seek:
                length = seek.getLength()
                position = seek.getPlayPosition()
                
                if length[0] == 0 and position[0] == 0:
                    len_secs = length[1] // 90000
                    pos_secs = position[1] // 90000
                    
                    self["current_time"].setText(self.format_time(pos_secs))
                    self["total_time"].setText(self.format_time(len_secs))
    
    def format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"
    
    def show_osd(self):
        """Show on-screen display"""
        self.is_osd_visible = True
        self.osd_hide_timer.start(5000, True)
    
    def hide_osd(self):
        """Hide on-screen display"""
        self.is_osd_visible = False
    
    def toggle_osd(self):
        """Toggle OSD visibility"""
        if self.is_osd_visible:
            self.hide_osd()
        else:
            self.show_osd()
    
    def update_control_hints(self):
        """Update control hints based on context"""
        hints = []
        
        # Basic controls
        hints.append("▶/❚❚: Play/Pause")
        hints.append("◄/►: Seek")
        
        # Subtitle controls
        hints.append("CH+/CH-: Sub delay")
        hints.append("TEXT: Download subs")
        hints.append("HELP: Toggle subs")
        
        # Navigation
        if len(self.playlist) > 1:
            hints.append("▲/▼: Prev/Next file")
        
        hints.append("EXIT: Stop")
        
        self["controls"].setText(" | ".join(hints))
    
    def next_file(self):
        """Play next file in playlist"""
        if not self.playlist:
            return
        
        new_index = self.current_index + 1
        if new_index >= len(self.playlist):
            new_index = 0
        
        self.play_file_at_index(new_index)
    
    def prev_file(self):
        """Play previous file in playlist"""
        if not self.playlist:
            return
        
        new_index = self.current_index - 1
        if new_index < 0:
            new_index = len(self.playlist) - 1
        
        self.play_file_at_index(new_index)
    
    def play_file_at_index(self, index):
        """Play file at specific playlist index"""
        if index < 0 or index >= len(self.playlist):
            return
        
        self.current_index = index
        next_file = self.playlist[index]
        
        # Create new service reference
        ref = eServiceReference(4097, 0, next_file)
        self.session.nav.playService(ref)
        
        self.current_file = next_file
        self["filename"].setText(os.path.basename(next_file))
        
        # Reset subtitle state
        self.subtitle_delay = 0
        self.external_subtitle_loaded = False
        self.init_subtitles()
        
        self.logger.info(f"Playing next file: {next_file}")
    
    def show_playlist(self):
        """Show playlist screen"""
        if not self.playlist:
            return
        
        playlist_items = []
        for i, file_path in enumerate(self.playlist):
            prefix = "▶ " if i == self.current_index else "  "
            playlist_items.append((prefix + os.path.basename(file_path), file_path))
        
        self.session.openWithCallback(
            self.playlist_selected,
            ChoiceBox,
            _("Playlist"),
            playlist_items
        )
    
    def playlist_selected(self, selection):
        """Handle playlist selection"""
        if selection:
            file_path = selection[1]
            if file_path in self.playlist:
                index = self.playlist.index(file_path)
                self.play_file_at_index(index)
    
    def delete_current_file(self):
        """Delete current file with confirmation"""
        self.session.openWithCallback(
            self.confirm_delete,
            MessageBox,
            _("Delete this file permanently?\n") + os.path.basename(self.current_file),
            MessageBox.TYPE_YESNO
        )
    
    def confirm_delete(self, confirmed):
        """Handle delete confirmation"""
        if confirmed:
            try:
                # Stop playback
                self.session.nav.stopService()
                
                # Delete file
                os.remove(self.current_file)
                
                # Remove from playlist
                if self.current_file in self.playlist:
                    self.playlist.remove(self.current_file)
                
                self.logger.info(f"Deleted file: {self.current_file}")
                
                # Play next file
                if self.playlist:
                    if self.current_index >= len(self.playlist):
                        self.current_index = 0
                    self.play_file_at_index(self.current_index)
                else:
                    self.close()
                    
            except Exception as e:
                self.logger.error(f"Delete failed: {e}")
                self.session.open(
                    MessageBox,
                    _("Delete failed: ") + str(e),
                    MessageBox.TYPE_ERROR
                )
    
    def show_file_info(self):
        """Show detailed file information"""
        try:
            stat = os.stat(self.current_file)
            size_mb = stat.st_size / (1024 * 1024)
            
            info = []
            info.append(f"File: {os.path.basename(self.current_file)}")
            info.append(f"Path: {os.path.dirname(self.current_file)}")
            info.append(f"Size: {size_mb:.2f} MB")
            info.append(f"Modified: {self.format_timestamp(stat.st_mtime)}")
            
            # Video info from service
            service = self.session.nav.getCurrentService()
            if service:
                info_obj = service.info()
                if info_obj:
                    width = info_obj.getInfo(iServiceInformation.sVideoWidth)
                    height = info_obj.getInfo(iServiceInformation.sVideoHeight)
                    if width > 0 and height > 0:
                        info.append(f"Resolution: {width}x{height}")
            
            self.session.open(
                MessageBox,
                "\n".join(info),
                MessageBox.TYPE_INFO
            )
            
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
    
    def format_timestamp(self, timestamp):
        """Format Unix timestamp to readable date"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    def show_video_menu(self):
        """Show video options menu"""
        options = [
            (_("Audio track"), self.show_audio_menu),
            (_("Subtitle track"), self.show_subtitle_menu),
            (_("Video settings"), self.show_video_settings),
            (_("Bookmark"), self.add_bookmark),
        ]
        
        self.session.openWithCallback(
            self.menu_callback,
            ChoiceBox,
            _("Video Options"),
            options
        )
    
    def menu_callback(self, selection):
        """Handle menu selection"""
        if selection:
            selection[1]()
    
    def show_audio_menu(self):
        """Show audio track selection"""
        if hasattr(self, 'switchAudio'):
            self.switchAudio()
    
    def show_subtitle_menu(self):
        """Show subtitle track selection"""
        if hasattr(self, 'subtitleSelection'):
            self.subtitleSelection()
    
    def show_video_settings(self):
        """Show video settings"""
        pass
    
    def add_bookmark(self):
        """Add current position to bookmarks"""
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            if seek:
                pos = seek.getPlayPosition()
                if pos[0] == 0:
                    position = pos[1] // 90000
                    self.logger.info(f"Bookmark added at {position}s for {self.current_file}")
                    
                    self.session.open(
                        MessageBox,
                        _("Bookmark added at ") + self.format_time(position),
                        MessageBox.TYPE_INFO,
                        timeout=2
                    )
    
    def leavePlayer(self):
        """Override leavePlayer to confirm exit"""
        self.session.openWithCallback(
            self.leavePlayerConfirmed,
            MessageBox,
            _("Stop playback and return to file manager?"),
            MessageBox.TYPE_YESNO
        )
    
    def leavePlayerConfirmed(self, answer):
        """Handle exit confirmation"""
        if answer:
            self.close()
    
    def handleLeave(self, how):
        """Handle player exit"""
        self.close()