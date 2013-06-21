################################################################################
## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this file,
## You can obtain one at http://mozilla.org/MPL/2.0/.
################################################################################
## Author: Kyle Lahnakoski (kyle@lahnakoski.com)
################################################################################

from math import sqrt
from datazilla.util.basic import nvl
from datazilla.util.debug import D
from datazilla.util.map import Map

DEBUG=True
EPSILON=0.000001

def stats2z_moment(stats):
    # MODIFIED FROM http://statsmodels.sourceforge.net/devel/_modules/statsmodels/stats/moment_helpers.html
    # ADDED count
    # FIXED ERROR IN COEFFICIENTS
    mc0, mc1, mc2, skew, kurt = (stats.count, stats.mean, stats.variance, stats.skew, stats.kurtosis)

    mz0 = mc0
    mz1 = mc1 * mc0
    mz2 = (mc2 + mc1*mc1)*mc0
    mc3 = skew*(mc2**1.5) # 3rd central moment
    mz3 = (mc3 + 3*mc1*mc2 - mc1**3)*mc0  # 3rd non-central moment
    mc4 = (kurt+3.0)*(mc2**2.0) # 4th central moment
    mz4 = (mc4 + 4*mc1*mc3 + 6*mc1*mc1*mc2 + mc1**4) * mc0

    m=Z_moment(stats.count, mz1, mz2, mz3, mz4)
    if DEBUG:
        v = z_moment2stats(m, unbiased=False)
        if not closeEnough(v.count, stats.count): D.error("convertion error")
        if not closeEnough(v.mean, stats.mean): D.error("convertion error")
        if not closeEnough(v.variance, stats.variance):
            D.error("convertion error")

    return m

def closeEnough(a, b):
    if abs(a-b)<=EPSILON*(abs(a)+abs(b)+1): return True
    return False


def z_moment2stats(z_moment, unbiased=True):
    free=0
    if unbiased: free=1
    N=z_moment.S[0]

    if N==0: return Stats()

    return Stats(
        count=N,
        mean=z_moment.S[1]/N,
        variance=(z_moment.S[2]-(z_moment.S[1]**2)/N)/(N-free),
        unbiased=unbiased
    )



class Stats():

    def __init__(self, **args):
        args=Map(**args)
        self.count=nvl(args.count, 0)
        self.mean=nvl(args.mean, 0)
        self.variance=nvl(args.variance, nvl(args.std, 0)**2)
        self.skew=nvl(args.skew, 0)
        self.kurtosis=nvl(args.kurtosis, 0)
        self.unbiased=nvl(args.unbiased, not args.biased, False)     #DEFAULT FOR MAXIMUM VARIANCE



    @property
    def std(self):
        return sqrt(self.variance)




################################################################################
## ZERO-CENTERED MOMENTS
################################################################################
class Z_moment():
    def __init__(self, *args):
        self.S=tuple(args)

    def __add__(self, other):
        return Z_moment(*map(add, self.S, other.S))

    def __sub__(self, other):
        return Z_moment(*map(sub, self.S, other.S))

    @property
    def tuple(self):
        return self.S


    @staticmethod
    def new_instance(values):
        values=[float(v) for v in values]

        return Moments(*[
            len(values),
            sum([n for n in values]),
            sum([pow(n, 2) for n in values]),
            sum([pow(n, 3) for n in values]),
            sum([pow(n, 4) for n in values])
        ])



def add(a,b):
    return nvl(a, 0)+nvl(b,0)

def sub(a,b):
    return nvl(a, 0)-nvl(b,0)