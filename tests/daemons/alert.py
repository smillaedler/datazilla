from datetime import datetime, timedelta
from datazilla import daemons
from datazilla.daemons.alert import send_alerts
from datazilla.util.cnv import CNV
from datazilla.util.db import DB
from datazilla.util.map import Map
from datazilla.util.maths import bayesian_add
from datazilla.util.query import Q
from datazilla.util.strings import between
from util.testing import settings

class test_alert:
# datazilla.daemons.alert.py IS A *FUNCTION* WITH DOMAIN alert_* AND CODOMAIN email_*
# self.test_data HAS THE DOMAIN VALUES TO TEST
#
# self.test_data[].details INCLUDES THE pass/fail INDICATION SO THE VERIFICATION
# LOGIC KNOWS WHAT SHOULD BE IN THOSE email_* TABLES


    def __init__(self):
        self.now=datetime.utcnow()
        self.recent_past=now-timedelta(hours=1)
        self.far_past=now-timedelta(days=2)

        self.db=DB(settings.database)
        self.uid=self.db.query("SELECT util_newid() uid FROM DUAL")[0].uid

        self.series=0

        self.reason="used for testing 1"

        self.high_severity=0.7
        self.high_confidence=0.9
        self.important=bayesian_add(self.high_severity, self.high_confidence)
        self.low_severity=0.5
        self.low_confidence=0.7



    def setup(self, to_list):
        self.uid=self.db.query("SELECT util_newid() uid FROM DUAL")[0].uid

        #TEST NUMBER OF LISTENERS IN alert_listeners TABLE
        self.db.execute("DELETE FROM alert_listeners")
        self.db.insert("alert_listeners", [{"email":l} for l in to_list])


        #MAKE A REASON FOR USE IN THIS TESTING
        self.db.execute("DELETE FROM alert_mail WHERE reason=${reason}", {"reason":self.reason})
        self.db.execute("DELETE FROM alert_reasons WHERE code=${reason}", {"reason":self.reason})
        self.db.insert("alert_reasons", {
            "code":self.reason,
            "description":">>>>${id}<<<<",
            "config":None
        })

        # WE INJECT THE EXPECTED TEST RESULTS RIGHT INTO THE DETAILS, THAT WAY
        # WE CAN SEE THEM IN THE EMAIL DELIVERED
        test_data=Map({
            "header":
                ("id",      "status",  "create_time", "last_updated", "last_sent",        "test_series", "reason",    "details",                 "severity",         "confidence",        "solution"),
            "data":[
                #TEST last_sent IS NOT TOO YOUNG
                (self.uid+0,"new",      self.far_past, self.far_past,  self.recent_past, self.series,   self.reason, CNV.object2JSON({"id":0, "expect":"fail"}),  self.high_severity, self.high_confidence, None),
                #TEST last_sent IS TOO OLD, SHOULD BE (RE)SENT
                (self.uid+1,"new",      self.far_past, self.now,       None,             self.series,   self.reason, CNV.object2JSON({"id":1, "expect":"pass"}),  self.high_severity, self.high_confidence, None),
                (self.uid+2,"new",      self.far_past, self.now,       self.far_past,    self.series,   self.reason, CNV.object2JSON({"id":2, "expect":"pass"}),  self.high_severity, self.high_confidence, None),
                (self.uid+3,"new",      self.now,      self.now,       self.recent_past, self.series,   self.reason, CNV.object2JSON({"id":3, "expect":"pass"}),  self.high_severity, self.high_confidence, None),
                #TEST obsolete ARE NOT SENT
                (self.uid+4,"obsolete", self.now,      self.now,       self.now,         self.series,   self.reason, CNV.object2JSON({"id":4, "expect":"fail"}),  self.high_severity, self.high_confidence, None),
                #TEST ONLY IMPORTANT ARE SENT
                (self.uid+5,"new",      self.now,      self.now,       None,             self.series,   self.reason, CNV.object2JSON({"id":5, "expect":"pass"}),  self.important,     0.5,                  None),
                (self.uid+6,"new",      self.now,      self.now,       None,             self.series,   self.reason, CNV.object2JSON({"id":6, "expect":"fail"}),  self.low_severity,  self.high_confidence, None),
                (self.uid+7,"new",      self.now,      self.now,       None,             self.series,   self.reason, CNV.object2JSON({"id":7, "expect":"fail"}),  self.high_severity, self.low_confidence,  None),
                #TEST ONES WITH SOLUTION ARE NOT SENT
                (self.uid+8,"new",      self.now,      self.now,       None,             self.series,   self.reason, CNV.object2JSON({"id":8, "expect":"fail"}),  self.high_severity, self.high_confidence, "a solution!")
                ]
        })

        self.test_data=CNV.table2list(test_data.header, test_data.data)
        self.db.insert("alert_mail", test_data)

        

    def test_send_zero_alerts(self):
        to_list=[]
        self.help_send_alerts(to_list)

    def test_send_one_alert(self):
        to_list=["klahnakoski@mozilla.com"]
        self.help_send_alerts(to_list)

    def test_send_many_alerts(self):
        to_list=[self.uid+"_"+str(i)+"@mozilla.com" for i in range(0,10)]
        self.help_send_alerts(to_list)


    def help_send_alerts(self, to_list):
        self.setup(to_list)

        ########################################################################
        # TEST
        ########################################################################
        send_alerts(
            db=self.db,
            debug=True
        )

        ########################################################################
        # VERIFY
        ########################################################################
        expecting_alerts=set([d.id for d in map(lambda d: CNV.JSON2object(d.details), self.test_data) if d.expect=='pass'])
        if len(to_list)==0: expecting_alerts=[]

        emails=self.get_new_emails() # id, to, body

        #VERIFY ONE MAIL SENT
        assert len(emails)==1
        #VERIFY to MATCHES WHAT'S EXPECTED
        assert set(emails[0].to) == set(to_list)

        #VERIFY last_sent IS WRITTEN
        alert_state=self.db.execute("""
            SELECT
                id
            FROM
                alert_mail
            WHERE
                reason=${reason} AND
                last_sent>=${send_time}
        """, {
            "reason":self.reason,
            "send_time":self.now
        })
        actual_marked=set(Q.select(alert_state, "id"))
        assert expecting_alerts == actual_marked

        #VERIFY BODY HAS THE CORRECT ALERTS
        actual_alerts_sent=set([int(between(b, ">>>>", "<<<<")) for b in emails[0].body.split(daemons.alert.SEPARATOR)])
        assert expecting_alerts == actual_alerts_sent



    def get_new_emails(self):
        emails=self.db.query("""
            SELECT
                c.id,
                group_concat(d.deliver_to SEPARATOR ',') `to`,
                c.body
            FROM
                email_content c
            LEFT JOIN
                email_delivery d ON d.content=c.id
            WHERE
                c.date_sent IS NULL
            GROUP BY
                c.id
            """)
        for e in emails: e.to=e.to.split(",")

        return emails