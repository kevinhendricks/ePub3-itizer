#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright (c) 2025 Doug Massay
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of
# conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list
# of conditions and the following disclaimer in the documentation and/or other materials
# provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
# SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import inspect


SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
e = os.environ.get('SIGIL_QT_RUNTIME_VERSION', '6.2.2')
SIGIL_QT_MAJOR_VERSION = tuple(map(int, (e.split("."))))[0]
DEBUG = 0

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401
from PySide6.QtCore import Qt

PLUGIN_QT_MAJOR_VERSION = tuple(map(int, (QtCore.qVersion().split("."))))[0]

# Function alias used to surround translatable strings
_t = QtCore.QCoreApplication.translate

if DEBUG:
    print('Sigil Qt: ', os.environ.get('SIGIL_QT_RUNTIME_VERSION'))
    print('Sigil Qt major version: ', SIGIL_QT_MAJOR_VERSION)


_plat = sys.platform.lower()
iswindows = 'win32' in _plat or 'win64' in _plat
ismacos = isosx = 'darwin' in _plat


''' Keep Windows from showing the Python icon on the taskbar '''
def ensure_windows_taskbar_icon():
    if not iswindows:
        return
    import ctypes
    myappid = 'mycompany.myproduct.subproduct.version'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


''' Find the location of Qt's base translations '''
def get_qt_translations_path(app_path):
    isBundled = False
    if iswindows or ismacos:
        isBundled = 'sigil' in sys.prefix.lower()
    if DEBUG:
        print('Python is Bundled: {}'.format(isBundled))
    if isBundled:
        if ismacos:
            return os.path.normpath(app_path + '/../translations')
        else:
            return os.path.join(app_path, 'translations')
    else:
        # This should work on Linux whether it's in an AppImage or not
        return QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)



''' Subclass of the QApplication object that includes a lot of
    Sigil specific routines that plugin devs won't have to worry
    about (unless they choose to, of course - hence the overrides)'''
