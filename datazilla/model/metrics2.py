import datetime
from datasource.bases.RDBSHub import RDBSHubExecuteError
from datazilla.model.metrics import MetricsTestModel
from datazilla.util.db import SQL, Connection
from datazilla.util.debug import D
from datazilla.util.map import Map

class DataSource(MetricsTestModel):
#inherit MetricsTestModel to add convenience methods

    def __init__(self, project):
        MetricsTestModel.__init__(self, project=project)
        self.execute_backlog=[]         #batch the inserts and updates to minimize db calls
        self.backlog_type=None          #used to track which piece of json is being used for the backlog
        self.committed=True


    @property
    def db(self):
    #this model has only one source
        return self.sources["perftest"].dhub

    
    def begin(self):
        if not self.committed: D.error("multiple begin not supported. yet")
        self.committed=False


    def execute_json(self,
                   json, #name of SQL template
                   param #ordered list of (name,value) tuples
    ):
        if self.committed: D.error("Must open a transaction first")
        # param is an ordered list of (name, value) tuples.
        # the names are ignored, for now
        if not isinstance(param, list): D.error("Expecting a list of tuples (until we have named parameters")
        if len(param)>0 and not isinstance(param[0], tuple):  D.error("Expecting a list of tuples (until we have named parameters")

        #the datasource can only handle one type of call at a time, so we must
        #push the current batch before we start accumulating another type
        if not self.backlog_type==json:
            self._execute_json_backlog()
            self.execute_backlog=[]
        self.backlog_type=json
        self.execute_backlog.append(param)




    def call_json(self, proc_name, param):
    #make call to database procedure
        self._execute_json_backlog()

        #replace when procedure calling is supported
        c=Connection(self._get_sql_db())
        c.begin()
        c.call(proc_name, param)
        c.commit()
        

    def query_json(self,
                   json, #name of SQL template
                   param #ordered list of (name,value) tuples
    ):
        self._execute_json_backlog()
        
        # param is an ordered list of (name, value) tuples.
        # the names are ignored, for now
        if not isinstance(param, list): D.error("Expecting a list of tuples (until we have named parameters")
        if len(param)>0 and not isinstance(param[0], tuple):  D.error("Expecting a list of tuples (until we have named parameters")

        # REFs are pure sql bits that should not be quoted.
        # It is assumed the bits of sql make sense in the overall sql
        refs=[p[1] for p in param if isinstance(p, SQL)]
        values=[p[1] for p in param if not isinstance(p, SQL)]

        try:
            results=self.db.execute(
                proc=json,
                debug_show=self.DEBUG,
                replace=refs,
                placeholders=values,
                nocommit=True,
                return_type='tuple'
                )
            return [Map(**r) for r in results]
        except Exception, e:
            D.error("Can not execute SQL\n"+self._get_sql(json), e)
        except RDBSHubExecuteError, r:
            D.error("Can not execute SQL\n"+self._get_sql(json), r)


            
    def insert_json(self, table_name, param):
    #just until we have an insert routine 
        def quote(value):
            return "`"+value+"`"    #MY SQL QUOTE OF COLUMN NAMES

        keys = param.keys()
        param = [(k, v) for k,v in param]
        name="insert into "+table_name+"("+",".join(keys)+")"

        if not self._get_sql(name):
            #register new sql into the json
            sql = "INSERT INTO "+quote(table_name)+"("+\
                  ",".join([quote(k) for k in keys])+\
                  ") VALUES ("+\
                  ",".join("?")+\
                  ")"
            self._set_sql(name,sql)

        self.execute_json(name, param)



    def rollback(self):
        self.backlog=[]     #YAY! FREE!
        self.db.rollback(self.db.default_host_type)
        self.committed=True

    def commit(self):
        self._execute_json_backlog()
        self.db.commit(self.db.default_host_type)
        self.committed=True

    def close(self):
        if not self.committed: D.error("Please commit, or rollback, before closing")
        self.db.close()


    def _execute_json_backlog(self):
    # private method to flush the backlog of update queries
    # executemany=True changes the refs and placeholders parameters to be lists
    # of parameters, instead of just parameters
        refs=[]
        values=[]

        for b in self.execute_backlog:
            # REFs are pure sql bits that should not be quoted.
            # It is assumed the bits of sql make sense in the overall sql
            refs.append([p[1] for p in b if isinstance(p, SQL)])
            values.append([p[1] for p in b if not isinstance(p, SQL)])
            try:
                self.db.execute(
                    proc=self.backlog_type,
                    debug_show=self.DEBUG,
                    replace=refs,
                    placeholders=values,
                    nocommit=True,
                    return_type='tuple',
                    executemany=True
                    )
            except Exception, e:
                D.error("Can not execute SQL\n"+self._get_sql(self.backlog_type), e)
            except RDBSHubExecuteError, r:
                D.error("Can not execute SQL\n"+self._get_sql(self.backlog_type), r)

        self.backlog_type=None


    def _get_sql_db(self):
    #return the underlying mysql connection object
        return self.db.connection["master_host"]["con_obj"]

    def _get_sql(self, name):
        return Map(**self.db.procs[self.db.data_source])[name].sql

    def _set_sql(self, name, sql):
        self.db.procs[self.db.data_source][name]["sql"]=sql