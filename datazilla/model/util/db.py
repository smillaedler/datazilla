#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####
from datetime import datetime
from string import Template
import string
import MySQLdb
from django.conf import LazySettings
from datazilla import settings
from datazilla.model.base import PerformanceTestModel
from datazilla.model.util.debug import D




## return a database connection
from datazilla.model.utils import indent
from datazilla.model.utils import unindent

def getDatabaseConnection(project, schema):

    settings = LazySettings()
    
    return Connection(MySQLdb.connect(
        host=settings.DATAZILLA_DATABASE_HOST,
        port=int(settings.DATAZILLA_DATABASE_PORT),
        user=settings.DATAZILLA_DATABASE_USER,
        passwd=settings.DATAZILLA_DATABASE_PASSWORD,
        db=project+"_"+schema+"_1"
    ))


DEBUG = False


class Connection():

    def __init__(self, db):
        self.db=db
        self.cursor=None
        self.committed=True
        self.debug=DEBUG

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

    def call(self, procName, params):
        try:
            self.cursor.callproc(procName, params)
        except Exception, e:
            D.error("Problem calling procedure "+procName, e)



    def execute(self, sql, param=None):

        if self.cursor is None: D.error("Expecting transation to be started before issuing queries")
        try:
            if param is not None: sql=Template(sql).substitute(self.quote(param))
            sql=unindent(sql)
            if self.debug: D.println("Execute SQL:\n"+indent(sql))
            self.cursor.execute(sql)

            result = []
            columns = tuple( [d[0].decode('utf8') for d in self.cursor.description] )
            for row in self.cursor:
                result.append(dict(zip(columns, row)))
            return result
        except Exception, e:
            D.error("Problem executing SQL:\n"+indent(sql.strip()), e, offset=1)

        
    ## Insert dictionary of values into table
    def insert (self, tableName, param):
        def quote(value):
            return "`"+value+"`"    #MY SQL QUOTE OF COLUMN NAMES

        keys = param.keys()
        param = self.quote(param)

        command = "INSERT INTO "+quote(tableName)+"("+\
                  ",".join([quote(k) for k in keys])+\
                  ") VALUES ("+\
                  ",".join([param[k] for k in keys])+\
                  ")"

        self.cursor.execute(command)


    def quote(self, param):
        try:
            keys = param.keys()
            values = [param[k] for k in keys]

            output={}
            for i in [0,len(keys)-1]:
                v=values[i]
                if isinstance(v, datetime):
                    v="str_to_date('"+v.strftime("%Y%m%d%H%M%S")+"', '%Y%m%d%H%i%s')"
                elif isinstance(v, list):
                    v="("+",".join([self.db.literal(vv) for vv in v])+")"
                else:
                    v=self.db.literal(v)

                output[keys[i]]=v
            return output
        except Exception, e:
            D.error("problem quoting SQL", e)

    