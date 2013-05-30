from datetime import timedelta, datetime
from datazilla.model.util.debug import D






#simplest of rules to test the dataflow from test_run, to alert, to email
#may prove slightly useful too!
##point out any pages that are breaking human-set threshold limits
from datazilla.model.utils import nvl

def page_threshold_limit (env):
    assert env.db is not None
    
    typeName="page_threshold_limit"     #name of the reason in alert_mail_reason

    try:
        db = env.db
        db.debug = env.debug

        #CALCULATE HOW FAR BACK TO LOOK
        db.begin()
        lasttime = db.execute("SELECT last_run, description FROM alert_mail_reasons WHERE code=${type}", {"type":typeName})[0]
        minDate=lasttime["last_run"]+timedelta(weeks=-4)

        #FIND ALL PAGES THAT HAVE LIMITS TO TEST
        #BRING BACK ONES THAT BREAK LIMITS
        #BUT DO NOT ALREADY HAVE AN ALERTS EXISTING
        pages = db.execute("""
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
                test_data_all_dimensions t ON t.page_id=h.page
            LEFT JOIN
                alert_mail m on m.test_run=t.test_run_id AND m.reason=${type}
            WHERE
                h.threshold<t.mean AND
                t.push_date>${minDate} AND
                (m.id IS NULL OR m.status='obsolete')
            """,
            {"type":typeName, "minDate":minDate}
        )

        #FOR EACH PAGE THAT BREAKS LIMITS
        for page in pages:
            alert_id = db.execute("SELECT util_newID() id FROM DUAL")[0]["id"]

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
                    m.reason=%{reason}s AND
                    h.threshold>=t.mean AND
                    t.push_date>%{time}s
            )""",
            {
                "reason":typeName,
                "time":minDate.toUnixTime()
            }
        )

    except Exception, e:
        D.error("Could not perform threshold comparisons", e)


      
