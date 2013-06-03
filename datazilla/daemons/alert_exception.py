from datetime import timedelta, datetime
from numpy.lib.scimath import power, sqrt
from scipy.stats.distributions import t
from datazilla.util.bunch import Bunch
from datazilla.util.db import SQL
from datazilla.util.query import Q
from datazilla.util.stats import Moments, stats2moments, Stats, moments2stats



SEVERITY = 0.9
CONFIDENCE_THRESHOLD = 0.05
TYPE_NAME="exception_point"     #name of the reason in alert_reason
LOOK_BACK=timedelta(weeks=4)

def exception_point (env):
##find single points that deviate from the trend

    assert env.db is not None

    db=env.db

    #LOAD CONFIG
    start_time=datetime.utcnow()-LOOK_BACK

    #CALCULATE HOW FAR BACK TO LOOK
    #BRING IN ALL NEEDED DATA

    test_results=db.query("""
        SELECT
            id test_series,
            test_run_id,
            page_id,
            date_received,
            n_replicates `count`,
            mean
            std
        FROM
            test_data_all_dimensions t
        WHERE
            coalesce(push_date, date_received)>unix_timestamp(${begin_time})
        ORDER BY
            test_run_id,
            page_id,
            coalesce(push_date, date_received)
        """,
        {"begin_time":start_time}
    )

    alerts=[]   #PUT ALL THE EXCEPTION ITEM HERE

    for keys, values in Q.groupby(test_results, ("test_run_id", "page_id")):
        total=Moments(0,0,0)          #total ROLLING STATS ACCUMULATION
        count=0
        if len(values)<=1: continue     #CAN DO NOTHING WITH THIS ONE SAMPLE
        for v in values:
            s=Stats(count=v.count, mean=v.mean, std=v.std)
            if count==0:
                v.status="unknown"
            else:
                #SEE HOW MUCH THE CURRENT STATS DEVIATES FROM total
                p=welchs_ttest(s, moments2stats(total, unbiased=True))
                v.severity=SEVERITY,
                v.confidence=1-p
                v.status="known"
                if p<CONFIDENCE_THRESHOLD: alerts.append(v)
            #accumulate v
            m=stats2moments(s)
            v.m=m
            total=total+m
            if count>5: total=total-values[count-5].m  #WINDOW LIMITED TO 5 SAMPLES
            count+=1


    #CHECK THE CURRENT ALERTS
    current_alerts=db.query("""
        SELECT
            a.id,
            a.test_series,
            a.status,
            a.last_updated,
            a.severity,
            a.confidence
        FROM
            alert_mail a
        WHERE
        WHERE
            coalesce(push_date, date_received)>unix_timestamp(${begin_time}) AND
            reason=${type} 
        """, {
            "begin_time":start_time,
            "list":[a.test_series for a in alerts],
            "type":TYPE_NAME
        }
    )

    lookup_alert=dict([(a.test_series, a) for a in alerts])
    lookup_current=dict([(c.test_series, c) for c in current_alerts])


    for a in alerts:
        #CHECK IF ALREADY AN ALERT
        if a.test_series in lookup_current:
            c=lookup_current[a.test_series]
            if round(a.severity, 3)!=round(c.severity, 3) or round(a.confidence, 3)!=round(c.confidence, 3):
                a.last_updated=datetime.utcnow()
                db.update("alert_mail", {"id":a.id}, a)
        else:
            a.id=SQL("util_newid()")
            a.last_updated=datetime.utcnow()
            db.add("alert_mail", a)

    for c in current_alerts:
        if c.test_series not in lookup_alert:
            c.status="obsolete"
            c.last_updated=datetime.utcnow()
            db.update("alert_mail", {"id":c.id}, c)



def welchs_ttest(stats1, stats2):
    """
    SNAGGED FROM https://github.com/mozilla/datazilla-metrics/blob/master/dzmetrics/ttest.py#L56
    Execute one-sided Welch's t-test given pre-calculated means and stddevs.

    Accepts summary data (N, stddev, and mean) for two datasets and performs
    one-sided Welch's t-test, returning p-value.

    """

    n1=stats1.count
    m1=stats1.mean
    s1=stats1.std

    n2=stats2.count
    m2=stats2.mean
    s2=stats2.std




    v1             = power(s1, 2)
    v2             = power(s2, 2)
    vpooled        = v1/n1 + v2/n2
    spooled        = sqrt(vpooled)
    tt             = (m1-m2)/spooled
    df_numerator   = power(vpooled, 2)
    df_denominator = power(v1/n1, 2)/(n1-1) + power(v2/n2, 2)/(n2-1)
    df             = df_numerator / df_denominator

    t_distribution = t(df)
    return 1 - t_distribution.cdf(tt)