class PluginApplication(QtWidgets.QApplication):
    def __init__(self, args, bk, app_icon=None, match_fonts=True,
                match_dark_palette=False, dont_use_native_menubars=False,
                load_qtbase_translations=True, load_qtplugin_translations=True,
                plugin_trans_folder=None):

        # Keep menubars in the application windows on all platforms
        if dont_use_native_menubars:
            self.setAttribute(Qt.AA_DontUseNativeMenuBar)

        self.bk = bk
        program_name = '{}'.format(bk._w.plugin_name)
        if plugin_trans_folder is None:
            plugin_trans_folder = os.path.join(self.bk._w.plugin_dir, self.bk._w.plugin_name, 'translations')

        # Initialize the QApplication to be used by the plugin
        args = [program_name] + args[1:]
        QtWidgets.QApplication.__init__(self, args)

        # set the app icon (used by all child windows)
        if app_icon is not None:
            self.setWindowIcon(QtGui.QIcon(app_icon))
            if iswindows:
                ensure_windows_taskbar_icon()

        # Match Sigil's dark palette if possible and/or wanted
        if match_dark_palette:
            self.match_sigil_darkmode()

        # Load Qt base dialog translations if available
        if load_qtbase_translations:
            self.load_base_qt_translations()
        # Load plugin dialog translations if available
        if load_qtplugin_translations:
            self.load_plugin_translations(plugin_trans_folder)

        # Match Sigil UI font if possible and/or wanted
        if match_fonts:
            self.match_sigil_font()
        

    def match_sigil_darkmode(self):
        if self.bk.colorMode() != "dark":
            return
        if DEBUG:
            print('Setting dark palette')

        p = QtGui.QPalette()
        sigil_colors = self.bk.color
        dark_color = QtGui.QColor(sigil_colors("Window"))
        disabled_color = QtGui.QColor(127, 127, 127)
        dark_link_color = QtGui.QColor(108, 180, 238)
        text_color = QtGui.QColor(sigil_colors("Text"))
        p.setColor(QtGui.QPalette.Window, dark_color)
        p.setColor(QtGui.QPalette.WindowText, text_color)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, disabled_color)
        p.setColor(QtGui.QPalette.Base, QtGui.QColor(sigil_colors("Base")))
        p.setColor(QtGui.QPalette.AlternateBase, dark_color)
        p.setColor(QtGui.QPalette.ToolTipBase, dark_color)
        p.setColor(QtGui.QPalette.ToolTipText, text_color)
        p.setColor(QtGui.QPalette.Text, text_color)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabled_color)
        p.setColor(QtGui.QPalette.Button, dark_color)
        p.setColor(QtGui.QPalette.ButtonText, text_color)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabled_color)
        p.setColor(QtGui.QPalette.BrightText, Qt.red)
        p.setColor(QtGui.QPalette.Link, dark_link_color)
        p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(sigil_colors("Highlight")))
        p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(sigil_colors("HighlightedText")))
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, disabled_color)

        self.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        self.setPalette(p)

    def _setup_ui_font_(self, font_lst):
        font = QtWidgets.QApplication.font()
        font.fromString(','.join(font_lst))

        if DEBUG:
            print('Font Weight: {}'.format(font.weight()))

        self.instance().setFont(font)
        if DEBUG:
            print(font.toString())

    def match_sigil_font(self):
        if DEBUG:
            print(self.bk._w.uifont)
        lst = self.bk._w.uifont.split(',')

        if not ismacos and not iswindows:
            # Qt 5.10.1 on Linux resets the global font on first event loop tick.
            # So workaround it by setting the font once again in a timer.
            try:
                QtCore.QTimer.singleShot(0, lambda : self._setup_ui_font_(lst))
            except Exception:
                pass

    # Install qtbase translator for standard dialogs and such.
    # Use the Sigil language setting unless manually overridden.
    def load_base_qt_translations(self):
        qt_translator = QtCore.QTranslator(self.instance())
        language_override = os.environ.get("SIGIL_PLUGIN_LANGUAGE_OVERRIDE")
        if language_override is not None:
            if DEBUG:
                print('Qt Base language override in effect')
            qmf = 'qtbase_{}'.format(language_override)
        else:
            qmf = 'qtbase_{}'.format(self.bk.sigil_ui_lang)
        # Get bundled or external translations directory
        qt_trans_dir = get_qt_translations_path(self.bk._w.appdir)
        if DEBUG:
            print('Qt translation dir: {}'.format(qt_trans_dir))
            print('Looking for {} in {}'.format(qmf, qt_trans_dir))
        qt_translator.load(qmf, qt_trans_dir)
        res = self.instance().installTranslator(qt_translator)
        if DEBUG:
            print('Qt Base Translator succesfully installed: {}'.format(res))

    # Install translator for the plugin's dialogs (if any).
    # Use the Sigil language setting unless manually overridden.
    def load_plugin_translations(self, trans_folder):
        plugin_translator = QtCore.QTranslator(self.instance())
        language_override = os.environ.get("SIGIL_PLUGIN_LANGUAGE_OVERRIDE")
        if language_override is not None:
            if DEBUG:
                print('Plugin language override in effect')
            qmf = '{}_{}'.format(self.bk._w.plugin_name.lower(), language_override)
        else:
            qmf = '{}_{}'.format(self.bk._w.plugin_name.lower(), self.bk.sigil_ui_lang)
        # Plugin *.qm files are looked for in the 'translations' folder at the root
        # of the plugin_dir by default. Override by setting an alternative location
        # with the plugin_trans_folder parameter of the Application class.
        if DEBUG:
            print('Looking for {} in {}'.format(qmf, trans_folder))
        plugin_translator.load(qmf, trans_folder)
        res = self.instance().installTranslator(plugin_translator)
        if DEBUG:
            print('Plugin Translator succesfully installed: {}'.format(res))
