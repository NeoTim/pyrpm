#
# Copyright (C) 2005,2006 Red Hat, Inc.
# Author: Thomas Woerner <twoerner@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import os.path
from installer import keyboard_models
from functions import create_file
import hwdata

def x_config(ks, buildroot, installation):
    # default: VGA graphics card, Generic extended super VGA monitor
    card = "Unknown video card"
    driver = "vga"
    videoram = 0
    monitor = "Unknown monitor"
    hsync = "31.5 - 37.9"
    vsync = "50 - 61"
    dmps = 0
    resolution = "800x600"
    depth = 8
    user_hsync = user_vsync = None
    options = [ ]

    # keyboard
    (kbd_layout, kbd_model, kbd_variant, kbd_options) = \
                 keyboard_models[ks["keyboard"]]

    _card = None
    _driver = None
    _options = [ ]
    if ks["xconfig"].has_key("card"):
        if os.path.exists(buildroot+'/usr/share/hwdata/Cards'):
            try:
                cards = hwdata.Cards(buildroot+'/usr/share/hwdata/Cards')
            except:
                print "Failed to load '/usr/share/hwdata/Cards'."
            else:
                dict = cards.get(ks["xconfig"]["card"])
                if dict and dict.has_key("driver"):
                    _card = ks["xconfig"]["card"]
                    _driver = dict["driver"]
                    if dict.has_key("options"):
                        _options.extend(dict["options"])
                else:
                    print "ERROR: Card not found in hardware database."
        else:
            print "Unable to use card '%s'" % (ks["xconfig"]["card"]) + \
                  ", because there is no '/usr/share/hwdata/Cards'"
    if not _card and ks["xconfig"]["driver"]:
        if os.path.exists(buildroot+'/usr/share/hwdata/videodrivers'):
        # There is no usable name in the videodrivers file, so fake it
            _driver = ks["xconfig"]["driver"]
            _card = driver + ' (generic)'
        else:
            print "Unable to use driver '%s'" % ks["xconfig"]["driver"] + \
                  ", because there is no '/usr/share/hwdata/videodrivers'"

    if not _card or not _driver:
        print "Using default X driver configuration."
    else:
        card = _card
        driver = _driver
        options = _options
        if ks["xconfig"].has_key("videoram"):
            videoram = ks["xconfig"]["videoram"]

    _monitor = None
    _hsync = None
    _vsync = None
    _dpms = 0
    if ks["xconfig"].has_key("monitor"):
        if os.path.exists(buildroot+'/usr/share/hwdata/Cards'):
            try:
                monitors = hwdata.Monitors(buildroot)
            except:
                print "ERROR: Failed to load monitor database."
            else:
                dict = monitors.get(ks["xconfig"]["monitor"])
                if dict:
                    _monitor = ks["xconfig"]["monitor"]
                    _hsync = dict["hsync"]
                    _vsync = dict["vsync"]
                    _dpms = dict["dpms"]
                else:
                    print "ERROR: Monitor not found in hardware database."

    if not _monitor or not _hsync or not _vsync:
        print "Using default monitor X configuration."
    else:
        monitor = _monitor
        hsync = _hsync
        vsync = _vsync
        dpms = _dpms
        if ks["xconfig"].has_key("hsync"): # overwrite with user supplied value
            hsync = ks["xconfig"]["hsync"]
        if ks["xconfig"].has_key("vsync"):
            vsync = ks["xconfig"]["vsync"] # overwrite with user supplied value
        if ks["xconfig"].has_key("resolution"):
            resolution = ks["xconfig"]["resolution"]
        if ks["xconfig"].has_key("depth"):
            depth = ks["xconfig"]["depth"]

    if (installation.release == "RHEL" and installation.version < 4) or \
           (installation.release == "FC" and installation.version < 3.9):
        conf = "/etc/X11/XF86Config"
    else:
        conf = "/etc/X11/xorg.conf"

    _kbdvariant = _kbdoptions = ""
    if kbd_variant and len(kbd_variant) > 0:
        _kbdvariant = '        Option       "XkbVariant" "%s"\n' % kbd_variant
    if kbd_options and len(kbd_options) > 0:
        _kbdoptions = '        Option       "XkbOptions" "%s"\n' % kbd_options

    if (installation.release == "RHEL" and installation.version < 4) or \
           (installation.release == "FC" and installation.version < 2.9):
        mousedev = "/dev/mouse"
    else:
        mousedev = "/dev/input/mice"

    _hsync = _vsync = _dmps = ""
    if hsync:
        _hsync = '        HorizSync    %s\n' % hsync
    if vsync:
        _vsync = '        VertRefresh  %s\n' % vsync
    if dpms:
        _dpms = '        Option       "dpms"\n'

    _videoram = ""
    if videoram:
        _videoram = '        VideoRam     %s\n' % videoram
    _options = ""
    if len(options) > 0:
        for option in options:
            _options += '        %s\n' % option

    content = [ 'Section "ServerLayout"\n',
                '        Identifier   "Default Layout"\n',
                '        Screen       0 "Screen0" 0 0\n',
                '        InputDevice  "Mouse0" "CorePointer"\n',
                '        InputDevice  "Keyboard0" "CoreKeyboard"\n',
                'EndSection\n\n',
                'Section "Files"\n',
                '        FontPath     "unix/:7100"\n',
                'EndSection\n\n',
                'Section "Module"\n',
                '        Load         "dbe"\n',
                '        Load         "extmod"\n',
                '        Load         "fbdevhw"\n',
                '        Load         "record"\n',
                '        Load         "freetype"\n',
                '        Load         "type1"\n',
                '        Load         "glx"\n',
                '        Load         "dri"\n',
                'EndSection\n\n',
                'Section "InputDevice"\n',
                '        Identifier   "Keyboard0"\n',
                '        Driver       "kbd"\n',
                '        Option       "XkbModel" "%s"\n' % kbd_model,
                '        Option       "XkbLayout" "%s"\n' % kbd_layout,
                _kbdvariant,
                _kbdoptions,
                'EndSection\n\n',
                'Section "InputDevice"\n',
                '        Identifier   "Mouse0"\n',
                '        Driver       "mouse"\n',
                '        Option       "Protocol" "IMPS/2"\n',
                '        Option       "Device" "%s"\n' % mousedev,
                '        Option       "ZAxisMapping" "4 5"\n',
                '        Option       "Emulate3Buttons" "no"\n',
                'EndSection\n\n',
                'Section "Monitor"\n',
                '        Identifier   "Monitor0"\n',
                '        VendorName   "Monitor Vendor"\n',
                '        ModelName    "%s"\n' % monitor,
                _hsync,
                _vsync,
                _dpms,
                'EndSection\n\n',
                'Section "Device"\n',
                '        Identifier   "Videocard0"\n',
                '        VendorName   "Videocard vendor"\n',
                '        BoardName    "%s"\n' % card,
                '        Driver       "%s"\n' % driver,
                _videoram,
                _options,
                'EndSection\n\n',
                'Section "Screen"\n',
                '        Identifier   "Screen0"\n',
                '        Device       "Videocard0"\n',
                '        Monitor      "Monitor0"\n',
                '        DefaultDepth %s\n' % depth,
                '        SubSection "Display"\n',
                '                Viewport 0 0\n',
                '                Depth    %s\n' % depth,
                '                Modes    "%s"\n' % resolution,
                '        EndSubSection\n',
                'EndSection\n\n' ]
    if (installation.release == "RHEL" and installation.version < 4) or \
           (installation.release == "FC" and installation.version < 2.9):
        content.extend( ['Section "DRI"\n',
                         '        Group        0\n',
                         '        Mode         0666\n',
                         'EndSection\n' ] )
    create_file(buildroot, conf, content)
