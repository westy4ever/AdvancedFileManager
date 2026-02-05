# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.Sources.List import List
from Components.config import config
from enigma import eTimer, eServiceReference, iPlayableService, iServiceInformation
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import os

# Import our logger
from ..utils.logger import Logger

class AudioPlayer(Screen):
    skin = """
    <screen name="AudioPlayer" position="center,center" size="900,600" title="Audio Player" flags="wfNoBorder">
        <!-- Background -->
        <eLabel position="0,0" size="900,600" backgroundColor="#1a1a1a" />
        
        <!-- Header -->
        <eLabel position="0,0" size="900,60" backgroundColor="#2a2a2a" />
        <widget source="title" render="Label" position="20,15" size="860,30" font="Regular;26" foregroundColor="#ffffff" halign="center" />
        
        <!-- Album Art / Visualization Area -->
        <eLabel position="20,80" size="300,300" backgroundColor="#000000" />
        <widget name="album_art" position="20,80" size="300,300" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AdvancedFileManager/icons/no_cover.png" alphatest="blend" />
        
        <!-- Track Info -->
        <widget source="artist" render="Label" position="340,100" size="540,40" font="Regular;24" foregroundColor="#00ffff" />
        <widget source="album" render="Label" position="340,150" size="540,35" font="Regular;22" foregroundColor="#aaaaaa" />
        <widget source="title" render="Label" position="340,200" size="540,40" font="Regular;26" foregroundColor="#ffffff" />
        <widget source="genre" render="Label" position="340,250" size="540,30" font="Regular;20" foregroundColor="#888888" />
        <widget source="year" render="Label" position="340,290" size="200,30" font="Regular;20" foregroundColor="#888888" />
        
        <!-- Progress Bar -->
        <widget source="progress" render="Slider" position="340,340" size="540,10" borderWidth="1" />
        <widget source="current_time" render="Label" position="340,360" size="100,25" font="Regular;18" foregroundColor="#aaaaaa" />
        <widget source="total_time" render="Label" position="780,360" size="100,25" font="Regular;18" foregroundColor="#aaaaaa" halign="right" />
        
        <!-- Playlist -->
        <eLabel position="20,400" size="860,140" backgroundColor="#2a2a2a" />
        <widget source="playlist" render="Listbox" position="25,405" size="850,130" scrollbarMode="showOnDemand">
            <convert type="TemplatedMultiContent">
                {"template": [
                    MultiContentEntryText(pos=(5,2), size=(500,24), font=0, text=1),
                    MultiContentEntryText(pos=(510,2), size=(200,24), font=0, text=2, color=0x00aaaaaa),
                    MultiContentEntryText(pos=(720,2), size=(100,24), font=0, text=3, color=0x00888888, flags=RT_HALIGN_RIGHT)
                ],
                "fonts": [gFont("Regular",20)],
                "itemHeight": 28}
            </convert>
        </widget>
        
        <!-- Controls Info -->
        <widget source="status" render="Label" position="20,550" size="860,30" font="Regular;18" foregroundColor="#666666" halign="center" />
        
        <!-- Color Buttons -->
        <eLabel position="0,580" size="900,20" backgroundColor="#333333" />
    </screen>
    """
    
    def __init__(self, session, file_path=None, playlist=None):
        Screen.__init__(self, session)
        self.session = session
        self.logger = Logger("AudioPlayer")
        
        # Player state
        self.current_file = file_path
        self.playlist = playlist or []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        
        # Audio service
        self.service = None
        self.seek_target = None
        
        # UI Elements
        self["title"] = Label("Audio Player")
        self["artist"] = Label("Unknown Artist")
        self["album"] = Label("Unknown Album")
        self["genre"] = Label("")
        self["year"] = Label("")
        self["current_time"] = Label("0:00")
        self["total_time"] = Label("0:00")
        self["progress"] = Slider(0, 100)
        self["playlist"] = List([])
        self["status"] = Label("OK: Play/Pause | Stop: Stop | Left/Right: Seek | Up/Down: Playlist | Exit: Close")
        
        # Actions
        self["actions"] = ActionMap(["WizardActions", "MediaPlayerActions", "DirectionActions", "ColorActions"],
        {
            "ok": self.toggle_play_pause,
            "stop": self.stop,
            "up": self.prev_track,
            "down": self.next_track,
            "left": self.seek_backward,
            "right": self.seek_forward,
            "back": self.close,
            "red": self.close,
            "green": self.toggle_play_pause,
            "yellow": self.stop,
            "blue": self.show_playlist,
            "pageUp": self.prev_track,
            "pageDown": self.next_track,
        }, -1)
        
        # Update timer
        self.update_timer = eTimer()
        self.update_timer.callback.append(self.update_progress)
        
        # Build playlist if single file
        if file_path and not playlist:
            self.build_playlist_from_file(file_path)
        
        self.update_playlist_ui()
        
        # Start playback if file provided
        if self.playlist:
            self.play_index(0)
    
    def build_playlist_from_file(self, file_path):
        """Build playlist from directory of current file"""
        directory = os.path.dirname(file_path)
        audio_exts = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma']
        
        try:
            files = sorted([f for f in os.listdir(directory) 
                          if os.path.splitext(f)[1].lower() in audio_exts])
            
            for f in files:
                full_path = os.path.join(directory, f)
                self.playlist.append({
                    'path': full_path,
                    'title': self.get_metadata(full_path).get('title', os.path.splitext(f)[0]),
                    'artist': self.get_metadata(full_path).get('artist', 'Unknown'),
                    'duration': self.get_metadata(full_path).get('duration', '0:00')
                })
                
                # Set current index
                if full_path == file_path:
                    self.current_index = len(self.playlist) - 1
                    
        except Exception as e:
            self.logger.error(f"Error building playlist: {e}")
            # Add single file if directory scan fails
            self.playlist.append({
                'path': file_path,
                'title': os.path.basename(file_path),
                'artist': 'Unknown',
                'duration': '0:00'
            })
    
    def get_metadata(self, file_path):
        """Extract metadata from audio file"""
        metadata = {
            'title': os.path.splitext(os.path.basename(file_path))[0],
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'genre': '',
            'year': '',
            'duration': '0:00'
        }
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                metadata.update(self._read_mp3_metadata(file_path))
            elif ext == '.flac':
                metadata.update(self._read_flac_metadata(file_path))
            elif ext in ['.m4a', '.mp4']:
                metadata.update(self._read_mp4_metadata(file_path))
                
        except Exception as e:
            self.logger.error(f"Metadata read error: {e}")
        
        return metadata
    
    def _read_mp3_metadata(self, file_path):
        """Read ID3 tags from MP3"""
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3
            
            audio = MP3(file_path)
            tags = ID3(file_path) if audio.tags else {}
            
            def get_tag(tag_id, default=''):
                if tag_id in tags:
                    return str(tags[tag_id].text[0]) if tags[tag_id].text else default
                return default
            
            duration = int(audio.info.length) if audio.info else 0
            minutes, seconds = divmod(duration, 60)
            
            return {
                'title': get_tag('TIT2', os.path.splitext(os.path.basename(file_path))[0]),
                'artist': get_tag('TPE1', 'Unknown Artist'),
                'album': get_tag('TALB', 'Unknown Album'),
                'genre': get_tag('TCON'),
                'year': get_tag('TDRC') or get_tag('TYER'),
                'duration': f"{minutes}:{seconds:02d}"
            }
        except:
            return {}
    
    def _read_flac_metadata(self, file_path):
        """Read Vorbis comments from FLAC"""
        try:
            from mutagen.flac import FLAC
            
            audio = FLAC(file_path)
            duration = int(audio.info.length) if audio.info else 0
            minutes, seconds = divmod(duration, 60)
            
            return {
                'title': audio.get('title', [os.path.splitext(os.path.basename(file_path))[0]])[0],
                'artist': audio.get('artist', ['Unknown Artist'])[0],
                'album': audio.get('album', ['Unknown Album'])[0],
                'genre': audio.get('genre', [''])[0],
                'year': audio.get('date', [''])[0],
                'duration': f"{minutes}:{seconds:02d}"
            }
        except:
            return {}
    
    def _read_mp4_metadata(self, file_path):
        """Read metadata from MP4/M4A"""
        try:
            from mutagen.mp4 import MP4
            
            audio = MP4(file_path)
            duration = int(audio.info.length) if audio.info else 0
            minutes, seconds = divmod(duration, 60)
            
            return {
                'title': audio.get('\xa9nam', [os.path.splitext(os.path.basename(file_path))[0]])[0],
                'artist': audio.get('\xa9ART', ['Unknown Artist'])[0],
                'album': audio.get('\xa9alb', ['Unknown Album'])[0],
                'genre': audio.get('\xa9gen', [''])[0],
                'year': audio.get('\xa9day', [''])[0],
                'duration': f"{minutes}:{seconds:02d}"
            }
        except:
            return {}
    
    def update_playlist_ui(self):
        """Update playlist listbox"""
        list_data = []
        for i, track in enumerate(self.playlist):
            # Mark current track
            prefix = "▶ " if i == self.current_index else "  "
            list_data.append((
                i,
                prefix + track['title'],
                track['artist'],
                track['duration']
            ))
        self["playlist"].setList(list_data)
    
    def play_index(self, index):
        """Play track at specific index"""
        if not self.playlist or index >= len(self.playlist):
            return
        
        self.current_index = index
        track = self.playlist[index]
        self.current_file = track['path']
        
        # Stop current playback
        self.stop()
        
        # Update UI with metadata
        metadata = self.get_metadata(self.current_file)
        self["title"].setText(metadata.get('title', track['title']))
        self["artist"].setText(metadata.get('artist', track['artist']))
        self["album"].setText(metadata.get('album', ''))
        self["genre"].setText(metadata.get('genre', ''))
        self["year"].setText(metadata.get('year', ''))
        
        # Start playback using Enigma2 service
        self.service = eServiceReference(4097, 0, self.current_file)
        self.session.nav.playService(self.service)
        self.is_playing = True
        self.is_paused = False
        
        # Start progress updates
        self.update_timer.start(1000, False)
        self.update_playlist_ui()
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if not self.is_playing:
            if self.current_file:
                self.play_index(self.current_index)
        else:
            service = self.session.nav.getCurrentService()
            if service:
                seek = service.seek()
                if seek:
                    if self.is_paused:
                        self.session.nav.playService(self.service)
                        self.is_paused = False
                        self.update_timer.start(1000, False)
                    else:
                        self.session.nav.stopService()
                        self.is_paused = True
                        self.update_timer.stop()
    
    def stop(self):
        """Stop playback"""
        self.session.nav.stopService()
        self.is_playing = False
        self.is_paused = False
        self.update_timer.stop()
        self["current_time"].setText("0:00")
        self["progress"].setValue(0)
    
    def next_track(self):
        """Play next track"""
        if self.playlist:
            next_index = (self.current_index + 1) % len(self.playlist)
            self.play_index(next_index)
    
    def prev_track(self):
        """Play previous track"""
        if self.playlist:
            prev_index = (self.current_index - 1) % len(self.playlist)
            self.play_index(prev_index)
    
    def seek_forward(self):
        """Seek forward 10 seconds"""
        self._seek(10)
    
    def seek_backward(self):
        """Seek backward 10 seconds"""
        self._seek(-10)
    
    def _seek(self, seconds):
        """Seek by specified seconds"""
        if not self.is_playing:
            return
        
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            if seek:
                current = seek.getPlayPosition()
                if current[0] == 0:
                    new_pos = current[1] + (seconds * 90000)
                    seek.seekTo(new_pos)
    
    def update_progress(self):
        """Update progress bar and time display"""
        if not self.is_playing:
            return
        
        service = self.session.nav.getCurrentService()
        if service:
            seek = service.seek()
            info = service.info()
            
            if seek and info:
                # Get current position
                pos = seek.getPlayPosition()
                if pos[0] == 0:
                    current_pts = pos[1]
                    current_sec = current_pts // 90000
                    minutes, seconds = divmod(current_sec, 60)
                    self["current_time"].setText(f"{minutes}:{seconds:02d}")
                
                # Get duration
                length = info.getLength()
                if length[0] == 0:
                    total_sec = length[1] // 90000
                    minutes, seconds = divmod(total_sec, 60)
                    self["total_time"].setText(f"{minutes}:{seconds:02d}")
                    
                    # Update progress bar
                    if total_sec > 0:
                        progress = int((current_sec / total_sec) * 100)
                        self["progress"].setValue(progress)
                
                # Check if track ended
                if current_sec >= (length[1] // 90000) - 1:
                    self.next_track()
    
    def show_playlist(self):
        """Show full playlist view"""
        pass
    
    def close(self):
        """Clean up and close"""
        self.stop()
        self.update_timer.stop()
        Screen.close(self)