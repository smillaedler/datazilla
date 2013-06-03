from datetime import timedelta, datetime
from itertools import groupby
from model.utils import get_database_connection, error, nvl


##find single points that deviate from the trend
from numpy.lib.scimath import power, sqrt
from scipy.stats.distributions import t
from datazilla.util.bunch import Bunch
from datazilla.util.stats import Moments, stats2moments, Stats, moments2stats



SEVERITY = 0.9
CONFIDENCE_TREASHOLD = 0.05

def exception_point (env):
    assert env.db is not None

    db=env.db

    #LOAD CONFIG

    #CALCULATE HOW FAR BACK TO LOOK
    #BRING IN ALL NEEDED DATA

    test_results=db.query("""
        SELECT
            id,
            test_run_id,
            page_id,
            date_received,
            n_replicates `count`,
            mean
            std
        FROM
            test_data_all_dimensions t
        WHERE
            date_received>unix_timestamp(${begin_time})
        ORDER BY
            test_run_id,
            page_id,
            coalesce(push_date, date_received)
        """,
        {"begin_time":datetime.utcnow()}
    )

    alerts=[]   #PUT ALL THE EXCEPTION ITEM HERE

    for keys, values in Q.groupby(test_results, ("test_run_id", "page_id")):
        total=Moments(0,0,0)          #total ROLLING STATS ACCUMULATION
        count=0
        if len(values)<=1: continue     #CAN DO NOTHING WITH THIS ONE SAMPLE
        for v in values:
            s=Stats(count=v.count, mean=v.mean, std=v.std)
            if count>0:
                #SEE HOW MUCH THE CURRENT STATS DEVIATES FROM total
                p=welchs_ttest(s, moments2stats(total, unbiased=True))
                v["severity"]=SEVERITY,
                v["confidence"]=1-p
                if p<CONFIDENCE_TREASHOLD: alerts.append(v)
            #accumulate v
            m=stats2moments(s)
            v.m=m
            total=total+m
            if count>5: total=total-values[count-5].m  #WINDOW LIMITED TO 5 SAMPLES
            count+=1


    #CHECK IF ALREADY AN ALERT
    current_alerts=db.query("""
        SELECT
            a.id,
            a.status,
            a.last_updated,

        FROM
            alert_email a
        WHERE
            test_series in (${list}) AND
            reason=${}

        """,
        {""}
    )



        #IF SO, UPDATE
        #IF NOT, ADD
    pass





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
