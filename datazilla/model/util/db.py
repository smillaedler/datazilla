#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####
from datetime import datetime
from string import Template
import MySQLdb
from datazilla.model.util.bunch import Bunch
from datazilla.model.util.debug import D




## return a database connection
from datazilla.model.util.strings import indent
from datazilla.model.util.strings import outdent
from datazilla.model.utils import datazilla

def getDatabaseConnection(project, schema):

    return Connection(MySQLdb.connect(
        host=datazilla.settings.DATABASE_HOST,
        port=int(datazilla.settings.DATABASE_PORT),
        user=datazilla.settings.DATABASE_USER,
        passwd=datazilla.settings.DATABASE_PASSWORD,
        db=project+"_"+schema+"_1"
    ))


DEBUG = False


class Connection():

    def __init__(self, db):
        self.db=db
        self.cursor=None
        self.committed=True
        self.debug=DEBUG
        self.backlog=[]     #accumulate the write commands so they are sent at once

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
        self.executeBacklog()
        self.db.commit()
        self.committed=True

    def rollback(self):
        self.backlog=[]     #YAY! FREE!
        self.db.rollback()
        self.committed=True

    def call(self, procName, params):
        self.executeBacklog()
        try:
            self.cursor.callproc(procName, params)
            self.cursor.close()
            self.cursor=self.db.cursor()
        except Exception, e:
            D.error("Problem calling procedure "+procName, e)



    def query(self, sql, param=None):
        self.executeBacklog()
        try:
            oldCursor=self.cursor
            if oldCursor is None: #ALLOW NON-TRANSACTIONAL READS
                self.cursor=self.db.cursor()

            if param is not None: sql=Template(sql).substitute(self.quote(param))
            sql=outdent(sql)
            if self.debug: D.println("Execute SQL:\n"+indent(sql))

            self.cursor.execute(sql)

            result = []
            columns = tuple( [d[0].decode('utf8') for d in self.cursor.description] )
            for row in self.cursor:
                result.append(Bunch(zip(columns, row)))

            if oldCursor is None:   #CLEANUP AFTER NON-TRANSACTIONAL READS
                self.cursor.close()
                self.cursor=None

            return result
        except Exception, e:
            D.error("Problem executing SQL:\n"+indent(sql.strip()), e, offset=1)


    def execute(self, sql, param=None):
        if self.cursor is None: D.error("Expecting transation to be started before issuing queries")

        if param is not None: sql=Template(sql).substitute(self.quote(param))
        sql=outdent(sql)
        self.backlog.append(sql)



    def executeBacklog(self):
        if len(self.backlog)==0: return

        sql=";\n".join(self.backlog)
        try:
            if self.debug: D.println("Execute block of SQL:\n"+indent(sql))
            self.cursor.execute(sql)
            self.cursor.close()
            self.cursor = self.db.cursor()
        except Exception, e:
            D.error("Problem executing SQL:\n"+indent(sql.strip()), e, offset=1)

        self.backlog=[]


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

        self.execute(command)


    def quote(self, param):
        try:
            output={}
            for k, v in [(k, param[k]) for k in param.keys()]:
                if isinstance(v, datetime):
                    v=SQL("str_to_date('"+v.strftime("%Y%m%d%H%M%S")+"', '%Y%m%d%H%i%s')")
                elif isinstance(v, list):
                    v=SQL("("+",".join([self.db.literal(vv) for vv in v])+")")
                elif isinstance(v, SQL):
                    pass      
                else:
                    v=SQL(self.db.literal(v))

                output[k]=v
            return output
        except Exception, e:
            D.error("problem quoting SQL", e)


#ACTUAL SQL
class SQL(str):

    def __init__(self, string=''):
        str.__init__(self, string)
