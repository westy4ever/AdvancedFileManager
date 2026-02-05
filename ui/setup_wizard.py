# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.config import config, ConfigYesNo, ConfigText, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Label import Label

class SetupWizard(ConfigListScreen, Screen):
    skin = """
    <screen position="center,center" size="800,600" title="Advanced File Manager Setup">
        <widget name="config" position="20,20" size="760,400" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,430" size="760,100" font="Regular;20" />
        <eLabel position="0,540" size="800,60" backgroundColor="#1a1a1a" />
        <widget source="key_red" render="Label" position="20,550" size="370,40" font="Regular;20" foregroundColor="#ff4444" halign="center" />
        <widget source="key_green" render="Label" position="410,550" size="370,40" font="Regular;20" foregroundColor="#44ff44" halign="center" />
    </screen>
    """
    
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        # Setup configuration options
        self.list = []
        
        # Trash settings
        self.use_trash = ConfigYesNo(default=True)
        self.trash_path = ConfigText(default="/media/.trash")
        
        # View settings
        self.show_hidden = ConfigYesNo(default=False)
        self.default_view = ConfigSelection(default="dual", choices=[("dual", "Dual Pane"), ("single", "Single Pane")])
        
        # Network settings
        self.enable_network = ConfigYesNo(default=True)
        
        # Media settings
        self.enable_media_player = ConfigYesNo(default=True)
        self.auto_load_subtitles = ConfigYesNo(default=True)
        
        # Build config list
        self.list.append(("Use Trash/Recycle Bin", self.use_trash))
        self.list.append(("Trash Directory", self.trash_path))
        self.list.append(("Show Hidden Files", self.show_hidden))
        self.list.append(("Default View Mode", self.default_view))
        self.list.append(("Enable Network Features", self.enable_network))
        self.list.append(("Enable Media Player", self.enable_media_player))
        self.list.append(("Auto-load Subtitles", self.auto_load_subtitles))
        
        ConfigListScreen.__init__(self, self.list)
        
        self["description"] = Label("Configure Advanced File Manager settings")
        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Save")
        
        self["actions"] = ActionMap(["WizardActions", "ColorActions"],
        {
            "red": self.cancel,
            "green": self.save,
            "back": self.cancel,
        }, -2)
    
    def save(self):
        """Save configuration"""
        # Apply settings to config
        config.plugins.advancedfilemanager.use_trash.value = self.use_trash.value
        config.plugins.advancedfilemanager.trash_path.value = self.trash_path.value
        config.plugins.advancedfilemanager.showhidden.value = self.show_hidden.value
        
        config.plugins.advancedfilemanager.save()
        
        self.close(True)
    
    def cancel(self):
        """Cancel setup"""
        self.close(False)