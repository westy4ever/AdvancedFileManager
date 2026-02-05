# -*- coding: utf-8 -*-
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config
from enigma import eTimer, eServiceReference, iPlayableService, iServiceInformation, getDesktop
from ServiceReference import ServiceReference
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarNotifications

# Try to import MoviePlayer
try:
    from Screens.MoviePlayer import MoviePlayer
    HAS_MOVIEPLAYER = True
except ImportError:
    # Fallback for systems without MoviePlayer
    from Screens.Screen import Screen
    MoviePlayer = Screen
    HAS_MOVIEPLAYER = False

import os
import json

# Import our logger and subtitle manager
from ..utils.logger import Logger

try:
    from .subtitle_manager import SubtitleManager
    HAS_SUBTITLE_MANAGER = True
except ImportError:
    HAS_SUBTITLE_MANAGER = False

class AdvancedVideoPlayer(MoviePlayer if HAS_MOVIEPLAYER else Screen):
    """
    Enhanced video player with advanced subtitle controls and file manager integration
    """
    
    skin = """
    <screen name="AdvancedVideoPlayer" position="0,0" size="1920,1080" title="Video Player" flags="wfNoBorder">
        <!-- Subtitle Display Area -->
        <widget source="subtitle_label" render="Label" position="200,900" size="1520,120" font="Regular;32" foregroundColor="#ffffff" 
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
        # Initialize parent MoviePlayer if available
        if HAS_MOVIEPLAYER:
            MoviePlayer.__init__(self, session, service)
        else:
            Screen.__init__(self, session)
        
        self.session = session
        self.service = service
        self.current_file = file_path or service.getPath()
        self.playlist = playlist or []
        self.current_index = 0
        self.logger = Logger("VideoPlayer")
        
        # Subtitle management
        if HAS_SUBTITLE_MANAGER:
            self.subtitle_manager = subtitles or SubtitleManager()
        else:
            self.subtitle_manager = None
        
        self.subtitle_delay = 0
        self.subtitle_enabled = True
        self.external_subtitle_loaded = False
        
        # Player state
        self.is_osd_visible = True
        self.osd_hide_timer = eTimer()
        self.osd_hide_timer.callback.append(self.hide_osd)
        
        # UI Elements
        self["subtitle_label"] = StaticText("")
        self["progress"] = StaticText("0")
        self["current_time"] = StaticText("0:00:00")
        self["total_time"] = StaticText("0:00:00")
        self["filename"] = StaticText(os.path.basename(self.current_file))
        self["subtitle_status"] = StaticText("Subtitles: None")
        self["controls"] = StaticText("")
        
        # Additional actions for file manager integration
        self["filemanager_actions"] = ActionMap(["MoviePlayerActions", "DirectionActions"],
        {
            "leavePlayer": self.leavePlayer,
            "channelUp": self.subtitle_delay_plus,
            "channelDown": self.subtitle_delay_minus,
            "up": self.next_file,
            "down": self.prev_file,
            "info": self.show_file_info,
            "menu": self.show_video_menu,
        }, prio=-1)
        
        # Event tracking
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
            iPlayableService.evUpdatedInfo: self.__updatedInfo,
            iPlayableService.evStart: self.__serviceStarted,
            iPlayableService.evEOF: self.__serviceEnded,
        })
        
        # Initialize subtitle system
        if self.subtitle_manager:
            self.init_subtitles()
        
        # Start OSD hide timer
        self.osd_hide_timer.start(5000, True)
        
        # Update control hints
        self.update_control_hints()
    
    def init_subtitles(self):
        """Initialize subtitle system for current video"""
        if not self.subtitle_manager:
            return
        
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
    
    def apply_subtitle_delay(self):
        """Apply current subtitle delay to player"""
        if not self.subtitle_manager:
            return
        
        self.subtitle_manager.delay = self.subtitle_delay
        
        # For embedded subtitles, use Enigma2's subtitle delay if available
        service = self.session.nav.getCurrentService()
        if service:
            subtitle = service.subtitle()
            if subtitle and hasattr(subtitle, 'setSubtitleDelay'):
                try:
                    subtitle.setSubtitleDelay(self.subtitle_delay)
                except:
                    pass
    
    def __updatedInfo(self):
        """Called when service info is updated"""
        self.update_progress()
        self.update_time_display()
    
    def __serviceStarted(self):
        """Called when playback starts"""
        self.logger.info(f"Playback started: {self.current_file}")
        if self.subtitle_manager:
            self.init_subtitles()
    
    def __serviceEnded(self):
        """Called when playback ends"""
        self.logger.info("Playback ended")
        # Auto-play next file if in playlist
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self.next_file()
        else:
            self.close()
    
    def update_progress(self):
        """Update progress bar"""
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            if seek:
                length = seek.getLength()
                position = seek.getPlayPosition()
                
                if length[0] == 0 and position[0] == 0 and length[1] > 0:
                    len_secs = length[1] // 90000
                    pos_secs = position[1] // 90000
                    
                    if len_secs > 0:
                        progress = int((pos_secs / len_secs) * 100)
                        self["progress"].setText(str(progress))
    
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
    
    def update_control_hints(self):
        """Update control hints based on context"""
        hints = []
        
        hints.append("OK: Play/Pause")
        hints.append("CH+/-: Sub delay")
        
        if len(self.playlist) > 1:
            hints.append("Up/Down: Prev/Next")
        
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
        if self.subtitle_manager:
            self.init_subtitles()
        
        self.logger.info(f"Playing next file: {next_file}")
    
    def show_file_info(self):
        """Show detailed file information"""
        try:
            stat = os.stat(self.current_file)
            size_mb = stat.st_size / (1024 * 1024)
            
            info = []
            info.append(f"File: {os.path.basename(self.current_file)}")
            info.append(f"Path: {os.path.dirname(self.current_file)}")
            info.append(f"Size: {size_mb:.2f} MB")
            
            # Video info from service
            service = self.session.nav.getCurrentService()
            if service:
                info_obj = service.info()
                if info_obj:
                    try:
                        width = info_obj.getInfo(iServiceInformation.sVideoWidth)
                        height = info_obj.getInfo(iServiceInformation.sVideoHeight)
                        if width > 0 and height > 0:
                            info.append(f"Resolution: {width}x{height}")
                    except:
                        pass
            
            self.session.open(MessageBox, "\n".join(info), MessageBox.TYPE_INFO)
            
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
    
    def show_video_menu(self):
        """Show video options menu"""
        options = [
            ("Audio Track", self.show_audio_menu),
            ("Subtitle Track", self.show_subtitle_menu),
        ]
        
        self.session.openWithCallback(
            lambda choice: choice[1]() if choice else None,
            ChoiceBox,
            "Video Options",
            options
        )
    
    def show_audio_menu(self):
        """Show audio track selection"""
        # Use InfoBarAudioSelection if available
        if hasattr(self, 'audioSelection'):
            try:
                self.audioSelection()
            except:
                self.session.open(MessageBox, "Audio selection not available", MessageBox.TYPE_INFO)
    
    def show_subtitle_menu(self):
        """Show subtitle track selection"""
        # Use InfoBarSubtitleSupport if available
        if hasattr(self, 'subtitleSelection'):
            try:
                self.subtitleSelection()
            except:
                self.session.open(MessageBox, "Subtitle selection not available", MessageBox.TYPE_INFO)
    
    def leavePlayer(self):
        """Override leavePlayer to confirm exit"""
        self.session.openWithCallback(
            self.leavePlayerConfirmed,
            MessageBox,
            "Stop playback?",
            MessageBox.TYPE_YESNO
        )
    
    def leavePlayerConfirmed(self, answer):
        """Handle exit confirmation"""
        if answer:
            self.close()
    
    def close(self):
        """Clean up and close"""
        try:
            self.osd_hide_timer.stop()
        except:
            pass
        
        if HAS_MOVIEPLAYER:
            MoviePlayer.close(self)
        else:
            Screen.close(self)