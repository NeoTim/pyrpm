#!python
# -*- python -*-
# -*- coding: utf-8 -*-
## Copyright (C) 2005 Red Hat, Inc.
## Copyright (C) 2005 Harald Hoyer <harald@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


"""Parser for RPM Specfiles.
"""

import sys
import string

class RpmSpecFile:
    """Class for parsing an rpm specfile
    """
    sections = [ "description",
                 "package",
                 "prep",
                 "build",
                 "install",
                 "clean",
                 "files",
                 "changelog" ]


    def __init__(self, filename = None, lines = None, packagename = None):
        """filename: filename of the specfile
        lines: array of specfile lines
        packagename: if no lines or filename is specified,
                     use this for later initialization
        """
        self.Name = "head"

        if filename:
            self.readFile(filename)
        elif lines:
            self.lines = lines
        elif packagename:
            self.Name = packagename
        else:
            # should raise an exception here??
            return
        
        self.parse()

    def readFile(self, filename):
        """Initialize with filename
        """
        fd = open(filename)
        self.lines = fd.read().splitlines()
        fd.close()
        
    def parse(self):
        """Parse the specfile lines
        """
        section = "package"
        package = "head"
        # search for the package name
        for line in self.lines:
            if line[:5] == "Name:":
                toks = line.split()
                if len(toks) == 2:
                    self.Name = toks[1]
                break

        if self.Name:
            package = self.Name

        self.section = dict()
        self.section[section] = dict()
        self.section[section][package] = list()


        # Now split into sections
        for line in self.lines:
            if line[:1] == "%":                            
                tokens = line[1:].split()
                if tokens[0] in RpmSpecFile.sections:
                    if len(tokens) == 3 and tokens[1] == "-n":
                        section = tokens[0]
                        package = tokens[2]                    
                    else:
                        section = tokens[0]
                        package = self.Name

                    if not self.section.has_key(section):
                        self.section[section] = dict()
                    if not self.section[section].has_key(package):
                        self.section[section][package] = list()
                    continue

            if package:
                self.section[section][package].append(line)
            else:
                self.section[section].append(line)

    def getName(self):
        """returns the package name
        """
        return self.Name

    def getSections(self):
        """returns all section names, which are known and in the specfile
        """
        return self.section.keys()

    def getPackages(self):
        """returns a list of package names
        """
        if self.section.has_key("description"):
            return self.section["description"].keys()
        else:
            return [self.Name]
        

    def getSection(self, section, package = None):
        """Returns the section from package
        If package is not specified, the section from all packages will be
        returned, each prefixed with the package name.
        If the section is only specified for the main package, no package
        prefix will be used.
        """
        if package == None:
            if self.section.has_key(section):
                if len(self.section[section].keys()) == 1 and \
                   self.section[section].keys()[0] == self.Name:
                    return string.join(self.section[section][self.Name],
                                       '\n') + "\n"

                else:
                    s = ""
                    for (name, section) in self.section[section].items():
                        s += name + ": " + \
                             string.join(section,
                                         '\n' + name + ": ") + "\n"
                    return s

        else:
            if self.section.has_key(section) and \
                   self.section[section].has_key(package):
                return string.join(self.section[section][package],
                                   '\n') + "\n"            
        return ""

__author__ = "Harald Hoyer <harald@redhat.com>"
