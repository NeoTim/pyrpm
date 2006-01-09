#
# Copyright (C) 2004, 2005 Red Hat, Inc.
# Author: Phil Knirsch, Thomas Woerner, Florian La Roche, Karel Zak
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


import libxml2
import functions


class RpmCompsXML:
    def __init__(self, config, source):
        """Initialize the parser.

        source is an URL to comps.xml."""

        self.config = config
        self.source = source
        self.grouphash = {}             # group id => { key => value }
        self.grouphierarchyhash = {}    # FIXME: write-only

    def __str__(self):
        return str(self.grouphash)

    def read(self):
        """Open and parse the comps file.

        Return 1 on success, 0 on failure."""

        filename = functions.cacheLocal(functions._uriToFilename(self.source), "", 1)
        if filename is None:
            return 0
        try:
            doc = libxml2.parseFile (filename)
            root = doc.getRootElement()
        except libxml2.libxmlError:
            return 0
        return self.__parseNode(root.children)

    def getPackageNames(self, group):
        """Return a list of mandatory an default packages from group and its
        dependencies and the dependencies of the packages.

        The list may contain a single package name more than once.  Only the
        first-level package dependencies are returned, not their transitive
        closure."""

        ret = self.__getPackageNames(group, ("mandatory", "default"))
        ret2 = []
        for val in ret:
            ret2.append(val[0])
            ret2.extend(val[1])
        return ret2

    def getOptionalPackageNames(self, group):
        """Return a sorted list of (package name, [package requirement]) of
        optional packagres from group and its dependencies."""

        return self.__getPackageNames(group, ["optional"])

    def getDefaultPackageNames(self, group):
        """Return a sorted list of (package name, [package requirement]) of
        default packagres from group and its dependencies."""

        return self.__getPackageNames(group, ["default"])

    def getMandatoryPackageNames(self, group):
        """Return a sorted list of (package name, [package requirement]) of
        mandatory packagres from group and its dependencies."""

        return self.__getPackageNames(group, ["mandatory"])

    def __getPackageNames(self, group, typelist):
        """Return a sorted list of (package name, [package requirement]) of
        packages from group and its dependencies with selection type in
        typelist."""

        ret = []
        if not self.grouphash.has_key(group):
            return ret
        if self.grouphash[group].has_key("packagelist"):
            pkglist = self.grouphash[group]["packagelist"]
            for (pkgname, value) in pkglist.iteritems():
                if value[0] in typelist:
                    ret.append((pkgname, value[1]))
        if self.grouphash[group].has_key("grouplist"):
            grplist = self.grouphash[group]["grouplist"]
            # FIXME: Stack overflow with loops in group requirements
            for grpname in grplist["groupreqs"]:
                ret.extend(self.__getPackageNames(grpname, typelist))
            for grpname in grplist["metapkgs"]:
                ret.extend(self.__getPackageNames(grpname, typelist))
        # Sort and duplicate removal
        ret.sort()
        for i in xrange(len(ret)-2, -1, -1):
            if ret[i+1] == ret[i]:
                ret.pop(i+1)
        return ret

    def __parseNode(self, node):
        """Parse libxml2.xmlNode node and its siblings under the root
        element.

        Return 1 on success, 0 on failure.  Handle <group>, <grouphierarchy>,
        warn about other tags."""

        while node != None:
            if node.type != "element":
                node = node.next
                continue
            if node.name == "group" or node.name == "category":
                self.__parseGroup(node.children)
            elif node.name == "grouphierarchy":
                ret = self.__parseGroupHierarchy(node.children)
                if not ret:
                    return 0
            else:
                self.config.printWarning(1, "Unknown entry in comps.xml: %s" % node.name)
                return 0
            node = node.next
        return 1

    def __parseGroup(self, node):
        """Parse libxml2.xmlNode node and its siblings under <group>."""

        group = {}
        while node != None:
            if node.type != "element":
                node = node.next
                continue
            if  node.name == "name":
                lang = node.prop("lang")
                if lang:
                    group["name:"+lang] = node.content
                else:
                    group["name"] = node.content
            elif node.name == "id":
                group["id"] = node.content
            elif node.name == "description":
                lang = node.prop("lang")
                if lang:
                    group["description:"+lang] = node.content
                else:
                    group["description"] = node.content
            elif node.name == "default":
                group["default"] = functions.parseBoolean(node.content)
            elif node.name == "langonly":
                group["langonly"] = node.content
            elif node.name == "packagelist":
                group["packagelist"] = self.__parsePackageList(node.children)
            elif node.name == "grouplist":
                group["grouplist"] = self.__parseGroupList(node.children)
            node = node.next
        self.grouphash[group["id"]] = group

    def __parsePackageList(self, node):
        """Parse libxml2.xmlNode node and its siblings under <packagelist>.

        Return { package => (selection, [requirement]) }."""

        plist = {}
        while node != None:
            if node.type != "element":
                node = node.next
                continue
            if node.name == "packagereq":
                ptype = node.prop("type")
                if ptype == None:
                    ptype = "default"
                requires = node.prop("requires")
                if requires != None:
                    requires = requires.split()
                else:
                    requires = []
                plist[node.content] = (ptype, requires)
            node = node.next
        return plist

    def __parseGroupList(self, node):
        """Parse libxml2.xmlNode node and its siblings under <grouplist>.

        Return { "groupgreqs" => [requirement],
        "metapkgs" => { requirement => requirement type } }."""

        glist = {}
        glist["groupreqs"] = []
        glist["metapkgs"] = {}
        while node != None:
            if node.type != "element":
                node = node.next
                continue
            if   node.name == "groupreq" or node.name == "groupid":
                glist["groupreqs"].append(node.content)
            elif node.name == "metapkg":
                gtype = node.prop("type")
                if gtype == None:
                    gtype = "default"
                glist["metapkgs"][node.content] = gtype
            node = node.next
        return glist

    def __parseGroupHierarchy(self, node):
        """"Parse" libxml2.xmlNode node and its siblings under
        <grouphierarchy>.

        Return 1."""

        # We don't need grouphierarchies, so don't parse them ;)
        return 1

# vim:ts=4:sw=4:showmatch:expandtab