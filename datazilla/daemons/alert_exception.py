################################################################################
## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this file,
## You can obtain one at http://mozilla.org/MPL/2.0/.
################################################################################
from datetime import timedelta, datetime
from numpy.lib.scimath import power, sqrt
from scipy.stats.distributions import t
from datazilla.daemons.alert import update_h0_rejected
from datazilla.util.basic import nvl
from datazilla.util.cnv import CNV
from datazilla.util.db import SQL
from datazilla.util.map import Map
from datazilla.util.query import Q
from datazilla.util.stats import Z_moment, stats2z_moment, Stats, z_moment2stats



SEVERITY = 0.9
CONFIDENCE_THRESHOLD = 0.05
REASON="exception_point"     #name of the reason in alert_reason
LOOK_BACK=timedelta(weeks=24)

def exception_point (**env):
##find single points that deviate from the trend
    env=Map(**env)
    assert env.db is not None

    db=env.db

    #LOAD CONFIG
    start_time=datetime.utcnow()-LOOK_BACK

    #CALCULATE HOW FAR BACK TO LOOK
    #BRING IN ALL NEEDED DATA

    test_results=db.query("""
        SELECT
            id test_series,
            test_name,
            branch,
            branch_version,
            operating_system_name,
            operating_system_version,   
            page_id,
            test_run_id,
            date_received,
            n_replicates `count`,
            mean,
            std
        FROM
            test_data_all_dimensions t
        WHERE
            test_name="tp5o" AND
            coalesce(push_date, date_received)>unix_timestamp(${begin_time}) AND
            n_replicates IS NOT NULL
        ORDER BY
            test_run_id,
            page_id,
            coalesce(push_date, date_received)
        """,
        {"begin_time":start_time}
    )

    alerts=[]   #PUT ALL THE EXCEPTION ITEM HERE

    for keys, values in Q.groupby(test_results, ["test_name", "branch", "branch_version", "operating_system_name", "page_id"]):
        total=Z_moment()                #total ROLLING STATS ACCUMULATION
        if len(values)<=1: continue     #CAN DO NOTHING WITH THIS ONE SAMPLE
        
        for count, v in enumerate(values):
            s=Stats(count=v.count, mean=v.mean, std=v.std, biased=True)
            if count>0:
                #SEE HOW MUCH THE CURRENT STATS DEVIATES FROM total
                t=z_moment2stats(total, unbiased=True)
                confidence, diff=welchs_ttest(s, t)
                if 1-CONFIDENCE_THRESHOLD < confidence:
                    alerts.append(Map(
                        status="new",
                        create_time=datetime.utcnow(),
                        test_series=v.test_series,
                        reason=REASON,
                        details=CNV.object2JSON({
                            "amount":diff,
                            "confidence":v.confidence
                        }),
                        severity=SEVERITY,
                        confidence=confidence
                    ))
            #accumulate v
            m=stats2z_moment(s)
            v.m=m
            total=total+m
            if count>=5:
                total=total-values[count-5].m  #WINDOW LIMITED TO 5 SAMPLES


    #CHECK THE CURRENT ALERTS
    current_alerts=db.query("""
        SELECT
            a.id,
            a.test_series,
            a.status,
            a.last_updated,
            a.severity,
            a.confidence,
            a.solution
        FROM
            alert_mail a
        WHERE
            coalesce(last_updated, create_time)>unix_timestamp(${begin_time}) AND
            reason=${type} 
        """, {
            "begin_time":start_time,
            "list":[a.test_series for a in alerts],
            "type":REASON
        }
    )

    lookup_alert=dict([(a.test_series, a) for a in alerts])
    lookup_current=dict([(c.test_series, c) for c in current_alerts])


    for a in alerts:
        #CHECK IF ALREADY AN ALERT
        if a.test_series in lookup_current:
            if len(nvl(a.solution, "").trim())==0: continue  # DO NOT TOUCH SOLVED ALERTS

            c=lookup_current[a.test_series]
            if round(a.severity, 5)!=round(c.severity, 5) or round(a.confidence, 5)!=round(c.confidence, 5):
                a.last_updated=datetime.utcnow()
                db.update("alert_mail", {"id":a.id}, a)
        else:
            a.id=SQL("util_newid()")
            a.last_updated=datetime.utcnow()
            db.insert("alert_mail", a)

    #OBSOLETE THE ALERTS THAT ARE NO LONGER VALID
    for c in current_alerts:
        if c.test_series not in lookup_alert:
            c.status="obsolete"
            c.last_updated=datetime.utcnow()
            db.update("alert_mail", {"id":c.id}, c)

    db.execute(
        "UPDATE alert_reasons SET last_run=${run_time} WHERE code=${reason}", {
        "run_time":datetime.utcnow(),
        "reason":REASON
    })

    update_h0_rejected(db, start_time)


def welchs_ttest(stats1, stats2):
    """
    SNAGGED FROM https://github.com/mozilla/datazilla-metrics/blob/master/dzmetrics/ttest.py#L56
    Execute one-sided Welch's t-test given pre-calculated means and stddevs.

    Accepts summary data (N, stddev, and mean) for two datasets and performs
    one-sided Welch's t-test, returning p-value.

    """

    n1=stats1.count
    m1=stats1.mean
    v1=stats1.variance

    n2=stats2.count
    m2=stats2.mean
    v2=stats2.variance


    vpooled        = v1/n1 + v2/n2
    tt             = (m1-m2)/sqrt(vpooled)

    df_numerator   = power(vpooled, 2)
    df_denominator = power(v1/n1, 2)/(n1-1) + power(v2/n2, 2)/(n2-1)
    df             = df_numerator / df_denominator

    t_distribution = t(df)
    return t_distribution.cdf(tt), m1-m2
