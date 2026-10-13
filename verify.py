"""Independent verification of the engine.

The reference implementations below use exact rational arithmetic (fractions.Fraction) and
textbook closed forms (annuity / loan formulas). They are deliberately written in a different
style from engine.py, so agreement is meaningful evidence of accuracy."""
import random
from fractions import Fraction as Fr

import engine as E


def fr(x):
    return Fr(x).limit_denominator(10 ** 9) if isinstance(x, float) else Fr(x)


def close(a, b, rel=1e-6, ab=1.0):
    a, b = float(a), float(b)
    return abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))


def ref_simulate(p, inc, exp, ret, extra=0, debt_pay=None, save_cap=None, years=None):
    """Exact-arithmetic reference of the documented waterfall."""
    years = years or p["years"]
    r, rd = fr(max(ret, -0.9)) / 12, fr(p["debt_rate"]) / 1200
    sched = fr(p["debt_payment"] if debt_pay is None else debt_pay)
    em_t = fr(E.LIQ_MONTHS[p["liquidity"]] * p["expenses"])
    st = {"cash": fr(p["assets"]), "pool": fr(p["investments"]), "debt": fr(p["debt"])}
    inc, exp, extra = fr(inc), fr(exp), fr(extra)
    cap = None if save_cap is None else fr(save_cap)
    for _ in range(years * 12):
        pay = min(sched, st["debt"] + st["debt"] * rd)
        st["debt"] = st["debt"] + st["debt"] * rd - pay
        if st["debt"] < Fr(1, 2):
            st["debt"] = Fr(0)
        flow = inc - exp - extra - pay
        if st["pool"] > 0:
            st["pool"] *= 1 + r
        if flow >= 0:
            s = flow if cap is None else min(flow, cap)
            top = min(s, max(em_t - st["cash"], Fr(0)))
            st["cash"] += top
            s -= top
            ex = min(s / 2, st["debt"]) if st["debt"] > 0 else Fr(0)
            st["debt"] -= ex
            st["pool"] += s - ex
        else:
            st["cash"] += flow
            if st["cash"] < 0:
                st["pool"] += st["cash"]
                st["cash"] = Fr(0)
    return st


def ref_payment(pv, rate_m, n):
    pv, rate_m = fr(pv), fr(rate_m)
    return pv / n if rate_m == 0 else pv * rate_m / (1 - (1 + rate_m) ** (-n))


def rand_profile(rng, with_debt=None):
    inc = rng.randint(6, 90) * 1_000_000
    has_debt = rng.random() < 0.6 if with_debt is None else with_debt
    debt = rng.randint(10, 600) * 1_000_000 if has_debt else 0
    return {"income": inc, "expenses": inc * rng.uniform(0.25, 0.85), "investments": rng.randint(0, 300) * 1e6,
            "assets": rng.randint(0, 500) * 1e6, "debt": debt,
            "debt_payment": min(debt, inc * rng.uniform(0.02, 0.3)) if has_debt else 0,
            "debt_rate": rng.choice([0, 6, 9.5, 12]) if has_debt else 0,
            "years": rng.randint(2, 30), "liquidity": rng.choice(E.LEVELS), "risk": rng.choice(E.LEVELS)}


