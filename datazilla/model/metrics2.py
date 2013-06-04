
from datazilla.model.metrics import MetricsTestModel
from datazilla.util.db import SQL
from datazilla.util.debug import D

class MetricsTestModel2(MetricsTestModel):
#inherit MetricsTestModel to add convenience methods

    def __init__(self):
        MetricsTestModel.__init__(self)
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


    def execute_json(self, json, param):
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

        self.db.execute(
            proc=self.backlog_type,
            debug_show=self.DEBUG,
            refs=refs,
            placeholders=values,
            nocommit=True,
            return_type='tuple',
            executemany=True
            )

        self.backlog_type=None


    def query_json(self, json, param):
        self._execute_json_backlog()
        
        # param is an ordered list of (name, value) tuples.
        # the names are ignored, for now
        if not isinstance(param, list): D.error("Expecting a list of tuples (until we have named parameters")
        if len(param)>0 and not isinstance(param[0], tuple):  D.error("Expecting a list of tuples (until we have named parameters")

        # REFs are pure sql bits that should not be quoted.
        # It is assumed the bits of sql make sense in the overall sql
        refs=[p[1] for p in param if isinstance(p, SQL)]
        values=[p[1] for p in param if not isinstance(p, SQL)]

        return self.db.execute(
            proc=json,
            debug_show=self.DEBUG,
            refs=refs,
            placeholders=values,
            nocommit=True,
            return_type='tuple'
            )


    def rollback(self):
        self.backlog=[]     #YAY! FREE!
        self.db.rollback()
        self.committed=True

    def commit(self):
        self._execute_json_backlog()
        self.db.commit()
        self.committe=True
