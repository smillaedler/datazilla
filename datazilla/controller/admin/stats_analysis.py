from datetime import timedelta, datetime
from model.utils import getDatabaseConnection, error, nvl


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
def page_threshold_limit (project):
    typeName="page_threshold_limit"     #name of the reason in alert_mail_reason

    try:
        ##point out any pages that are breaking human-set threshold limits
        db = getDatabaseConnection(project, "perftest")

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
                h.reason,
                m.id alert_id
            FROM
                alert_mail_page_thresholds h
            JOIN
                test_all_dimensions t ON t.page_id=h.page_id
            LEFT JOIN
                alert_mail m on m.test_run=t.test_run_id AND m.reason=%s
            WHERE
                h.threshold<t.mean AND
                t.push_date>%s AND
                (m.id IS NULL OR m.status='obsolete')
        """, typeName, minDate.toUnixTime())

        #FOR EACH PAGE THAT BREAKS LIMITS
        for page in pages:
            alert_id = db.query("SELECT util_newID() id FROM DUAL")[0]["id"]

            alert = {
                "id":nvl(page["alert_id"], alert_id),
    	        "status":"new",
                "create_time":datetime.utcnow(),
                "last_updated":datetime.utcnow(),
                "test_run":page["test_run_id"],
                "reason":typeName,
                "details":{"expected":page["threshold"], "actual":page["mean"], "reason":page["reason"]},
                "severity":page["severity"],
                "confidence":1.0  #USING NORMAL DIST ASSUMPTION WE CAN MESS WITH CONFIDENCE EVEN BEFORE THRESHOLD IS HIT!
            }

            if page["mail_id"] is None:
                db.insert("alert_mail", alert)
            else:
                db.update("alert_mail", alert)


        #OBSOLETE THE ALERTS THAT SHOULD NO LONGER GET SENT
        db.execute("""
            UPDATE alert_mail SET status='obsolete' WHERE id IN (
                SELECT
                    m.id
                FROM
                    alert_mail m
                JOIN
                    test_all_dimensions t ON m.test_run=t.test_run_id
                JOIN
                    alert_mail_page_thresholds h on t.page_id=h.page_id
                WHERE
                    m.reason=%s AND
                    h.threshold>=t.mean AND
                    t.push_date>%s
            )
        """, typeName, minDate.toUnixTime())

    except Exception, e:
        error("Could not perform threshold comparisons", e)


      
