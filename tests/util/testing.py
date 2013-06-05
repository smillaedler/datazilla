#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####

import os
from datazilla.util.cnv import CNV


with open(os.environ.get("SETTINGS_FILE", "")) as f:
    settings=CNV.JSON2object(f.read())