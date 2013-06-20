from datetime import datetime, timedelta
import json
from string import Template
from datazilla.util.cnv import CNV
from datazilla.util.map import Map
from datazilla.util.maths import bayesian_add
from datazilla.util.debug import D


ALERT_LIMIT = bayesian_add(0.90, 0.70)  #SIMPLE severity*confidence LIMIT (FOR NOW)
TEMPLATE = Template("<div><h2>${score} - ${revision}</h2>${reason}</div>\n")
SEPARATOR = "<hr>\n"
RESEND_AFTER = timedelta(days=1)
MAX_EMAIL_LENGTH = 8000
EPSILON = 0.0001



def send_alerts(**env):
    env=Map(**env)
    assert env.db is not None

    db = env.db
    db.debug = env.debug

    db.begin()

    try:
        new_alerts = db.query("""
            SELECT
                a.id alert_id,
                a.reason,
                r.description,
                a.details,
                a.severity,
                a.confidence,
                t.revision
            FROM
                alert_mail a
            JOIN
                alert_reasons r on r.code=a.reason
            JOIN
                test_data_all_dimensions t ON t.id=a.test_series
            WHERE
                (
                    a.last_sent IS NULL OR
                    a.last_sent < a.last_updated OR
                    a.last_sent < ${last_sent}
                ) AND
                a.status <> 'obsolete' AND
                bayesian_add(a.severity, a.confidence) > ${alert_limit} AND
                a.solution IS NULL
            """, {
                "last_sent":datetime.utcnow()-RESEND_AFTER,
                "alert_limit":ALERT_LIMIT-EPSILON
            })

        if len(new_alerts)==0:
            if env.debug: D.println("Nothing important to email")
            return

        body=[]
        for alert in new_alerts:
            details=CNV.JSON2object(alert.details)
            #EXPAND THE MESSAGE
            body.append(TEMPLATE.substitute({
                "score":str(round(bayesian_add(alert.severity, alert.confidence)*100, 0))+"%",  #AS A PERCENT
                "revision":alert.revision,
                "reason":Template(alert.description).substitute(details)
                }))
        body=SEPARATOR.join(body)

#        listeners = SQLQuery.run({
#            "select":{"value":"email"},
#            "from":"alert_email_listener"
#        })
        #poor souls that signed up for emails
        listeners=db.query("SELECT email FROM alert_listeners")
        listeners = [x["email"] for x in listeners]
        listeners = ";".join(listeners)

        if len(body)>MAX_EMAIL_LENGTH:
            D.println("Truncated the email body")
            suffix="... (has been truncated)"
            body=body[0:MAX_EMAIL_LENGTH-len(suffix)]+suffix   #keep it reasonable

        db.call("email_send", (
            listeners, #to
            "Bad news from tests", #title
            body, #body
            None
        ))

        #I HOPE I CAN SEND ARRAYS OF NUMBERS
        if len(new_alerts)>0:
            db.execute(
                "UPDATE alert_mail SET last_sent=${time} WHERE id IN ${send_list}",
                {"time":datetime.utcnow(), "send_list":[a["alert_id"] for a in new_alerts]}
            )

        db.commit()
    except Exception, e:
        db.rollback()
        D.error("Could not send alerts", e)

# REVIEW THE ALERT TABLE AND ENSURE THE test_data_all_dimensions(h0_rejected)
# COLUMN REFLECTS THE ALERT STATI
def update_h0_rejected(db, start_date):
    db.execute("""
        UPDATE 
            test_data_all_dimensions t
        JOIN (
            SELECT
                test_series,
                max(CASE WHEN status<>'obsolete' THEN 1 ELSE 0 END) h0
            FROM
                alert_mail
            GROUP BY
                test_series
            ) a ON a.test_series=t.id
        SET t.h0_rejected=a.h0
    """)
    