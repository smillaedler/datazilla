################################################################################
## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this file,
## You can obtain one at http://mozilla.org/MPL/2.0/.
################################################################################
from datetime import datetime, timedelta
from datazilla.daemons.alert_exception import exception_point, REASON

from datazilla.util.cnv import CNV
from datazilla.util.db import SQL, DB
from datazilla.util.debug import D
from datazilla.util.map import Map
from datazilla.util.stats import closeEnough
from tests.util.testing import settings, make_test_database


EXPECTED_SEVERITY=0.9

class test_alert_exception:

    def __init__(self, db):
        self.db=db
        self.db.debug=True
        self.url="mozilla.com"


    def test_alert_generated(self):
        self._setup()

        exception_point (
            db=self.db,
            debug=True
        )

        ## VERIFY AN ALERT IS GENERATED
        alert=self.db.query("""
            SELECT
                id,
                status,
                create_time,
                test_series,
                reason,
                details,
                severity,
                confidence
            FROM
                alert_mail
            WHERE
                reason=${reason}
            """, {
                "reason":REASON
        })

        assert len(alert)==1
        assert alert[0].status=='new'
        assert closeEnough(alert[0].severity, EXPECTED_SEVERITY)
        assert alert[0].confidence==1.0

        #VERIFY last_run HAS BEEEN UPDATED
        last_run=self.db.query(
            "SELECT last_run FROM alert_reasons WHERE code=${type}",
            {"type":REASON}
        )[0].last_run
        expected_run_after=datetime.utcnow()+timedelta(minutes=-1)
        assert last_run>=expected_run_after

        #REMEMEBER id FOR CHECKING OBSOLETE
        self.alert_id=alert[0].id

        #VERIFY test_data_all_dimensions HAS BEEN MARKED PROPERLY
        h0_rejected = self.db.query("""
            SELECT
                h0_rejected
            FROM
                test_data_all_dimensions t
            JOIN
                alert_mail a ON a.test_series=t.id
            WHERE
                a.id=${alert_id}
            """,
            {"alert_id":alert[0].id}
        )

        assert len(h0_rejected)==1
        assert h0_rejected[0].h0_rejected==1














    def _setup(self):
        uid=self.db.query("SELECT util_newid() uid FROM DUAL")[0].uid

        ## VERFIY THE alert_reason EXISTS
        exists=self.db.query("""
            SELECT
                count(1) num
            FROM
                alert_reasons
            WHERE
                code=${reason}
            """,
            {"reason":REASON}
        )[0].num
        if exists==0:
            D.error("Expecting the database to have an alert_reason=${reason}", {"reason":REASON})

        ## MAKE A 'PAGE' TO TEST
        self.db.execute("DELETE FROM pages")
        self.db.insert("pages", {
            "test_id":0,
            "url":self.url
        })
        self.page_id=self.db.query("SELECT id FROM pages")[0].id

        ## ENSURE THERE ARE NO ALERTS IN DB
        self.db.execute("DELETE FROM alert_mail WHERE reason=${reason}", {"reason":REASON})

        ## diff_time IS REQUIRED TO TRANSLATE THE TEST DATE DATES TO SOMETHING MORE CURRENT
        now_time=CNV.datetime2unix(datetime.utcnow())
        max_time=max([CNV.datetime2unix(CNV.string2datetime(t.date, "%Y-%b-%d %H:%M:%S")) for t in CNV.table2list(test_data.header, test_data.rows)])
        diff_time=now_time-max_time

        ## INSERT THE TEST RESULTS
        for t in CNV.table2list(test_data.header, test_data.rows):
            time=CNV.datetime2unix(CNV.string2datetime(t.date, "%Y-%b-%d %H:%M:%S"))
            time+=diff_time

            self.db.insert("test_data_all_dimensions",{
                "id":SQL("util_newid()"),
                "test_run_id":SQL("util_newid()"),
                "product_id":0,
                "operating_system_id":0,
                "test_id":0,
                "page_id":self.page_id,
                "date_received":time,
                "revision":"ba928cbd5191",
                "product":"Firefox",
                "branch":"Mozilla-Inbound",
                "branch_version":"23.0a1",
                "operating_system_name":"mac",
                "operating_system_version":"OS X 10.8",
                "processor":"x86_64",
                "build_type":"opt",
                "machine_name":"talos-mtnlion-r5-049",
                "pushlog_id":19998363,
                "push_date":time,
                "test_name":"tp5o",
                "page_url":self.url,
                "mean":float(t.mean),
                "std":float(t["mean+std"])-float(t.mean),
                "h0_rejected":None,
                "p":None,
                "n_replicates":t.count,
                "fdr":0,
                "trend_mean":None,
                "trend_std":None,
                "test_evaluation":0,
                "status":1
            })





## DEFINE SOME TEST DATA
test_data=Map(**{
    "header":("date", "count", "mean-std", "mean", "mean+std"),
    "rows":[
        ("2013-Apr-05 13:55:00", "23", "655.048136994614", "668.5652173913044", "682.0822977879948"),
        ("2013-Apr-05 13:59:00", "23", "657.8717192954238", "673.3478260869565", "688.8239328784892"),
        ("2013-Apr-05 14:05:00", "23", "658.3247270429598", "673", "687.6752729570402"),
        ("2013-Apr-05 14:08:00", "23", "658.5476631609771", "673.6521739130435", "688.7566846651099"),
        ("2013-Apr-05 14:16:00", "23", "653.2311994952266", "666.1739130434783", "679.1166265917299"),
        ("2013-Apr-05 14:26:00", "23", "659.5613845589426", "671.8260869565217", "684.0907893541009"),
        ("2013-Apr-05 14:42:00", "23", "662.3517791831357", "677.1739130434783", "691.9960469038208"),
        ("2013-Apr-05 15:26:00", "23", "659.8270045518033", "672", "684.1729954481967"),
        ("2013-Apr-05 15:30:00", "23", "659.4023663187861", "674", "688.5976336812139"),
        ("2013-Apr-05 15:32:00", "23", "652.8643631817508", "666.9565217391304", "681.0486802965099"),
        ("2013-Apr-05 15:35:00", "23", "661.6037178485499", "675.1739130434783", "688.7441082384066"),
        ("2013-Apr-05 15:39:00", "23", "658.0124378440726", "670.1304347826087", "682.2484317211449"),
        ("2013-Apr-05 16:20:00", "46", "655.9645219644624", "667.4782608695652", "678.9919997746681"),
        ("2013-Apr-05 16:30:00", "23", "660.2572506418051", "671.8695652173913", "683.4818797929775"),
        ("2013-Apr-05 16:31:00", "23", "661.011102554583", "673.4347826086956", "685.8584626628083"),
        ("2013-Apr-05 16:55:00", "23", "655.9407699325201", "671.304347826087", "686.6679257196539"),
        ("2013-Apr-05 17:07:00", "23", "657.6412277100247", "667.5217391304348", "677.4022505508448"),
        ("2013-Apr-05 17:12:00", "23", "598.3432138277318", "617.7391304347826", "637.1350470418334"),
        ("2013-Apr-05 17:23:00", "23", "801.0537973113723", "822.1739130434783", "843.2940287755843")  # <--SPIKE IN DATA
    ]
})

make_test_database(settings)

with DB(settings.database) as db:
    tester=test_alert_exception(db)
    tester.test_alert_generated()

