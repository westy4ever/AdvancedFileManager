# -*- coding: utf-8 -*-
from Components.GUIComponent import GUIComponent
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListbox

class FileItemComponent(GUIComponent):
    """
    Custom GUI component for rendering file items
    Supports icons, selection states, and metadata display
    """
    
    def __init__(self):
        GUIComponent.__init__(self)
        self.l = eListboxPythonMultiContent()
        self.l.setBuildFunc(self.buildEntry)
        self.l.setFont(0, gFont("Regular", 20))
        self.l.setFont(1, gFont("Regular", 18))
        self.l.setItemHeight(28)
        
        # Colors
        self.color_normal = 0xFFFFFF  # White
        self.color_selected = 0x00FF00  # Green
        self.color_directory = 0x00FFFF  # Cyan
        self.color_link = 0xFFAA00  # Orange
        self.color_hidden = 0x888888  # Gray
    
    def buildEntry(self, icon, selected, name, size, date, is_dir=False, is_link=False, is_hidden=False):
        """Build list entry"""
        res = [None]
        
        # Selection checkbox (30px)
        if selected:
            res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 2, 30, 24, 1, RT_HALIGN_CENTER | RT_VALIGN_CENTER, "[X]"))
        else:
            res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 2, 30, 24, 1, RT_HALIGN_CENTER | RT_VALIGN_CENTER, "[ ]"))
        
        # Icon (30px)
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 40, 2, 30, 24, 1, RT_HALIGN_CENTER | RT_VALIGN_CENTER, icon))
        
        # Determine color
        if is_hidden:
            color = self.color_hidden
        elif is_link:
            color = self.color_link
        elif is_dir:
            color = self.color_directory
        else:
            color = self.color_normal
        
        # Name (flexible width)
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 75, 2, 400, 24, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name, color))
        
        # Size (100px, right-aligned)
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 480, 2, 100, 24, 1, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, size, 0xAAAAAA))
        
        # Date (150px)
        res.append((eListboxPythonMultiContent.TYPE_TEXT, 590, 2, 150, 24, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, date, 0x888888))
        
        return res
    
    def getCurrent(self):
        return self.l.getCurrentSelection()
    
    def setList(self, list):
        self.l.setList(list)
    
    def getSelectedIndex(self):
        return self.l.getCurrentSelectionIndex()
    
    def moveToIndex(self, index):
        self.l.moveToIndex(index)
    
    GUI_WIDGET = eListbox
    
    def postWidgetCreate(self, instance):
        instance.setContent(self.l)
        instance.setSelectionEnable(True)
    
    def preWidgetRemove(self, instance):
        instance.setContent(None)