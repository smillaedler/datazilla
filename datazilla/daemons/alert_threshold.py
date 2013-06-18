from datetime import timedelta, datetime
from datazilla.util.basic import nvl
from datazilla.util.cnv import CNV
from datazilla.util.db import SQL
from datazilla.util.debug import D






#simplest of rules to test the dataflow from test_run, to alert, to email
#may prove slightly useful also!
##point out any pages that are breaking human-set threshold limits
from datazilla.util.map import Map

def page_threshold_limit(**env):
    env=Map(**env)
    assert env.db is not None
    
    reason="page_threshold_limit"     #name of the reason in alert_reason

    db = env.db
    db.debug = env.debug

    try:
        #CALCULATE HOW FAR BACK TO LOOK
        db.begin()
        lasttime = db.query("SELECT last_run, description FROM alert_reasons WHERE code=${type}", {"type":reason})[0]
        lasttime = nvl(lasttime.last_run, datetime.utcnow())
        min_date=lasttime+timedelta(weeks=-4)

        #FIND ALL PAGES THAT HAVE LIMITS TO TEST
        #BRING BACK ONES THAT BREAK LIMITS
        #BUT DO NOT ALREADY HAVE AN ALERTS EXISTING
        pages = db.query("""
            SELECT
                t.id test_series_id,
                t.n_replicates,
                t.mean,
                t.std,
                h.threshold,
                h.severity,
                h.reason,
                m.id alert_id
            FROM
                alert_page_thresholds h
            JOIN
                test_data_all_dimensions t ON t.page_id=h.page
            LEFT JOIN
                alert_mail m on m.test_series=t.test_run_id AND m.reason=${type}
            WHERE
                h.threshold<t.mean AND
                t.push_date>${min_date} AND
                (m.id IS NULL OR m.status='obsolete')
            """,
            {"type":reason, "min_date":min_date}
        )

        #FOR EACH PAGE THAT BREAKS LIMITS
        for page in pages:
            if page.alert_id is not None: break

            alert = {
                "id":SQL("util_newID()"),
    	        "status":"new",
                "create_time":datetime.utcnow(),
                "last_updated":datetime.utcnow(),
                "test_series":page.test_series_id,
                "reason":reason,
                "details":CNV.object2JSON({"expected":float(page.threshold), "actual":float(page.mean), "reason":page.reason}),
                "severity":page.severity,
                "confidence":1.0    # USING NORMAL DIST ASSUMPTION WE CAN ADJUST
                                    # CONFIDENCE EVEN BEFORE THRESHOLD IS HIT!
                                    # FOR NOW WE KEEP IT SIMPLE
            }

            db.insert("alert_mail", alert)

        for page in pages:
            if page.alert_id is None: break
            db.update("alert_mail", None)  #ERROR FOR NOW


        #OBSOLETE THE ALERTS THAT SHOULD NO LONGER GET SENT
        obsolete = db.query("""
            SELECT
                m.id
            FROM
                alert_mail m
            JOIN
                test_data_all_dimensions t ON m.test_series=t.id
            JOIN
                alert_page_thresholds h on t.page_id=h.page
            WHERE
                m.reason=${reason} AND
                h.threshold>=t.mean AND
                t.push_date>${time}
            """,
            {
                "reason":reason,
                "time":min_date
            }
        )
        obsolete = [o["id"] for o in obsolete]

        if len(obsolete)>0:
            db.execute("UPDATE alert_mail SET status='obsolete' WHERE id IN ${list}", {"list":obsolete})

        db.execute(
            "UPDATE alert_reasons SET last_run=${now} WHERE code=${reason}",
            {"now":datetime.utcnow(), "reason":reason}
        )

        db.commit()
    except Exception, e:
        db.rollback()
        D.error("Could not perform threshold comparisons", e)


      
