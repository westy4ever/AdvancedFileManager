# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER
import os

class DualPaneLayout:
    """
    Dual-pane file manager layout handler
    Manages left and right panels with independent navigation
    """
    
    def __init__(self, session, screen, left_path="/media", right_path="/media/hdd"):
        self.session = session
        self.screen = screen
        
        # Panel states
        self.active_panel = 'left'
        self.left_path = left_path
        self.right_path = right_path
        
        # File lists
        self.left_files = []
        self.right_files = []
        
        # Selections
        self.left_selected = set()
        self.right_selected = set()
        
        # UI Components
        self.left_list = None
        self.right_list = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize UI components"""
        # Create menu lists for both panels
        self.left_list = MenuList([])
        self.right_list = MenuList([])
        
        # Add to screen
        self.screen["left_list"] = self.left_list
        self.screen["right_list"] = self.right_list
    
    def refresh(self, panel=None):
        """
        Refresh file lists
        
        Args:
            panel: 'left', 'right', or None for both
        """
        if panel in (None, 'left'):
            self.load_directory('left', self.left_path)
        
        if panel in (None, 'right'):
            self.load_directory('right', self.right_path)
    
    def load_directory(self, panel, path):
        """Load directory into panel"""
        try:
            items = []
            
            # Parent directory
            parent = os.path.dirname(path)
            if parent != path:
                items.append({
                    'name': '..',
                    'path': parent,
                    'is_dir': True,
                    'is_parent': True,
                    'size': 0,
                    'modified': 0
                })
            
            # Directory contents
            try:
                entries = os.listdir(path)
            except PermissionError:
                self.show_error(f"Permission denied: {path}")
                return
            except Exception as e:
                self.show_error(f"Error reading directory: {e}")
                return
            
            # Separate dirs and files
            dirs = []
            files = []
            
            for entry in entries:
                # Skip hidden files if configured
                try:
                    from Components.config import config
                    if not config.plugins.advancedfilemanager.showhidden.value and entry.startswith('.'):
                        continue
                except:
                    if entry.startswith('.'):
                        continue
                
                full_path = os.path.join(path, entry)
                try:
                    stat = os.stat(full_path)
                    is_dir = os.path.isdir(full_path)
                    is_link = os.path.islink(full_path)
                    
                    item = {
                        'name': entry,
                        'path': full_path,
                        'is_dir': is_dir,
                        'is_link': is_link,
                        'size': stat.st_size if not is_dir else 0,
                        'modified': stat.st_mtime,
                        'mode': stat.st_mode
                    }
                    
                    if is_dir:
                        dirs.append(item)
                    else:
                        files.append(item)
                        
                except (OSError, IOError) as e:
                    # Skip files we can't access
                    continue
            
            # Sort
            dirs.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())
            
            items.extend(dirs)
            items.extend(files)
            
            # Update panel
            if panel == 'left':
                self.left_files = items
                self.left_path = path
                if hasattr(self.screen, 'updateLeftPath'):
                    self.screen.updateLeftPath(path)
                self.update_list('left')
            else:
                self.right_files = items
                self.right_path = path
                if hasattr(self.screen, 'updateRightPath'):
                    self.screen.updateRightPath(path)
                self.update_list('right')
            
        except Exception as e:
            self.show_error(f"Error loading directory: {e}")
    
    def update_list(self, panel):
        """Update list display"""
        if panel == 'left':
            items = self.left_files
            selected = self.left_selected
            list_widget = self.left_list
        else:
            items = self.right_files
            selected = self.right_selected
            list_widget = self.right_list
        
        list_data = []
        for item in items:
            is_selected = item['path'] in selected
            
            # Format display
            display = self.format_item(item, is_selected)
            list_data.append((display, item))
        
        list_widget.setList(list_data)
    
    def format_item(self, item, is_selected):
        """Format item for display"""
        name = item['name']
        
        # Add indicators
        if item.get('is_parent'):
            icon = "[..]"
        elif item['is_dir']:
            icon = "[DIR]" if not item.get('is_link') else "[LNK]"
        else:
            icon = "    "
        
        # Format size
        if item['is_dir']:
            size_str = "<DIR>"
        else:
            size = item['size']
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024*1024:
                size_str = f"{size/1024:.1f}K"
            elif size < 1024*1024*1024:
                size_str = f"{size/(1024*1024):.1f}M"
            else:
                size_str = f"{size/(1024*1024*1024):.1f}G"
        
        # Selection indicator
        sel = "[X]" if is_selected else "[ ]"
        
        # Create display string
        display = f"{sel} {icon} {name:<40} {size_str:>10}"
        
        return display
    
    def switch_panel(self):
        """Switch active panel"""
        self.active_panel = 'right' if self.active_panel == 'left' else 'left'
        self.highlight_active_panel()
    
    def highlight_active_panel(self):
        """Visual indication of active panel"""
        # In real implementation, change border colors or backgrounds
        pass
    
    def get_active_list(self):
        """Get currently active list widget"""
        return self.left_list if self.active_panel == 'left' else self.right_list
    
    def get_active_path(self):
        """Get current path of active panel"""
        return self.left_path if self.active_panel == 'left' else self.right_path
    
    def get_active_files(self):
        """Get file list of active panel"""
        return self.left_files if self.active_panel == 'left' else self.right_files
    
    def get_active_selections(self):
        """Get selected items of active panel"""
        return self.left_selected if self.active_panel == 'left' else self.right_selected
    
    def toggle_selection(self):
        """Toggle selection of current item"""
        panel = self.active_panel
        files = self.get_active_files()
        selections = self.get_active_selections()
        list_widget = self.get_active_list()
        
        try:
            current = list_widget.getCurrent()
            if current and len(current) > 1:
                item = current[1]
                path = item['path']
                
                if path in selections:
                    selections.remove(path)
                else:
                    selections.add(path)
                
                self.update_list(panel)
        except Exception as e:
            print(f"Toggle selection error: {e}")
    
    def select_all(self):
        """Select all items in active panel"""
        panel = self.active_panel
        files = self.get_active_files()
        selections = self.get_active_selections()
        
        for item in files:
            if not item.get('is_parent'):
                selections.add(item['path'])
        
        self.update_list(panel)
    
    def deselect_all(self):
        """Clear all selections in active panel"""
        panel = self.active_panel
        selections = self.get_active_selections()
        selections.clear()
        self.update_list(panel)
    
    def invert_selection(self):
        """Invert selection in active panel"""
        panel = self.active_panel
        files = self.get_active_files()
        selections = self.get_active_selections()
        
        all_paths = {item['path'] for item in files if not item.get('is_parent')}
        
        # Invert
        new_selection = all_paths - selections
        selections.clear()
        selections.update(new_selection)
        
        self.update_list(panel)
    
    def get_selected_items(self):
        """Get list of selected file dictionaries"""
        panel = self.active_panel
        files = self.get_active_files()
        selections = self.get_active_selections()
        
        return [f for f in files if f['path'] in selections]
    
    def show_error(self, message):
        """Display error message"""
        # Delegate to screen
        if hasattr(self.screen, 'show_error'):
            self.screen.show_error(message)
        else:
            print(f"Error: {message}")