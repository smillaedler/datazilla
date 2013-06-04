#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####


#DUE TO MY POOR MEMORY, THIS IS A LIST OF ALL CONVERSION ROUTINES
import json
import time
import datetime
from datazilla.util.map import Map

class CNV:

    @staticmethod
    def object2JSON(obj):
        return json.dumps(obj)

    @staticmethod
    def JSON2object(json_string):
        return Map(**json.loads(json_string))



    @classmethod
    def datetime2unix(cls, d):
        return time.mktime(d.timetuple())

    @classmethod
    def unix2datetime(cls, u):
        return datetime.datetime.fromtimestamp(u)