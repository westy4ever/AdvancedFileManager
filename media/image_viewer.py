# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.Sources.StaticText import StaticText
from enigma import eTimer, loadPic, getDesktop
import os
import random

# PIL compatibility fix
try:
    from PIL import Image
    try:
        from PIL.Image import Resampling
        LANCZOS = Resampling.LANCZOS
    except (ImportError, AttributeError):
        LANCZOS = Image.LANCZOS
    
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import our logger
from ..utils.logger import Logger

class ImageViewer(Screen):
    skin = """
    <screen name="ImageViewer" position="0,0" size="1920,1080" title="Image Viewer" flags="wfNoBorder" backgroundColor="#000000">
        <!-- Main Image Display -->
        <widget name="image" position="0,0" size="1920,1080" zPosition="1" alphatest="blend" />
        
        <!-- Info Overlay -->
        <eLabel position="0,0" size="1920,80" backgroundColor="#000000" zPosition="2" transparent="1" />
        <widget source="filename" render="Label" position="20,20" size="1200,40" font="Regular;28" foregroundColor="#ffffff" zPosition="3" />
        <widget source="info" render="Label" position="20,60" size="600,30" font="Regular;22" foregroundColor="#aaaaaa" zPosition="3" />
        
        <!-- Controls Hint -->
        <widget source="controls" render="Label" position="0,1020" size="1920,40" font="Regular;20" foregroundColor="#666666" halign="center" zPosition="3" />
        
        <!-- Zoom Indicator -->
        <widget source="zoom" render="Label" position="1800,20" size="100,30" font="Regular;20" foregroundColor="#ffffff" halign="right" zPosition="3" />
    </screen>
    """
    
    def __init__(self, session, file_path=None, image_list=None):
        Screen.__init__(self, session)
        self.session = session
        self.logger = Logger("ImageViewer")
        
        if not HAS_PIL:
            self.logger.error("PIL/Pillow not available")
            self.close()
            return
        
        # Image state
        self.current_file = file_path
        self.image_list = image_list or []
        self.current_index = 0
        self.zoom_level = 1.0
        self.rotation = 0
        self.slideshow_active = False
        self.slideshow_delay = 5000
        
        # Build image list from directory if single file
        if file_path and not image_list:
            self.build_image_list(file_path)
        
        # Find current index
        if self.current_file in self.image_list:
            self.current_index = self.image_list.index(self.current_file)
        
        # UI Elements
        self["image"] = Pixmap()
        self["filename"] = StaticText("")
        self["info"] = StaticText("")
        self["controls"] = StaticText("◄ ►: Navigate | ▲ ▼: Zoom | 0: Rotate | Play: Slideshow | Exit: Close")
        self["zoom"] = StaticText("100%")
        
        # Actions
        self["actions"] = ActionMap(["WizardActions", "MediaPlayerActions", "ColorActions", "NumberActions"],
        {
            "ok": self.close,
            "back": self.close,
            "left": self.prev_image,
            "right": self.next_image,
            "up": self.zoom_in,
            "down": self.zoom_out,
            "red": self.close,
            "green": self.toggle_slideshow,
            "yellow": self.rotate_image,
            "blue": self.toggle_info,
            "0": self.rotate_image,
            "1": self.fit_to_screen,
            "2": self.original_size,
            "3": self.toggle_shuffle,
            "play": self.toggle_slideshow,
            "stop": self.stop_slideshow,
            "next": self.next_image,
            "previous": self.prev_image,
        }, -1)
        
        # Slideshow timer
        self.slideshow_timer = eTimer()
        self.slideshow_timer.callback.append(self.slideshow_next)
        
        # Hide info timer
        self.hide_timer = eTimer()
        self.hide_timer.callback.append(self.hide_info)
        
        # Load first image
        if self.image_list:
            self.load_image(self.current_index)
    
    def build_image_list(self, file_path):
        """Build list of images in directory"""
        directory = os.path.dirname(file_path)
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        try:
            files = sorted([f for f in os.listdir(directory)
                          if os.path.splitext(f)[1].lower() in image_exts])
            
            self.image_list = [os.path.join(directory, f) for f in files]
            
        except Exception as e:
            self.logger.error(f"Error building image list: {e}")
            self.image_list = [file_path]
    
    def load_image(self, index):
        """Load and display image at index"""
        if not self.image_list or index >= len(self.image_list):
            return
        
        self.current_index = index
        self.current_file = self.image_list[index]
        
        # Reset transformations
        self.zoom_level = 1.0
        self.rotation = 0
        
        try:
            # Load image using PIL for processing
            self.original_image = Image.open(self.current_file)
            
            # Convert to RGB if necessary
            if self.original_image.mode in ('RGBA', 'LA', 'P'):
                self.original_image = self.original_image.convert('RGB')
            
            self.display_image()
            
            # Update UI
            filename = os.path.basename(self.current_file)
            self["filename"].setText(filename)
            
            # Get image info
            width, height = self.original_image.size
            size_kb = os.path.getsize(self.current_file) / 1024
            self["info"].setText(f"{width}x{height} | {size_kb:.1f} KB | {index+1}/{len(self.image_list)}")
            self["zoom"].setText("100%")
            
            # Start hide timer
            self.hide_timer.start(3000, True)
            
        except Exception as e:
            self.logger.error(f"Error loading image: {e}")
            self["info"].setText(f"Error loading image: {e}")
    
    def display_image(self):
        """Display current image with transformations applied"""
        try:
            # Apply transformations
            image = self.original_image.copy()
            
            # Rotate
            if self.rotation != 0:
                image = image.rotate(self.rotation, expand=True)
            
            # Get screen size
            screen_width = getDesktop(0).size().width()
            screen_height = getDesktop(0).size().height()
            
            # Calculate scaled size
            img_width, img_height = image.size
            
            if self.zoom_level == "fit":
                # Fit to screen
                ratio = min(screen_width/img_width, screen_height/img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
            else:
                # Apply zoom
                new_width = int(img_width * self.zoom_level)
                new_height = int(img_height * self.zoom_level)
            
            # Resize with compatibility fix
            if new_width != img_width or new_height != img_height:
                image = image.resize((new_width, new_height), LANCZOS)
            
            # Save to temporary file for Enigma2 display
            temp_path = "/tmp/afm_image_view.jpg"
            image.save(temp_path, "JPEG", quality=95)
            
            # Load into pixmap
            self["image"].instance.setPixmapFromFile(temp_path)
            
        except Exception as e:
            self.logger.error(f"Display error: {e}")
    
    def prev_image(self):
        """Show previous image"""
        if self.image_list:
            new_index = (self.current_index - 1) % len(self.image_list)
            self.load_image(new_index)
            self.stop_slideshow()
    
    def next_image(self):
        """Show next image"""
        if self.image_list:
            new_index = (self.current_index + 1) % len(self.image_list)
            self.load_image(new_index)
            self.stop_slideshow()
    
    def zoom_in(self):
        """Zoom in"""
        if isinstance(self.zoom_level, (int, float)) and self.zoom_level < 5.0:
            self.zoom_level += 0.25
            self.display_image()
            self["zoom"].setText(f"{int(self.zoom_level*100)}%")
            self.show_info()
    
    def zoom_out(self):
        """Zoom out"""
        if isinstance(self.zoom_level, (int, float)) and self.zoom_level > 0.25:
            self.zoom_level -= 0.25
            self.display_image()
            self["zoom"].setText(f"{int(self.zoom_level*100)}%")
            self.show_info()
    
    def fit_to_screen(self):
        """Fit image to screen"""
        self.zoom_level = "fit"
        self.display_image()
        self["zoom"].setText("Fit")
        self.show_info()
    
    def original_size(self):
        """Show original size"""
        self.zoom_level = 1.0
        self.display_image()
        self["zoom"].setText("100%")
        self.show_info()
    
    def rotate_image(self):
        """Rotate image 90 degrees clockwise"""
        self.rotation = (self.rotation + 90) % 360
        self.display_image()
        self.show_info()
    
    def toggle_slideshow(self):
        """Toggle slideshow mode"""
        if self.slideshow_active:
            self.stop_slideshow()
        else:
            self.start_slideshow()
    
    def start_slideshow(self):
        """Start slideshow"""
        self.slideshow_active = True
        self["controls"].setText("Slideshow Active - Press STOP to exit")
        self.slideshow_timer.start(self.slideshow_delay, False)
    
    def stop_slideshow(self):
        """Stop slideshow"""
        self.slideshow_active = False
        self.slideshow_timer.stop()
        self["controls"].setText("◄ ►: Navigate | ▲ ▼: Zoom | 0: Rotate | Play: Slideshow | Exit: Close")
    
    def slideshow_next(self):
        """Advance to next image in slideshow"""
        if self.image_list:
            new_index = (self.current_index + 1) % len(self.image_list)
            self.load_image(new_index)
            self.slideshow_timer.start(self.slideshow_delay, False)
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        if hasattr(self, 'shuffle') and self.shuffle:
            self.image_list.sort()
            self.shuffle = False
            self.current_index = self.image_list.index(self.current_file)
        else:
            random.shuffle(self.image_list)
            self.shuffle = True
            self.current_index = 0
        
        self.show_info()
    
    def show_info(self):
        """Show info overlay"""
        self.hide_timer.start(3000, True)
    
    def hide_info(self):
        """Hide info overlay"""
        pass
    
    def toggle_info(self):
        """Toggle info display"""
        pass
    
    def close(self):
        """Clean up and close"""
        self.stop_slideshow()
        # Clean up temp files
        temp_path = "/tmp/afm_image_view.jpg"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        Screen.close(self)