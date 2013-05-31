#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####


#DUE TO MY POOR MEMORY, THIS IS A LIST OF ALL CONVERSION ROUTINES
import json

class CNV:

    @staticmethod
    def object2JSON(obj):
        return json.dumps(obj)

    @staticmethod
    def JSON2object(json):
        return json.loads(json)