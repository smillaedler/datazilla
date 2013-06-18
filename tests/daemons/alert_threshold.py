################################################################################
## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this file,
## You can obtain one at http://mozilla.org/MPL/2.0/.
################################################################################


from datazilla.daemons.alert_threshold import page_threshold_limit
from datazilla.util.cnv import CNV
from datazilla.util.db import SQL, DB
from datazilla.util.debug import D

from util.testing import settings, make_test_database




class test_alert_threshold:

    def __init__(self, db):
        self.db=db
        self.url="amazon.com"   #JUST A DUMMY VALUE
        self.reason='page_threshold_limit'
        self.severity=0.5




    def setup(self):
        uid=self.db.query("SELECT util_newid() uid FROM DUAL")[0].uid

        ## VERFIY THE alert_reason EXISTS
        exists=self.db.query("SELECT count(1) FROM alert_reasons WHERE code='page_threshold_limit'")
        if exists==0:
            D.error("Expecting the database to have an alert_reason=${reason}", {"reason":self.reason})
        

        ## ADD A THRESHOLD TO TEST WITH
        self.db.execute("""
            INSERT INTO alert_page_thresholds (
                id,
                page,
                threshold,
                severity,
                reason,
                time_added,
                contact
            )
            SELECT
                ${uid},
                p.id,
                ${threshold},
                ${severity},
                concat("(", ${url}, ") for test"),
                now(),
                "klahnakoski@mozilla.com"
            FROM
                pages p
            WHERE
                p.url=${url}
            """, {
            "uid":uid,
            "url":self.url,
            "severity":self.severity,
            "threshold":800
        })

        ##ENSURE THERE ARE NO ALERTS IN DB
        self.db.execute("DELETE FROM alert_mail WHERE reason=${reason}", {"reason":self.reason})



    def test_alert_generated(self):
        self.setup()

        page_threshold_limit ({
            "db":self.db,
            "debug":True
        })


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
                "reason":self.reason
        })

        assert len(alert)==1
        assert alert[0].staus=='new'
        assert alert[0].severity==self.severity
        assert alert[0].confidence==1.0

        #REMEMEBER id FOR CHECKING OBSOLETE
        self.id=alert[0].id



    ## TEST AN INCREASE IN THE THRESHOLD OBSOLETES THE ALERT
    def test_alert_obsolete(self):

        assert self.id is not None  #EXPECTING test_alert_generated TO BE RUN FIRST


        pass



    def make_test_data(self):

        for t in CNV.table2list(test_data.header, test_data.rows):
            time=CNV.datetime2unix(CNV.string2datetime(t.date, "%Y-%m-%d %h:%M:%S"))

            self.db.insert("test_data_all_dimensions",{
                "date_run":time,
                "id":SQL("util_newid()"),
                "test_run_id":test_run_id119181,
                "product_id":0,
                "operating_system_id":0,
                "test_id":0,
                "page_id":0,
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
                "mean":t.mean,
                "std":t["std+mean"]-t.mean,
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
test_data={
    "header":("date", "count", "mean-std", "mean", "mean+std"),
    "rows":[
        ("2013-Apr-05 13:53:00", "23", "458.4859477694967", "473.30434782608694", "488.1227478826772"),
        ("2013-Apr-05 13:55:00", "23", "655.048136994614", "668.5652173913044", "682.0822977879948"),
        ("2013-Apr-05 13:56:00", "23", "452.89061649510194", "466.9130434782609", "480.9354704614198"),
        ("2013-Apr-05 13:59:00", "23", "657.8717192954238", "673.3478260869565", "688.8239328784892"),
        ("2013-Apr-05 14:03:00", "23", "447.32039354456913", "458.4347826086956", "469.5491716728221"),
        ("2013-Apr-05 14:05:00", "23", "658.3247270429598", "673", "687.6752729570402"),
        ("2013-Apr-05 14:08:00", "23", "658.5476631609771", "673.6521739130435", "688.7566846651099"),
        ("2013-Apr-05 14:10:00", "46", "492.8191446281407", "581.7608695652174", "670.702594502294"),
        ("2013-Apr-05 14:16:00", "23", "653.2311994952266", "666.1739130434783", "679.1166265917299"),
        ("2013-Apr-05 14:20:00", "23", "467.2878043841933", "480.4782608695652", "493.6687173549371"),
        ("2013-Apr-05 14:26:00", "23", "659.5613845589426", "671.8260869565217", "684.0907893541009"),
        ("2013-Apr-05 14:42:00", "23", "662.3517791831357", "677.1739130434783", "691.9960469038208"),
        ("2013-Apr-05 15:22:00", "46", "473.9206889491661", "574.0869565217391", "674.2532240943121"),
        ("2013-Apr-05 15:26:00", "23", "659.8270045518033", "672", "684.1729954481967"),
        ("2013-Apr-05 15:29:00", "23", "448.23962722602005", "460.1304347826087", "472.02124233919733"),
        ("2013-Apr-05 15:30:00", "23", "659.4023663187861", "674", "688.5976336812139"),
        ("2013-Apr-05 15:32:00", "23", "652.8643631817508", "666.9565217391304", "681.0486802965099"),
        ("2013-Apr-05 15:34:00", "23", "444.689168566475", "456.7391304347826", "468.78909230309023"),
        ("2013-Apr-05 15:35:00", "23", "661.6037178485499", "675.1739130434783", "688.7441082384066"),
        ("2013-Apr-05 15:39:00", "23", "658.0124378440726", "670.1304347826087", "682.2484317211449"),
        ("2013-Apr-05 16:19:00", "23", "449.60814855486547", "465", "480.39185144513453"),
        ("2013-Apr-05 16:20:00", "46", "655.9645219644624", "667.4782608695652", "678.9919997746681"),
        ("2013-Apr-05 16:26:00", "23", "452.24027844816516", "466.2173913043478", "480.19450416053047"),
        ("2013-Apr-05 16:30:00", "23", "660.2572506418051", "671.8695652173913", "683.4818797929775"),
        ("2013-Apr-05 16:31:00", "23", "661.011102554583", "673.4347826086956", "685.8584626628083"),
        ("2013-Apr-05 16:53:00", "46", "457.7534312522435", "565.4347826086956", "673.1161339651477"),
        ("2013-Apr-05 16:55:00", "23", "655.9407699325201", "671.304347826087", "686.6679257196539"),
        ("2013-Apr-05 17:05:00", "46", "412.0344183976609", "561.0217391304348", "710.0090598632087"),
        ("2013-Apr-05 17:06:00", "46", "457.54528946430196", "567.5652173913044", "677.5851453183068"),
        ("2013-Apr-05 17:07:00", "23", "657.6412277100247", "667.5217391304348", "677.4022505508448"),
        ("2013-Apr-05 17:12:00", "23", "598.3432138277318", "617.7391304347826", "637.1350470418334"),
        ("2013-Apr-05 17:23:00", "23", "801.0537973113723", "822.1739130434783", "843.2940287755843")  # <--SPIKE IN DATA
    ]
}

make_test_database(settings)


with DB(settings.database) as db:
    test_alert_threshold(db).test_alert_generated()
    test_alert_threshold(db).test_alert_obsolete()
    