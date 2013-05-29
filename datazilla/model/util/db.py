#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####
import MySQLdb
from django.conf import LazySettings
from datazilla import settings

from datazilla.model.base import PerformanceTestModel
from datazilla.model.util.debug import D


## return a database connection
def getDatabaseConnection(project, schema):

    settings = LazySettings()
    
    return Connection(MySQLdb.connect(
        host=settings.DATAZILLA_DATABASE_HOST,
        port=int(settings.DATAZILLA_DATABASE_PORT),
        user=settings.DATAZILLA_DATABASE_USER,
        passwd=settings.DATAZILLA_DATABASE_PASSWORD,
        db=project+"_"+schema+"_1"
    ))




class Connection():

    def __init__(self, db):
        self.db=db
        self.cursor=None
        self.committed=True

    def begin(self):
        if self.cursor is not None:
            D.error("multiple begin not supported. yet")
        self.cursor=self.db.cursor()
        self.committed=False

    def close(self):
        if not self.committed:
           D.error("expecting commit() or rollback() before close")
        self.cursor.close()
        self.cursor=None

    def commit(self):
        self.db.commit()
        self.committed=True

    def rollback(self):
        self.db.rollback()
        self.committed=True

    def query(self, sql, param=None):
        self.cursor.execute(sql, param)
        return self.cursor.fecthall()

    def execute(self, sql, param=None):
        self.cursor.execute(sql, param)
        return self.cursor.fecthall()

        
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
