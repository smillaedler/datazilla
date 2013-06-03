#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####


#DUE TO MY POOR MEMORY, THIS IS A LIST OF ALL CONVERSION ROUTINES
import json
from datazilla.util.debug import D
from datazilla.util.strings import between

class CNV:

    @staticmethod
    def object2JSON(obj):
        return json.dumps(obj)

    @staticmethod
    def JSON2object(json_string):
        try:
            return json.loads(json_string)
        except Exception, e:
            #Invalid control character at: line 1 column 11373 (char 11372)
            #Expecting , delimiter: line 1 column 12261 (char 12260)
            line=0
            col=0
            sendDetails=False
            try: #TRY TO PULL LINE AND COLUMN FOR BETTER ERROR
                line = int(between(e.message, "line", "column").strip())
                col = int(between(e.message, "column", "(").strip())
                sendDetails=True
            except Exception, f:
                pass

            if sendDetails: D.error("Can not parse json near ..."+json_string.split("\n")[line-1][max(0, col-20):col+20], e)
            D.error("Can not parse json!", e)

