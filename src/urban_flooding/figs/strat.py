"""Stratified rainfall x local-factor analysis on the cell x storm panel.

For each cell and rainfall class we aggregate storms and 'hits' (storms with >=1
street-flooding report in the cell). Probabilities by (rain class, factor group)
come with cluster (cell) bootstrap CIs; the interaction is tested with a binomial
GLM (cluster-robust by cell) of hits ~ rain class * standardized factor + borough.
"""
from functools import lru_cache
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from .common import *  # noqa


@lru_cache(1)
def agg_table():
    pan = panel_df()
    s = storms()[["eid", "rain_class", "max1h_mm"]]
    pan = pan.merge(s, on="eid")
    pan["hit"] = (pan.n_reports > 0).astype(np.int32)
    a = pan.groupby(["cell_id", "rain_class"], observed=True).agg(hits=("hit", "sum"), n=("hit", "size"),
                                                                    reps=("n_reports", "sum")).reset_index()
    st = static()
    g = grid()[["cell_id", "boro", "land_km2", "land_frac"]]
    a = a.merge(st, on="cell_id").merge(g, on="cell_id")
    # Urban street cells only: reports need streets and people, so marsh, park, airport and
    # waterfront cells would otherwise confound hazard with exposure.
    return a[urban_mask(a)].copy()


def urban_mask(d):
    return (d.land_frac >= 0.5) & (d.road_frac >= 0.08) & (d["pop"] >= 200)


def groups(series, q=3, labels=None):
    labels = labels or (["Low", "Mid", "High"] if q == 3 else None)
    return pd.qcut(series.rank(method="first"), q, labels=labels)


def strata(a, grp_col, n_boot=400, seed=0):
    """P(hit) by rain class x group with cell-bootstrap CI, plus High/Low ratio CI."""
    rng = np.random.default_rng(seed)
    d = a.dropna(subset=[grp_col])
    piv_h = d.pivot_table(index="cell_id", columns="rain_class", values="hits", aggfunc="sum", observed=False).fillna(0)
    piv_n = d.pivot_table(index="cell_id", columns="rain_class", values="n", aggfunc="sum", observed=False).fillna(0)
    grp = d.drop_duplicates("cell_id").set_index("cell_id")[grp_col].reindex(piv_h.index)
    levels = [l for l in grp.cat.categories] if hasattr(grp, "cat") else sorted(grp.unique())
    out, boots = [], {}
    for l in levels:
        m = (grp == l).values
        H, N = piv_h.values[m], piv_n.values[m]
        p = H.sum(0) / N.sum(0)
        bs = []
        for _ in range(n_boot):
            i = rng.integers(0, m.sum(), m.sum())
            bs.append(H[i].sum(0) / N[i].sum(0))
        bs = np.array(bs); boots[l] = bs
        for j, c in enumerate(piv_h.columns):
            out.append({"group": l, "rain_class": c, "p": p[j], "lo": np.percentile(bs[:, j], 2.5),
                        "hi": np.percentile(bs[:, j], 97.5), "cells": int(m.sum()), "hits": int(H[:, j].sum())})
    out = pd.DataFrame(out)
    hi_l, lo_l = levels[-1], levels[0]
    ratio = boots[hi_l] / boots[lo_l]
    rat = pd.DataFrame({"rain_class": piv_h.columns, "ratio": (out[out.group == hi_l].p.values / out[out.group == lo_l].p.values),
                        "lo": np.percentile(ratio, 2.5, axis=0), "hi": np.percentile(ratio, 97.5, axis=0)})
    return out, rat


def interaction_test(a, feature, extra="", log=False):
    """Binomial GLM: does the factor's log-odds slope change with rainfall class?"""
    d = a.dropna(subset=[feature]).copy()
    x = np.log1p(d[feature].clip(lower=0)) if log else d[feature]
    d["z"] = (x - x.mean()) / x.std()
    d = d.dropna(subset=["z", "boro"])
    d["prop"] = d.hits / d.n
    d["rc"] = d.rain_class.cat.codes.astype(float)  # 0..4 ordinal
    d["rain_class"] = d.rain_class.astype(str)
    f = f"prop ~ rain_class + z + z:rc + boro{extra}"   # categorical dtypes; avoids name clash with palette C
    m = smf.glm(f, data=d, family=sm.families.Binomial(), var_weights=d.n).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.cell_id)[0]})
    return {"feature": feature, "beta_z": m.params["z"], "p_z": m.pvalues["z"],
            "beta_z_x_class": m.params["z:rc"], "p_interaction": m.pvalues["z:rc"]}


def draw_curves(ax, out, colors, labels=None, ylab=True, log=True):
    xs = np.arange(len(RAIN_LABELS))
    levels = list(dict.fromkeys(out.group))
    for k, l in enumerate(levels):
        d = out[out.group == l]
        off = (k - (len(levels) - 1) / 2) * 0.08
        ax.errorbar(xs + off, d.p * 100, yerr=[(d.p - d.lo) * 100, (d.hi - d.p) * 100], fmt="-o", ms=2.8, lw=1.2,
                    color=colors[k], capsize=0, label=(labels or {}).get(l, str(l)))
    if log:
        from matplotlib.ticker import FuncFormatter, NullFormatter, LogLocator
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(xs); ax.set_xticklabels(RAIN_LABELS)
    ax.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")
    if ylab:
        ax.set_ylabel("P(cell reports | storm), %")


def draw_ratio(ax, rat, color=INK, label="High / Low"):
    xs = np.arange(len(rat))
    ax.errorbar(xs, rat.ratio, yerr=[rat.ratio - rat.lo, rat.hi - rat.ratio], fmt="o", ms=3, color=color, lw=1, capsize=0)
    ax.axhline(1, color=MUTED, lw=0.6)
    ax.set_xticks(xs); ax.set_xticklabels(RAIN_LABELS, fontsize=5.8)
    ax.set_ylabel(label, fontsize=6)
