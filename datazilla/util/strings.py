#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####


def indent(value):
    return "\t"+"\n\t".join(value.rstrip().splitlines())


def outdent(value):
    num=100
    lines=value.splitlines()
    for l in lines:
        trim=len(l.lstrip())
        if trim>0: num=min(num, len(l)-len(l.lstrip()))
    return "\n".join([l[num:] for l in lines])




