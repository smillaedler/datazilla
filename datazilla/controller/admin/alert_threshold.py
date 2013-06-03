from datetime import timedelta, datetime
from datazilla.util.cnv import CNV
from datazilla.util.db import SQL
from datazilla.util.debug import D




#simplest of rules to test the dataflow from test_run, to alert, to email
#may prove slightly useful too!
##point out any pages that are breaking human-set threshold limits
def page_threshold_limit (env):
    type_name="page_threshold_limit"     #name of the reason in alert_reason

    db = env.db

    try:
        #CALCULATE HOW FAR BACK TO LOOK
        db.begin()
        lasttime = db.query_json(
#                SELECT last_run, description FROM alert_reasons WHERE code=?
            "perftest.selects.get_threshold_alert_reasons",
            [("type",type_name)]
        )[0]
        min_date=lasttime["last_run"]+timedelta(weeks=-4)

        #FIND ALL PAGES THAT HAVE LIMITS TO TEST
        #BRING BACK ONES THAT BREAK LIMITS
        #BUT DO NOT ALREADY HAVE AN ALERTS EXISTING
        pages = db.query_json(
#                
#                SELECT
#                    t.id test_series_id,
#                    t.n_replicates,
#                    t.mean,
#                    t.std,
#                    h.threshold,
#                    h.severity,
#                    h.reason,
#                    m.id alert_id
#                FROM
#                    alert_page_thresholds h
#                JOIN
#                    test_data_all_dimensions t ON t.page_id=h.page
#                LEFT JOIN
#                    alert_mail m on m.test_series=t.test_run_id AND m.reason=?
#                WHERE
#                    h.threshold<t.mean AND
#                    t.push_date>? AND
#                    (m.id IS NULL OR m.status='obsolete')
            "perftest.selects.get_threshhold_new_alerts",
            [
                ("type",type_name),
                ("min_date",min_date)
            ]
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
                "reason":type_name,
                "details":CNV.object2JSON({"expected":float(page.threshold), "actual":float(page.mean), "reason":page.reason}),
                "severity":page.severity,
                "confidence":1.0  #USING NORMAL DIST ASSUMPTION WE CAN MESS WITH CONFIDENCE EVEN BEFORE THRESHOLD IS HIT!
            }

            db.insert_json("alert_mail", alert)

        for page in pages:
            if page.alert_id is None: break
            db.update("alert_mail", None)  #ERROR FOR NOW


        #OBSOLETE THE ALERTS THAT SHOULD NO LONGER GET SENT
        obsolete = db.query_json(
#                
#                SELECT
#                    m.id
#                FROM
#                    alert_mail m
#                JOIN
#                    test_data_all_dimensions t ON m.test_series=t.test_run_id
#                JOIN
#                    alert_page_thresholds h on t.page_id=h.page
#                WHERE
#                    m.reason=? AND
#                    h.threshold>=t.mean AND
#                    t.push_date>?
            "perftest.selects.get_threshold_existing_alerts",
            [
                ("reason",type_name),
                ("time",min_date)
            ]
        )
        obsolete = SQL(",".join([o["id"] for o in obsolete]))

        if len(obsolete)>0:
            db.execute_json(
#                UPDATE alert_mail SET status='obsolete' WHERE id IN (REP0)
                "perftest.inserts.set_threshold_obsolete_alerts",
                [("list",obsolete)]
            )
        db.commit()
        db.close()
    except Exception, e:
        db.rollback()
        db.close()
        D.error("Could not perform threshold comparisons", e)



