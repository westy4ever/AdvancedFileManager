# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, ConfigSelection, ConfigInteger
from Components.Sources.StaticText import StaticText
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import os
import json

# Plugin configuration
config.plugins.advancedfilemanager = ConfigSubsection()

# General settings
config.plugins.advancedfilemanager.lastpath = ConfigText(default="/media")
config.plugins.advancedfilemanager.showhidden = ConfigYesNo(default=False)
config.plugins.advancedfilemanager.use_trash = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.trash_path = ConfigText(default="/media/.trash")
config.plugins.advancedfilemanager.confirm_delete = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.confirm_overwrite = ConfigYesNo(default=True)

# View settings
config.plugins.advancedfilemanager.default_view = ConfigSelection(default="dual", choices=[("dual", "Dual Pane"), ("single", "Single Pane")])
config.plugins.advancedfilemanager.show_extensions = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.dirs_first = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.sort_column = ConfigSelection(default="name", choices=[("name", "Name"), ("size", "Size"), ("date", "Date")])

# Network settings
config.plugins.advancedfilemanager.enable_network = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.ftp_timeout = ConfigInteger(default=30, limits=(5, 300))
config.plugins.advancedfilemanager.sftp_timeout = ConfigInteger(default=30, limits=(5, 300))

# Media settings
config.plugins.advancedfilemanager.enable_media = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.autoplay_next = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.auto_load_subtitles = ConfigYesNo(default=True)

# Cache settings
config.plugins.advancedfilemanager.enable_cache = ConfigYesNo(default=True)
config.plugins.advancedfilemanager.cache_expire = ConfigInteger(default=5, limits=(1, 60))

# Logging
config.plugins.advancedfilemanager.log_level = ConfigSelection(default="INFO", choices=[("DEBUG", "Debug"), ("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error")])
config.plugins.advancedfilemanager.log_to_file = ConfigYesNo(default=True)

# Load hotkeys configuration
def load_hotkeys():
    hotkey_file = resolveFilename(SCOPE_PLUGINS, "Extensions/AdvancedFileManager/default_hotkeys.json")
    try:
        with open(hotkey_file, 'r') as f:
            return json.load(f)
    except:
        return {
            "subtitle_download": ["KEY_SUBTITLE", "KEY_TEXT"],
            "subtitle_delay_plus": ["KEY_CHANNELUP"],
            "subtitle_delay_minus": ["KEY_CHANNELDOWN"],
            "toggle_subtitles": ["KEY_HELP"],
            "subtitle_sync_reset": ["KEY_0"],
            "context_menu": ["KEY_MENU"],
            "file_info": ["KEY_INFO"],
            "show_playlist": ["KEY_P"],
            "next_file": ["KEY_UP"],
            "prev_file": ["KEY_DOWN"],
            "delete_file": ["KEY_RED"],
            "toggle_osd": ["KEY_OK"]
        }

HOTKEYS = load_hotkeys()

def main(session, **kwargs):
    from .ui.filemanager import AdvancedFileManager
    session.open(AdvancedFileManager)

def setup(session, **kwargs):
    from .ui.setup_wizard import SetupWizard
    session.open(SetupWizard)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Advanced File Manager",
            description="Feature-rich file manager with network and media support",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        ),
        PluginDescriptor(
            name="Advanced File Manager",
            where=PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc=main
        ),
        PluginDescriptor(
            name="Advanced File Manager Setup",
            description="Configure file manager settings",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=setup
        )
    ]