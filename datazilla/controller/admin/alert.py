from datetime import datetime, timedelta
import json
from string import Template
from datazilla.controller.admin.math_bayes import bayesianAdd
from datazilla.model.util.debug import D


ALERT_LIMIT = 0.4 # bayesianAdd(0.90, 0.70)  #SIMPLE severity*confidence LIMIT (FOR NOW)
TEMPLATE = Template("<div><h2>${score} - ${revision}</h2>${reason}</div><hr>\n")
RESEND_AFTER = timedelta(days=1)


def send_alerts(env):
    assert env.db is not None

    db = env.db
    db.debug = env.debug

    db.begin()
    
    try:
        newAlerts = db.query("""
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
                    a.last_sent < ${lastSent}
                ) AND
                a.status <> 'obsolete' AND
                bayesian_add(a.severity, a.confidence) > ${alertLimit} AND
                a.solution IS NULL
            """, {
                "lastSent":datetime.utcnow()-RESEND_AFTER,
                "alertLimit":ALERT_LIMIT
            })

        if len(newAlerts)==0:
            if env.debug: D.println("Nothing important to email")
            return

        body=""
        for alert in newAlerts:
            details=json.loads(alert.details)
            #EXPAND THE MESSAGE
            body=body+TEMPLATE.substitute({
                "score":str(round(bayesianAdd(alert.severity, alert.confidence)*100, 0))+"%",  #AS A PERCENT
                "revision":alert.revision,
                "reason":Template(alert.description).substitute(details)
                })


#        listeners = SQLQuery.run({
#            "select":{"value":"email"},
#            "from":"alert_email_listener"
#        })
        #poor souls that signed up for emails
        listeners=db.query("SELECT email FROM alert_listeners")
        listeners = [x["email"] for x in listeners]
        listeners = ";".join(listeners)

        if len(body)>8000:
            D.println("Truncated the email body")
            body=body[0:8000]    #keep it reasonable
        
        db.call("email_send", (
            listeners, #to
            "Bad news from tests", #title
            body, #body
            None
        ))

        #I HOPE I CAN SEND ARRAYS OF NUMBERS
        if len(newAlerts)>0:
            db.execute(
                "UPDATE alert_mail SET last_sent=${time} WHERE id IN ${sendList}",
                {"time":datetime.utcnow(), "sendList":[a["alert_id"] for a in newAlerts]}
            )

        db.commit()
    except Exception, e:
        db.rollback()
        D.error("Could not send alerts", e)

