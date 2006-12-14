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

from pyrpm.logger import log
from pyrpm.config import rpmconfig
from pyrpm.cache import NetworkCache
from pyrpm.functions import stringCompare, normalizeList
from pyrpm.database import getRepoDB
from pyrpm.yum import YumConf
from devices import *
from functions import *
from pyrpm import database
from disk import *

################################### classes ###################################

class Source:
    def __init__(self):
        self.repos = { }
        self.base_repo_names = [ ]
        self.mounts = { }

    def load(self, ks, dir, no_discinfo=0):
        self.dir = dir
        self.exclude = None

        # mount source to dir
        if ks.has_key("cdrom"):
            self.url = mount_cdrom(dir)
            if ks["cdrom"].has_key("exclude"):
                self.exclude = ks["cdrom"]["exclude"]
        elif ks.has_key("nfs"):
            self.url = mount_nfs("nfs://%s:%s" % \
                                 (ks["nfs"]["server"], ks["nfs"]["dir"]), dir)
            if ks["nfs"].has_key("exclude"):
                self.exclude = ks["nfs"]["exclude"]
        else:
            self.url = ks["url"]["url"]
            if ks["url"].has_key("exclude"):
                self.exclude = ks["url"]["exclude"]

        # create network cache
        self.cache = NetworkCache([ self.url ], cachedir=rpmconfig.cachedir)

        # check source
        if not self.cache.cache("."):
            log.errorLn("Failed to access '%s'.", self.url)
            return 0

        # get source version, release and architecture
        if no_discinfo:
            # get source information via release package
            ri = release_info(source)
            if not ri:
                log.errorLn("Getting release info for '%s' failed.", url)
                return 0
            else:
                (self.name, self.version, self.arch) = ri
        else:
            # get source information via .discinfo file
            if not self.cache.cache(".discinfo"):
                log.errorLn("No .discinfo for '%s'", self.url)
                return 0
            di = get_discinfo(self.cache.cache(".discinfo"))
            if not di:
                log.errorLn("Getting .discinfo for '%s' failed.", url)
                return 0
            (self.name, self.version, self.arch) = di

        if self.name.startswith("Red Hat Enterprise Linux"):
            self.variant = self.name[24:].strip()
            self.id = "RHEL"
            self.prefix = "RedHat"
        elif self.name.startswith("Fedora"):
            self.variant = ""
            self.id = "FC"
            self.prefix = "Fedora"
        else:
            log.errorLn("Unknown source release '%s'.", self.release)
            return 0

        self.release = "%s-%s" % (self.id, self.version)        

        log.info1Ln("Installation source: %s %s [%s]", self.name, self.version,
                    self.arch)

        # load repos
        repos = [ ]
        if self.isRHEL() and self.cmpVersion("4.9") >= 0:
            # RHEL-5

            key = None
            skip = False
            if ks.has_key("key"):
                key = ks["key"].keys()[0]
                if ks["key"][key].has_key("skip"):
                    skip = True

            if self.variant == "Server":
                repos.append("Server")
                if key and not skip:
                    if key.find("C") >= 0:
                        repos.append("Cluster")
                    if key.find("S") >= 0:
                        repos.append("ClusterStorage")
            elif self.variant == "Client":
                repos.append("Client")
                if key and not skip:
                    if key.find("W") >= 0:
                        repos.append("Workstation")

            if self.arch in [ "i386", "x86_64", "ia64" ]:
                if key and not skip:
                    if key.find("V") >= 0:
                        repos.append("VT")

            for repo in repos:
                repo_name = "%s-%s" % (self.release, repo)
                if repo in self.repos:
                    log.errorLn("Repository '%s' already defined.", repo_name)
                    return 0

                log.info1Ln("Loading repo '%s'", repo_name)

                # create yumconf
                yumconf = YumConf(self.version, self.arch, self.arch)
                yumconf.vars[repo_name] = { }
                if self.exclude:
                    yumconf.vars[repo_name]["exclude"] = " ".join(self.exclude)
                _repo = getRepoDB(rpmconfig, [ "%s/%s" % (self.url, repo) ],
                                  yumconf=yumconf, reponame=repo_name)
                if not _repo.read():
                    log.errorLn("Could not load repository '%s'.", repo_name)
                    return 0
                self.repos[repo_name] = _repo
        else:
            # RHEL <= 4
            # FC
            yumconf = YumConf(self.version, self.arch, self.arch)
            repo = self.release
            yumconf.vars[repo] = { }
            if self.exclude:
                yumconf.vars[repo]["exclude"] = self.exclude
            _repo = getRepoDB(rpmconfig, [ self.url ], yumconf=yumconf,
                              reponame=repo)
            if not _repo.read():
                log.errorLn("Could not load repository '%s'.", repo)
                return 0
            if not _repo.comps: # every source repo has to have a comps
                log.errorLn("Missing comps file for '%s'.", repo)
                return 0
            self.repos[repo] = _repo

        self.base_repo_names = self.repos.keys()

        if not ks.has_key("repo"):
            return 1
            
        for repo in ks["repo"]:
            if repo in self.repos:
                log.errorLn("Repository '%s' already defined.", repo)
                return 0

            log.info1Ln("Loading extra repo '%s'", repo)

            url = ks["repo"][repo]["baseurl"]

            yumconf = YumConf(self.version, self.arch, self.arch)
            yumconf.vars[repo] = { }

            if ks["repo"][repo].has_key("mirrorlist"):
                yumconf.vars[repo]["mirrorlist"] = \
                                                 ks["repo"][repo]["mirrorlist"]
            if ks["repo"][repo].has_key("exclude"):
                yumconf.vars[repo]["exclude"] = ks["repo"][repo]["exclude"]

            if url[:6] == "nfs://":
                d = "%s/%s" % (dir, repo)
                create_dir("", d)
                url = mount_nfs(url, d)

            _repo = getRepoDB(rpmconfig, [ url ], yumconf=yumconf,
                              reponame=repo)
            if not _repo.read():
                log.errorLn("Could not load repository '%s'.", repo)
                return 0
            self.repos[repo] = _repo

        return 1

    def getStage2(self):
        if self.isRHEL() and self.cmpVersion("4.9") >= 0:
            return self.cache.cache("images/stage2.img")
        else:
            if self.cmpVersion("6") < 0:
                return self.cache.cache("%s/base/stage2.img" % self.prefix)
            else:
                return self.cache.cache("images/stage2.img")

    def getPackages(self, ks, languages, no_default_groups, all_comps,
                    has_raid, fstypes):
        if not ks.has_key("packages"):
            return [ ]

        groups = [ ]
        pkgs = [ ]
        everything = False
        if ks["packages"].has_key("groups") and \
               len(ks["packages"]["groups"]) > 0:
            groups = ks["packages"]["groups"]

        # add default group "base" and "core if it is not in groups and
        # no_default_groups is not set
        if not (ks.has_key("packages") and \
                ks["packages"].has_key("nobase")) or \
                not no_default_groups:
            if not "base" in groups:
                groups.append("base")
            if not "core" in groups:
                groups.append("core")

        if all_comps:
            repos = self.repos.keys()
        else:
            repos = self.base_repo_names

        if "everything" in groups:
            for repo in repos:
                for group in self.repos[repo].comps.getGroups():
                    if not _group in groups:
                        groups.append(_group)
            groups.remove("everything")
            everything = 1

        # add default desktop
        if ks.has_key("xconfig"):
            if ks["xconfig"].has_key("startxonboot"):
                if not "base-x" in groups:
                    log.info1Ln("Adding group 'base-x'.")
                    groups.append("base-x")
                desktop = "GNOME"
                if ks["xconfig"].has_key("defaultdesktop"):
                    desktop = ks["xconfig"]["defaultdesktop"]
                desktop = "%s-desktop" % desktop.lower()
                if not desktop in groups:
                    log.info1Ln("Adding group '%s'.", desktop)
                    groups.append(desktop)

        normalizeList(groups)

        # test if groups are available
        repo_groups = { }
        for group in groups:
            found = False
            for repo in repos:
                if not self.repos[repo].comps:
                    continue
                _group = self.repos[repo].comps.getGroup(group)
                if not _group:
                    continue
                found = True
                if not _group in repo_groups.keys() or \
                       not repo in repo_groups[_group]:
                    repo_groups.setdefault(_group, [ ]).append(repo)
            if not found:
                log.warningLn("Group '%s' does not exist.", group)
        del groups

        # add packages for groups
        for group in repo_groups:
            for repo in repo_groups[group]:
                comps = self.repos[repo].comps
                pkgs.extend(comps.getPackageNames(group))
                if everything:
                    # add all packages in this group
                    pkgs.extend(comps.getConditionalPackageNames(group))
        del repo_groups

        # add packages
        if ks["packages"].has_key("add"):
            for pkg in ks["packages"]["add"]:
                found = False
                exclude = [ ]
                for repo in self.repos.keys():
                    if self.repos[repo].hasName(pkg):
                        if pkg in self.repos[repo].excludes:
                            log.info2Ln("Excluding '%s' for repo '%s'", pkg,
                                        repo)
                            continue
                        # silently add package
                        if not pkg in pkgs:
                            pkgs.append(pkg)
                        found = True
                        break
                if not found:
                    log.warningLn("Package '%s' is not available.", pkg)
        # remove packages
        if ks["packages"].has_key("drop"):
            for pkg in ks["packages"]["drop"]:
                if pkg in pkgs:
                    log.info1Ln("Removing package '%s'.", pkg)
                    pkgs.remove(pkg)

        # add xorg driver package for past FC-5, RHEL-4
        if ks.has_key("xconfig"):
            if (self.isRHEL() and self.cmpVersion("4.9") > 0) or \
                   (self.isFedora() and self.cmpVersion("4") > 0):
                if ks["xconfig"].has_key("driver"):
                    self._addPkg("xorg-x11-drv-%s" % ks["xconfig"]["driver"],
                                 pkgs)
                else:
                    if not "xorg-x11-drivers" in pkgs:
                        self._addPkg("xorg-x11-drivers", pkgs)

        # add packages for needed filesystem types
        for fstype in fstypes:
            if fstype == "swap":
                continue
            self._addPkgByFilename("/sbin/mkfs.%s" % fstype, pkgs,
                                   "%s filesystem creation" % fstype)

        # add comps package
        if not "comps" in pkgs:
            pkgs.append("comps")

        # append mdadm
        if has_raid:
            self._addPkgByFilename("/sbin/mdadm", pkgs, "raid configuration")

        # append authconfig
        if ks.has_key("authconfig"):
            self._addPkgByFilename("/usr/sbin/authconfig", pkgs,
                                   "authentication configuration")

        # append iptables and config tool
        if ks.has_key("firewall") and \
               not ks["firewall"].has_key("disabled"):
            self._addPkg("iptables", pkgs)

        # no firewall config tool in RHEL-3
        if (self.isRHEL() and self.cmpVersion("4") >= 0) or \
               (self.isFedora() and self.cmpVersion("3") >= 0):
            self._addPkgByFilename("/usr/sbin/lokkit", pkgs,
                                   "firewall configuration")

        # append lokkit
        if ks.has_key("selinux") and \
               ((self.isRHEL() and self.cmpVersion("4") >= 0) or \
                (self.isFedora() and self.cmpVersion("3") >= 0)):
            self._addPkgByFilename("/usr/sbin/lokkit", pkgs,
                                   "selinux configuration")

        # append kernel
        if not "kernel" in pkgs and not "kernel-smp" in pkgs:
            self._addPkg("kernel", pkgs)

        # append kernel-devel for FC-6 and RHEL-5
        if "gcc" in pkgs and \
               ((self.isRHEL() and self.cmpVersion("4.9") >= 0) or \
                (self.isFedora() and self.cmpVersion("6") >= 0)):
            if "kernel" in pkgs:
                self._addPkg("kernel-devel", pkgs)
            elif "kernel-smp" in pkgs:
                self._addPkg("kernel-smp-devel", pkgs)

        # append firstboot
        if ks.has_key("firstboot") and \
               not ks["firstboot"].has_key("disabled"):
            self._addPkg("firstboot", pkgs)

        # append dhclient
        if ks.has_key("bootloader"):
            self._addPkg("grub", pkgs)

        # append grub
        if ks.has_key("network") and len(ks["network"]) > 0:
            for net in ks["network"]:
                if net["bootproto"] == "dhcp":
                    self._addPkg("dhclient", pkgs)

        # languages (pre FC-6 and pre RHEL-5)
        if len(languages) > 0:
            for repo in repos:
                _repo = self.repos[repo]
                if not _repo.comps:
                    continue
                for group in _repo.comps.grouphash.keys():
                    self._compsLangsupport(pkgs, _repo.comps, languages, group)

        return pkgs

    def _addPkg(self, name, pkgs, description=""):
        for repo in self.repos:
            if self.repos[repo].hasName(name):
                if name in self.repos[repo].excludes:
                    log.info2Ln("Excluding '%s' for repo '%s'", name, repo)
                    continue
                if not name in pkgs:
                    if description != "":
                        log.info1Ln("Adding package '%s' for %s.", name,
                                    description)
                    else:
                        log.info1Ln("Adding package '%s'.", name)
                    pkgs.append(name)
                return
        if description != "":
            raise ValueError, "Could not find package '%s'" % (name) + \
                  "needed for %s." % (description)
        else:
            raise ValueError, "Could not find package '%s'" % (name)

    def _addPkgByFilename(self, name, pkgs, description=""):
        for repo in self.repos:
            s = self.repos[repo].searchFilenames(name)
            if len(s) < 1:
                # import file list if not already imported and search again
                if not self.repos[repo]._matchesFile(name) and \
                       not self.repos[repo].isFilelistImported():
                    self.repos[repo].importFilelist()
                    s = self.repos[repo].searchFilenames(name)
                if len(s) < 1:
                    continue
            for pkg in s:
                if pkg["name"] in self.repos[repo].excludes:
                    log.info2Ln("Excluding '%s' for repo '%s'", pkg, repo)
                    continue
                if pkg["name"] in pkgs:
                    # package is already in list
                    return 
            pkg = s[0] # take first package, which provides ...
            if description != "":
                log.info1Ln("Adding package '%s' for %s.", pkg["name"],
                            description)
            else:
                log.info1Ln("Adding package '%s'.", pkg["name"])
            pkgs.append(pkg["name"])
            return

        if description != "":
            raise ValueError, "Could not find package providing '%s'" % \
                  (name) + "needed for %s." % (description)
        else:
            raise ValueError, "Could not find package providing '%s'" % (name)

    def _compsLangsupport(pkgs, comps, languages, group):
        if not comps.grouphash.has_key(group):
            return

        if not comps.grouphash[group].has_key("langonly") or \
               not comps.grouphash[group]["langonly"] in languages:
            return

        # add grouplist
        if comps.grouphash[group].has_key("grouplist"):
            for _group in comps.grouphash[group]["grouplist"]["groupreqs"]:
                self._compsLangsupport(pkgs, comps, languages, _group)
            for _group in comps.grouphash[group]["grouplist"]["metapkgs"]:
                self._compsLangsupport(pkgs, comps, languages, _group)

        for name in comps.getPackageNames(group):
            self._addPkg(name, pkgs, "langsupport")

        # old style conditional
        optional_list = comps.getOptionalPackageNames(group)
        for (name, requires) in optional_list:
            if name in pkgs:
                continue
            for req in requires:
                if req in pkgs:
                    log.info1Ln("Adding package '%s' for langsupport.", name)
                    pkgs.append(name)
                    break

        # new style conditional
        conditional_list = comps.getConditionalPackageNames(group)
        for (name, requires) in conditional_list:
            if name in pkgs:
                continue
            for req in requires:
                if req in pkgs:
                    log.info1Ln("Adding package '%s' for langsupport.", name)
                    pkgs.append(name)
                    break

    def getYumConf(self):
        ret = ""
        for repo in self.repos:
            ret += "[%s]\n" % repo
            ret += "name=%s\n" % repo
            _repo = self.repos[repo]
            baseurls = _repo.nc.baseurls[_repo.reponame]
            if len(baseurls) > 0:
                ret += "baseurl=%s\n" % " ".join(baseurls)
            if _repo.excludes:
                ret += "exclude=%s\n" % " ".join(_repo.excludes)
            if _repo.mirrorlist:
                ret += "mirrorlist=%s\n" % " ".join(_repo.mirrorlist)
            ret += "\n"
        return ret

    def close(self):
        for repo in self.repos:
            self.repos[repo].close()
        self.repos.clear()

    def cleanup(self):
        self.close()
        for mount in self.mounts:
            self.mounts[mount].umount()

    def isRHEL(self):
        return self.id == "RHEL"

    def isFedora(self):
        return self.id == "FC"

    def getName(self):
        return self.name

    def getVersion(self):
        return self.version

    def getArch(self):
        return self.arch

    def cmpVersion(self, other):
        return stringCompare(self.getVersion(), other)

    def getRelease(self):
        return self.release

    def get(self, filename):
        return self.cache.cache(filename)

# vim:ts=4:sw=4:showmatch:expandtab
