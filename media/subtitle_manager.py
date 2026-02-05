# -*- coding: utf-8 -*-
import os
import re
from urllib.request import urlopen, Request
from urllib.parse import quote

class SubtitleManager:
    SUPPORTED_FORMATS = ['.srt', '.sub', '.ass', '.ssa', '.txt']
    
    def __init__(self):
        self.current_subtitle = None
        self.delay = 0  # milliseconds
        self.enabled = True
    
    def load_subtitle(self, video_path, subtitle_path=None):
        """Load subtitle for video file"""
        if subtitle_path and os.path.exists(subtitle_path):
            self.current_subtitle = subtitle_path
            return True
        
        # Auto-detect subtitle with same name
        base = os.path.splitext(video_path)[0]
        for ext in self.SUPPORTED_FORMATS:
            sub_path = base + ext
            if os.path.exists(sub_path):
                self.current_subtitle = sub_path
                return True
        
        # Look for subtitle directory
        video_dir = os.path.dirname(video_path)
        subtitle_dirs = ['Subs', 'subtitles', 'Subtitles', 'SUB']
        
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        for sub_dir in subtitle_dirs:
            sub_path = os.path.join(video_dir, sub_dir)
            if os.path.exists(sub_path):
                # Look for matching subtitle in directory
                for file in os.listdir(sub_path):
                    if video_name in file and any(file.endswith(ext) for ext in self.SUPPORTED_FORMATS):
                        full_path = os.path.join(sub_path, file)
                        self.current_subtitle = full_path
                        return True
        
        return False
    
    def adjust_delay(self, delta_ms):
        """Adjust subtitle timing"""
        self.delay += delta_ms
        return self.delay
    
    def get_delay(self):
        """Get current delay in milliseconds"""
        return self.delay
    
    def reset_delay(self):
        """Reset delay to zero"""
        self.delay = 0


class SubtitleConverter:
    """Convert between subtitle formats"""
    
    @staticmethod
    def sub_to_srt(sub_path):
        """Convert MicroDVD/SUB format to SRT"""
        try:
            with open(sub_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            srt_lines = []
            index = 1
            
            for line in lines:
                match = re.match(r'\{(\d+)\}\{(\d+)\}(.+)', line.strip())
                if match:
                    start_frame = int(match.group(1))
                    end_frame = int(match.group(2))
                    text = match.group(3).replace('|', '\n')
                    
                    # Convert frames to time (assuming 25fps)
                    start_time = SubtitleConverter._frames_to_time(start_frame, 25)
                    end_time = SubtitleConverter._frames_to_time(end_frame, 25)
                    
                    srt_lines.append(f"{index}")
                    srt_lines.append(f"{start_time} --> {end_time}")
                    srt_lines.append(text)
                    srt_lines.append("")
                    index += 1
            
            # Write SRT file
            srt_path = os.path.splitext(sub_path)[0] + '.srt'
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            
            return srt_path
            
        except Exception as e:
            print(f"SUB to SRT conversion failed: {e}")
            return None
    
    @staticmethod
    def ass_to_srt(ass_path):
        """Convert ASS/SSA format to SRT"""
        try:
            with open(ass_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            srt_lines = []
            index = 1
            
            # Parse Dialogue lines
            dialogue_pattern = r'Dialogue: \d+,(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.+)'
            
            for match in re.finditer(dialogue_pattern, content):
                start_time = match.group(1).replace('.', ',')
                end_time = match.group(2).replace('.', ',')
                text = match.group(3)
                
                # Remove ASS formatting tags
                text = re.sub(r'\{[^}]*\}', '', text)
                text = text.replace('\\N', '\n')
                
                srt_lines.append(f"{index}")
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(text)
                srt_lines.append("")
                index += 1
            
            srt_path = os.path.splitext(ass_path)[0] + '.srt'
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            
            return srt_path
            
        except Exception as e:
            print(f"ASS to SRT conversion failed: {e}")
            return None
    
    @staticmethod
    def _frames_to_time(frames, fps):
        """Convert frame count to SRT time format"""
        total_seconds = frames / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"