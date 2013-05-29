from datetime import datetime, timedelta
import json
from string import Template
from controller.admin.math_bayes import bayesianAdd
from model.util.Debug import D


ALERT_LIMIT = bayesianAdd(0.90, 0.70)  #SIMPLE severity*confidence LIMIT (FOR NOW)
TEMPLATE = Template("<div><h2>${score} - ${revision}</h2>${reason}</div><hr>")
RESEND_AFTER = timedelta(day=1)


def send_alerts(env):
    assert env.db is not None

    db = env.db


    db.begin()
    
    try:
        newAlerts = db.query("""
            SELECT
                a.id,
                a.reason,
                r.description,
                a.details,
                a.severity,
                a.confidence,
                t.revision
            FROM
                alert_mail a
            JOIN
                alert_mail_reasons r on r.code=a.reason
            JOIN
                test_all_dimensions t ON t.test_run_id=a.test_run_id
            WHERE
                (
                    a.last_sent IS NULL OR
                    a.last_sent < a.last_updated OR
                    a.last_sent < %{lastSent}s
                ) AND
                a.status <> 'obsolete' AND
                bayesian_add(a.severity, a.confidence) > %{alertLimit}s AND
                a.solution IS NULL AND
            """, {
                "lastSent":datetime.utcnow()-RESEND_AFTER,
                "alertLimit":ALERT_LIMIT
            })

        body=""
        for alert in newAlerts:
            details=json.loads(alert["details"])
            #EXPAND THE MESSAGE
            body=body+TEMPLATE.substitute({
                "score":round(bayesian_add(alert["severity"], alert["confidence"])*100, 0)+"%",  #AS A PERCENT
                "test_run_id":alert["test_run_id"],
                "revision":alert["revision"],
                "reason":Template(alert["description"]).substitute(details)
                })


#        listeners = SQLQuery.run({
#            "select":{"value":"email"},
#            "from":"alert_email_listener"
#        })
        #poor souls that signed up for emails
        listeners = [x["email"] for x in db.query("SELECT email FROM alert_email_listeners")]
        listeners = ";".join(listeners)

        db.execute("CALL email_send(%{to}s, %{subject}a, %{body}s, null)", {
            "to":listeners,
            "subject":"Bad news from tests",
            "body":body
        })

        #I HOPE I CAN SEND ARRAYS OF NUMBERS
        db.execute("UPDATE alert_email SET last_sent=%s WHERE id IN (%s)", [datetime.utcnow(), json.dumps(newAlerts)])
#        db.execute("UPDATE alert_email SET last_sent=%s WHERE id IN ("+",".join("%s"*len(newAlerts))+")", datetime.utcnow(), [a["id"] for a in newAlerts])

        db.commit()
    except Exception, e:
        db.rollback()
        error("Could not send alerts", e)

