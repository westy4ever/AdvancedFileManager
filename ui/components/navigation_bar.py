# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from enigma import eLabel, eSize, ePoint, gFont

class NavigationBar(GUIComponent):
    """
    Navigation breadcrumb bar for showing current path
    Allows quick navigation to parent directories
    """
    
    def __init__(self):
        GUIComponent.__init__(self)
        self.path = "/"
        self.path_parts = []
        self.click_callbacks = []
    
    def set_path(self, path):
        """Update displayed path"""
        self.path = path
        self.path_parts = self._split_path(path)
        self.update_display()
    
    def _split_path(self, path):
        """Split path into navigable components"""
        parts = []
        current = ""
        
        for component in path.split('/'):
            if component:
                current += "/" + component
                parts.append({
                    'name': component,
                    'path': current
                })
        
        return parts
    
    def update_display(self):
        """Update the visual display"""
        # In a full implementation, this would render clickable breadcrumbs
        # For now, just show the path
        if hasattr(self, 'text'):
            self.text = self.path
    
    def get_current_path(self):
        return self.path
    
    def get_parent_path(self):
        """Get parent directory path"""
        if len(self.path_parts) > 1:
            return self.path_parts[-2]['path']
        return "/"
    
    def on_click(self, index):
        """Handle click on breadcrumb"""
        if 0 <= index < len(self.path_parts):
            path = self.path_parts[index]['path']
            for callback in self.click_callbacks:
                callback(path)
    
    GUI_WIDGET = eLabel
    
    def postWidgetCreate(self, instance):
        instance.setText(self.path)
        instance.setFont(gFont("Regular", 20))
    
    def preWidgetRemove(self, instance):
        pass