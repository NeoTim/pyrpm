#!/usr/bin/python
#
# Get header information from an RPM file

import sys

sys.path[0:0] = ['.', '..']
import pyrpm


def main():
    if len(sys.argv) == 1:
        sys.stderr.write("Usage: %s <RPM file>\n" % sys.argv[0])
        sys.exit(0)
    f = sys.argv[1]

    pyrpm.rpmconfig.nofileconflicts = 1
    pyrpm.rpmconfig.checkinstalled = 0

    # pyrpm.rpmconfig.debug = verbose
    # pyrpm.rpmconfig.warning = verbose
    # pyrpm.rpmconfig.verbose = verbose

    r = pyrpm.RpmPackage(pyrpm.rpmconfig, "%s" % (f), verify=None,
                         hdronly=None, db=None)

    r.read(tags=pyrpm.rpmconfig.resolvertags)
    for k in r:
        if k in pyrpm.rpmconfig.resolvertags:
            print("%s: %s" % (k, r[k]))

if __name__ == "__main__":
    main()