def run_checks(seed=7, n=25):
    """Return (correct, total, failures)."""
    rng = random.Random(seed)
    good = total = 0
    fails = []

    def check(ok, label):
        nonlocal good, total
        total += 1
        good += bool(ok)
        if not ok:
            fails.append(label)

    for i in range(n):
        p = E.clean_profile(rand_profile(rng))
        m = E.metrics(p)
        tag = f"profile {i}"
        # 1 metrics identities
        check(close(m["net_cash_flow"], p["income"] - p["expenses"] - p["debt_payment"]), f"{tag}: net cash flow")
        check(close(m["net_worth"], p["assets"] + p["investments"] - p["debt"]), f"{tag}: net worth")
        check(m["dti"] is None or close(m["dti"], p["debt_payment"] / p["income"], 1e-12, 1e-12), f"{tag}: DTI")
        # 2 every scenario vs exact-arithmetic reference
        for sc in E.SCENARIOS:
            s = E.simulate(p, sc)
            ret = E.BASE_RETURN[p["risk"]] + sc["ret"]
            ref = ref_simulate(p, p["income"] * (1 + sc["income"]), p["expenses"] * (1 + sc["expense"]), ret)
            nw = ref["cash"] + ref["pool"] - ref["debt"]
            check(close(s["net_worth_by_year"][p["years"]], nw, 1e-7, 2.0), f"{tag}/{sc['key']}: net worth at horizon")
            check(close(s["debt_by_year"][p["years"]], ref["debt"], 1e-7, 2.0), f"{tag}/{sc['key']}: debt at horizon")
        # 3 closed form (no debt, reserve already funded, positive surplus)
        if p["debt"] == 0 and p["assets"] >= E.LIQ_MONTHS[p["liquidity"]] * p["expenses"] and m["net_cash_flow"] > 0:
            r = E.BASE_RETURN[p["risk"]] / 12
            g, f = E._factor(r, p["years"] * 12)
            exp_nw = p["assets"] + p["investments"] * g + m["net_cash_flow"] * f
            nw = E.simulate(p, E.SCENARIOS[2])["net_worth_by_year"][p["years"]]
            check(close(nw, exp_nw, 1e-9, 1.0), f"{tag}: closed-form net worth")
        # 4 loan formulas
        if p["debt"] > 0:
            rd = p["debt_rate"] / 1200
            n_m = p["years"] * 12
            pay = E.pmt(p["debt"], rd, n_m)
            check(close(pay, ref_payment(p["debt"], rd, n_m), 1e-9, 0.01), f"{tag}: PMT")
            bal = fr(p["debt"])
            for _ in range(n_m):
                bal = bal * (1 + fr(rd)) - fr(pay)
            check(abs(float(bal)) < 1.0, f"{tag}: loan amortises to zero")
            k = E.nper(p["debt"], rd, pay)
            check(k is not None and abs(k - n_m) <= 1, f"{tag}: NPER round trip")
        # 5 goal plans: required saving reaches the target exactly; completion/time are consistent
        for kind_goal in E.default_goals(p):
            pl = E.goal_plan(kind_goal["name"], kind_goal["target"], kind_goal["current"], kind_goal["years"],
                             m["savings_capacity"], E.BASE_RETURN[p["risk"]], kind_goal["kind"], p["debt_rate"], p["debt_payment"])
            if pl["kind"] == "savings" and pl["extra_needed"] > 0:
                n_m = int(round(kind_goal["years"] * 12))
                r = E.BASE_RETURN[p["risk"]] / 12
                g, f = E._factor(r, n_m)
                reached = kind_goal["current"] * g + pl["required_monthly"] * f
                check(close(reached, max(kind_goal["target"], kind_goal["current"] * g), 1e-9, 1.0), f"{tag}/{kind_goal['name']}: required saving hits target")
                check((pl["completion"] >= 1 - 1e-12) == pl["on_track"] or pl["required_monthly"] == 0, f"{tag}/{kind_goal['name']}: completion vs on_track")
                last = pl["milestones"][-1]["balance"]
                check(close(last, max(kind_goal["target"], kind_goal["current"] * g), 1e-9, 1.0), f"{tag}/{kind_goal['name']}: final milestone equals target")
            if pl["months_at_rate"] is not None and pl["kind"] == "savings":
                ok = (pl["months_at_rate"] <= round(kind_goal["years"] * 12)) == (pl["completion"] >= 1 - 1e-12)
                check(ok, f"{tag}/{kind_goal['name']}: months-to-goal consistent with completion")
        # 6 no double counting of existing funds / capacity
        dg = E.default_goals(p)
        check(sum(g["current"] for g in dg) <= p["assets"] + p["investments"] + 1, f"{tag}: existing funds not double counted")
        res = E.goals_analyze(p, None)
        al = res["allocation"]
        check(al["total_allocated"] <= al["capacity"] + 1e-6 and all(r["allocated"] <= r["required"] + 1e-6 for r in al["rows"]),
              f"{tag}: allocation never exceeds capacity or requirement")
        # 7 what-if with no change equals the baseline
        w = E.whatif(p, {})
        check(all(r["variance"] in (None, 0) or abs(r["variance"]) < 1e-6 for r in w["rows"] if r["label"].startswith(("Net worth", "Remaining debt", "Net monthly"))),
              f"{tag}: zero what-if equals baseline")
        # 8 monotonic: more income never reduces final net worth
        w2 = E.whatif(p, {"income": {"sign": "+", "pct": 20}})
        check(w2["rows"][10]["adjusted"] >= w2["rows"][10]["baseline"] - 1.0, f"{tag}: income increase monotonic")
    return good, total, fails
