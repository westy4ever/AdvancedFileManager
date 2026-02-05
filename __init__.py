# -*- coding: utf-8 -*-
"""
Advanced File Manager Plugin for Enigma2
Compatible with OpenATV Python 3.13.11
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "GPL-2.0+"

from Plugins.Plugin import PluginDescriptor

def Plugins(**kwargs):
    from .plugin import Plugins
    return Plugins(**kwargs)