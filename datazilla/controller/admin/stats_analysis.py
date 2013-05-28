from datetime import timedelta, datetime

from utils import error, nvl

def exception_point ():
    ##find single points that deviate from the trend

    #LOAD CONFIG

    #CALCULATE HOW FAR BACK TO LOOK
    #BRING IN ALL NEEDED DATA
    #FOR EACH PAGE
        #ROLL THROUGH SERIES LOOKING FOR EXCEPTIONS THAT DEVIATE GREATLY
        #CHECK IF ALREADY AN ALERT
            #IF SO, UPDATE
            #IF NOT, ADD
    pass




#simplest of rules to test the dataflow from test_run, to alert, to email
#may prove slightly useful too!
def page_threshold_limit ():
    typeName="page_threshold_limit"     #name of the reason in alert_mail_reason

    try:
        ##point out any pages that are breaking human-set threshold limits
        db = None

        #CALCULATE HOW FAR BACK TO LOOK
        last_run, description = db.query("SELECT last_run, description FROM alert_mail_reasons WHERE code=%s", typeName)[0]
        minDate=last_run+timedelta(month=-1)

        #FIND ALL PAGES THAT HAVE LIMITS TO TEST
        #BRING BACK ONES THAT BREAK LIMITS
        #BUT DO NOT ALREADY HAVE AN ALERTS EXISTING
        pages = db.query("""
            SELECT
                t.test_run_id,
                t.n_replicates,
                t.mean,
                t.std,
                h.threshold,
                h.severity,
                h.reason
            FROM
                alert_mail_page_thresholds h
            JOIN
                test_all_dimensions t ON t.page_id=h.page_id
            LEFT JOIN
                alert_mail m on m.test_run=t.test_run_id AND m.reason=%s
            WHERE
                h.threshold<t.mean AND
                t.push_date>%s AND
                m.id IS NULL 
        """, typeName, minDate.toUnixTime())

        #FOR EACH PAGE THAT BREAKS LIMITS
        for page in pages:
            alert_id = db.query("SELECT util_newID() id FROM DUAL")[0]["id"]

            alert = {
                "id":alert_id,
    	        "mail_state":"new",
                "create_time":datetime.utcnow(),
                "last_updated":datetime.utcnow(),
                "test_run":page["test_run_id"],
                "reason":typeName,
                "details":{"expected":page["threshold"], "actual":page["mean"], "reason":page["reason"]},
                "severity":page["severity"],
                "confidence":1.0  #USING NORMAL DIST ASSUMPTION WE CAN MESS WITH CONFIDENCE EVEN BEFORE THRESHOLD IS HIT!
            }

            db.insert=nvl(db.insert, insert)#upgrade db object
            db.insert("alert_mail", alert)

    except Exception, e:
        error("Could not perform threshold comparisons", e)

## mixin for the database connection object
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

    self.execute(command, dict)



      

