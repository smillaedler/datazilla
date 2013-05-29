#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####



from datazilla.model.base import PerformanceTestModel
from datazilla.model.util.debug import D


## return a database connection
def getDatabaseConnection(project, schema):
    connection = PerformanceTestModel(project).sources[schema].dhub
    return Connection(connection)




class Connection():

    def __init__(self, db):
        self.db=db

    def begin(self):
        if self.cursor is not None:
            D.error("multiple begin not supported. yet")
        self.cursor=self.db.cursor()

    def close(self):
        self.cursor.close()
        self.cursor=None

    def commit(self):
        self.cursor.commit()

    def rollback(self):
        self.cursor.rollback()

    def query(self, **args):
        self.cursor.query(args)

    def execute(self, **args):
        self.cursor.execute(args)

        
    ## Insert dictionary of values into table
    def insert (self, tableName, dict):
        def quote(value):
            return "`"+value+"`"    #MY SQL QUOTE OF COLUMN NAMES

        def param(value):
            return "%("+value+")s"

        keys = dict.keys()

        command = "INSERT INTO "+quote(tableName)+"("+\
                  ",".join([quote(k) for k in keys])+\
                  ") VALUES ("+\
                  ",".join([param[k] for k in keys])+\
                  ")"

        self.cursor.execute(command, dict)
