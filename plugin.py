# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
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
config.plugins.advancedfilemanager.enable_network = ConfigYesNo(default=False)
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
    """Load custom hotkey mappings"""
    hotkey_file = resolveFilename(SCOPE_PLUGINS, "Extensions/AdvancedFileManager/default_hotkeys.json")
    try:
        if os.path.exists(hotkey_file):
            with open(hotkey_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading hotkeys: {e}")
    
    # Default hotkeys
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

def check_dependencies():
    """Check for optional dependencies and warn user"""
    missing = []
    warnings = []
    
    # Check for PIL/Pillow (image viewer)
    try:
        import PIL
    except ImportError:
        missing.append("python3-pillow (Image viewer will not work)")
    
    # Check for paramiko (SFTP)
    try:
        import paramiko
    except ImportError:
        warnings.append("python3-paramiko (SFTP support disabled)")
    
    # Check for mutagen (audio metadata)
    try:
        import mutagen
    except ImportError:
        warnings.append("python3-mutagen (Audio metadata disabled)")
    
    # Check for requests (WebDAV)
    try:
        import requests
    except ImportError:
        warnings.append("python3-requests (WebDAV support disabled)")
    
    return missing, warnings

def show_dependency_warning(session):
    """Show warning about missing dependencies"""
    missing, warnings = check_dependencies()
    
    if missing:
        msg = "Required dependencies missing:\n\n" + "\n".join(missing)
        msg += "\n\nInstall with: opkg install <package-name>"
        session.open(MessageBox, msg, MessageBox.TYPE_WARNING, timeout=10)
    elif warnings:
        msg = "Optional dependencies missing:\n\n" + "\n".join(warnings)
        msg += "\n\nSome features will be disabled."
        session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=5)

def main(session, **kwargs):
    """Main entry point"""
    try:
        # Check dependencies
        show_dependency_warning(session)
        
        # Import and open file manager
        from .ui.filemanager import AdvancedFileManager
        session.open(AdvancedFileManager)
    except ImportError as e:
        session.open(
            MessageBox,
            f"Failed to load Advanced File Manager:\n{e}\n\nPlease check installation.",
            MessageBox.TYPE_ERROR
        )
    except Exception as e:
        session.open(
            MessageBox,
            f"Error starting Advanced File Manager:\n{e}",
            MessageBox.TYPE_ERROR
        )

def setup(session, **kwargs):
    """Setup wizard entry point"""
    try:
        from .ui.setup_wizard import SetupWizard
        session.open(SetupWizard)
    except ImportError as e:
        session.open(
            MessageBox,
            f"Failed to load setup wizard:\n{e}",
            MessageBox.TYPE_ERROR
        )
    except Exception as e:
        session.open(
            MessageBox,
            f"Error starting setup wizard:\n{e}",
            MessageBox.TYPE_ERROR
        )

def Plugins(**kwargs):
    """Plugin descriptor"""
    descriptors = [
        PluginDescriptor(
            name="Advanced File Manager",
            description="Feature-rich file manager with network and media support",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        ),
        PluginDescriptor(
            name="Advanced File Manager",
            description="Advanced File Manager",
            where=PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc=main
        ),
    ]
    
    # Only add setup to plugin menu if user wants it
    descriptors.append(
        PluginDescriptor(
            name="Advanced File Manager Setup",
            description="Configure file manager settings",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=setup
        )
    )
    
    return descriptors