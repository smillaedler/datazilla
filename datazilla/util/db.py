#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####
from datetime import datetime
from string import Template
import MySQLdb
from datazilla.model.utils import nvl
from datazilla.util.cnv import CNV
from datazilla.util.debug import D
from datazilla.util.map import Map
from datazilla.util.strings import indent
from datazilla.util.strings import outdent


DEBUG = False

class DB():

    def __init__(self, settings):
        self.db=MySQLdb.connect(
            host=settings.host,
            port=settings.port,
            user=nvl(settings.username, settings.user),
            passwd=nvl(settings.password, settings.passwd),
            db=nvl(settings.schema, settings.db)
        )
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
        self.execute_backlog()
        self.db.commit()
        self.committed=True

    def rollback(self):
        self.backlog=[]     #YAY! FREE!
        self.db.rollback()
        self.committed=True

    def call(self, proc_name, params):
        self.execute_backlog()
        try:
            self.cursor.callproc(proc_name, params)
            self.cursor.close()
            self.cursor=self.db.cursor()
        except Exception, e:
            D.error("Problem calling procedure "+proc_name, e)



    def query(self, sql, param=None):
        self.execute_backlog()
        try:
            old_cursor=self.cursor
            if old_cursor is None: #ALLOW NON-TRANSACTIONAL READS
                self.cursor=self.db.cursor()

            if param is not None: sql=Template(sql).substitute(self.quote(param))
            sql=outdent(sql)
            if self.debug: D.println("Execute SQL:\n"+indent(sql))

            self.cursor.execute(sql)

            columns = tuple( [d[0].decode('utf8') for d in self.cursor.description] )
            result=CNV.table2list(columns, self.cursor)

            if old_cursor is None:   #CLEANUP AFTER NON-TRANSACTIONAL READS
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



    def execute_backlog(self):
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
    def insert (self, table_name, param):
        def quote(value):
            return "`"+value+"`"    #MY SQL QUOTE OF COLUMN NAMES

        keys = param.keys()
        param = self.quote(param)

        command = "INSERT INTO "+quote(table_name)+"("+\
                  ",".join([quote(k) for k in keys])+\
                  ") VALUES ("+\
                  ",".join([param[k] for k in keys])+\
                  ")"

        self.execute(command)


    #convert values to mysql code for the same
    #mostly delegate directly to the mysql lib, but some exceptions exist
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


            
#ACTUAL SQL, DO NOT QUOTE THIS STRING
class SQL(str):

    def __init__(self, string=''):
        str.__init__(self, string)
