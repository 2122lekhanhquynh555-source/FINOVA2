"""FINOVA deterministic calculation engine.

Every financial figure shown by the platform is produced here. The LLM layer only
parses language and explains these outputs; it never calculates them.

Modelling rules (all disclosed in the UI):
  * Cash (the "Assets" field) funds the Emergency Fund goal only.
  * Investments (plus cash above the emergency target) fund the Wealth goal only.
  * Debt is a separate liability amortised with the declared payment and optional interest.
  * Monthly surplus follows a waterfall: emergency cash -> 50% extra debt paydown while debt
    remains -> investments. Each VND of surplus is therefore used exactly once.
"""
import io
import math
import re
import time

BASE_RETURN = {"low": 0.03, "medium": 0.06, "high": 0.09}   # simulated annual yield assumptions
LIQ_MONTHS = {"low": 3, "medium": 6, "high": 9}             # emergency-fund target (months of expenses)
LEVELS = ("low", "medium", "high")
MAX_MONTHS = 600
WEALTH_MONTHS = 36
DEBT_SURPLUS_SHARE = 0.5
MAX_VALUE = 1e13
MONEY_KEYS = ("income", "expenses", "investments", "assets", "debt", "debt_payment")


# ----------------------------------------------------------------- formatting
def vnd(x):
    return f"{x:,.0f} VND"


def pc(x, d=1):
    return "n/a" if x is None else f"{x * 100:.{d}f}%"


def dur(m):
    if m is None:
        return "not reached within 50 years"
    y, mo = divmod(int(round(m)), 12)
    if y and mo:
        return f"{y} yr {mo} mo"
    if y:
        return f"{y} yr"
    return f"{mo} mo" if mo else "already achieved"


# ------------------------------------------------------------------- profile
def _num(v):
    try:
        if isinstance(v, bool):
            return 0.0
        v = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        v = 0.0
    return v if math.isfinite(v) else 0.0


def _pos(v):
    return min(max(_num(v), 0.0), MAX_VALUE)


def clean_profile(d):
    d = d or {}
    p = {k: _pos(d.get(k)) for k in MONEY_KEYS}
    p["debt_rate"] = min(max(_num(d.get("debt_rate")), 0.0), 100.0)      # % per year
    p["years"] = int(min(max(_num(d.get("years", 10)) or 10, 1), 30))
    for k in ("liquidity", "risk"):
        v = str(d.get(k, "medium")).lower()
        p[k] = v if v in LEVELS else "medium"
    return p


def validate_profile(d):
    """Python-side validation used by every input path (form, text parsing, Excel)."""
    raw = d or {}
    p = clean_profile(raw)
    issues = []

    def add(level, field, msg):
        issues.append({"level": level, "field": field, "msg": msg})

    for k in MONEY_KEYS:
        if k in raw and _num(raw[k]) < 0:
            add("warning", k, f"{k.replace('_', ' ')} was negative and has been set to 0.")
        if k in raw and _num(raw[k]) > MAX_VALUE:
            add("error", k, f"{k.replace('_', ' ')} is unrealistically large.")
    if not p["income"]:
        add("error", "income", "Monthly income is missing or 0; ratios and projections cannot be computed.")
    if not p["expenses"]:
        add("warning", "expenses", "Monthly expenses are 0 - please confirm this is correct.")
    if p["debt"] > 0 and not p["debt_payment"]:
        add("warning", "debt_payment", "You have debt but no monthly payment; the debt would never be repaid.")
    if p["debt"] == 0 and p["debt_payment"] > 0:
        add("warning", "debt", "A monthly debt payment was entered but total debt is 0 (conflicting data).")
    if p["income"] and p["debt_payment"] > p["income"]:
        add("error", "debt_payment", "Monthly debt payment is larger than monthly income.")
    elif p["income"] and p["expenses"] + p["debt_payment"] > p["income"]:
        add("warning", "income", "Expenses plus debt payments exceed income, so cash flow is negative.")
    if p["debt"] > 0 and p["debt_payment"] > 0 and p["debt_payment"] <= p["debt"] * p["debt_rate"] / 1200:
        add("warning", "debt_payment", "The monthly payment does not cover the monthly interest; the debt will not shrink.")
    for k in ("years", "liquidity", "risk"):
        if k not in raw:
            add("info", k, f"{k} was not provided; the default ({p[k]}) is used.")
    return issues


def metrics(p):
    inc, exp = p["income"], p["expenses"]
    net = inc - exp - p["debt_payment"]
    total_assets = p["assets"] + p["investments"]
    return {
        "income": inc, "expenses": exp, "debt_payment": p["debt_payment"],
        "net_cash_flow": net,
        "expense_ratio": exp / inc if inc else None,
        "dti": p["debt_payment"] / inc if inc else None,
        "savings_capacity": max(net, 0),
        "savings_rate": max(net, 0) / inc if inc else 0,
        "total_assets": total_assets,
        "liabilities": p["debt"],
        "net_worth": total_assets - p["debt"],
        "emergency_months": p["assets"] / exp if exp else None,
        "target_months": LIQ_MONTHS[p["liquidity"]],
    }


def health(p, m):
    inc = m["income"]
    items = []
    if inc <= 0:
        cf = ("bad", "No income", "No income was entered, so ongoing living expenses and debt service cannot be covered.")
    elif m["net_cash_flow"] >= 0.10 * inc:
        cf = ("good", "Positive", f"Income covers living expenses and debt service with {vnd(m['net_cash_flow'])} left each month ({pc(m['net_cash_flow'] / inc)} of income).")
    elif m["net_cash_flow"] >= 0:
        cf = ("warn", "Balanced (thin margin)", f"Income only just covers expenses and debt service; the monthly margin is {vnd(m['net_cash_flow'])}.")
    else:
        cf = ("bad", "Negative", f"Expenses plus debt service exceed income by {vnd(-m['net_cash_flow'])} per month.")
    items.append(("Cash Flow Analysis",) + cf)
    d = m["dti"]
    if not p["debt_payment"]:
        db = ("good", "No debt service", "No monthly debt payments were entered.")
    elif d is None:
        db = ("bad", "Unmeasurable", "Debt payments exist but no income was entered.")
    elif d < 0.20:
        db = ("good", "Low", f"Debt payments take {pc(d)} of income, below the commonly used 20% comfort level.")
    elif d < 0.36:
        db = ("warn", "Moderate", f"Debt payments take {pc(d)} of income, inside the 20%-36% watch zone.")
    elif d < 0.50:
        db = ("bad", "High", f"Debt payments take {pc(d)} of income, above the 36% guideline.")
    else:
        db = ("bad", "Severe", f"Debt payments take {pc(d)} of income, which leaves very little room for other needs.")
    items.append(("Debt Burden",) + db)
    em, tm = m["emergency_months"], m["target_months"]
    if em is None:
        lq = ("warn", "Unmeasurable", "No living expenses were entered, so reserve coverage cannot be measured.")
    elif em >= tm:
        lq = ("good", "Strong", f"Assets cover {em:.1f} months of expenses, meeting your {tm}-month target.")
    elif em >= tm / 2:
        lq = ("warn", "Partial", f"Assets cover {em:.1f} months of expenses against a {tm}-month target.")
    else:
        lq = ("bad", "Thin", f"Assets cover only {em:.1f} months of expenses against a {tm}-month target.")
    items.append(("Liquidity",) + lq)
    sr = m["savings_rate"]
    if sr >= 0.20:
        sv = ("good", "Strong", f"You can set aside about {pc(sr)} of income ({vnd(m['savings_capacity'])} per month).")
    elif sr >= 0.10:
        sv = ("good", "Healthy", f"You can set aside about {pc(sr)} of income ({vnd(m['savings_capacity'])} per month).")
    elif sr >= 0.05:
        sv = ("warn", "Modest", f"Savings capacity is {pc(sr)} of income ({vnd(m['savings_capacity'])} per month).")
    else:
        sv = ("bad", "Low", f"Savings capacity is only {pc(sr)} of income ({vnd(m['savings_capacity'])} per month).")
    items.append(("Savings Capacity",) + sv)

    strengths, weak, actions = [], [], []
    for name, lvl, status, txt in items:
        (strengths if lvl == "good" else weak if lvl == "bad" else []).append(f"{name}: {status}")
    if m["net_cash_flow"] < 0:
        actions.append("Close the monthly cash-flow gap first (reduce expenses, raise income, or restructure debt).")
    if d is not None and d >= 0.36:
        actions.append("Lower the debt burden: prioritise high-cost debt and avoid new borrowing.")
    if em is not None and em < tm:
        actions.append(f"Build the emergency reserve toward {tm} months of expenses ({vnd(tm * m['expenses'])}).")
    if sr < 0.10 and m["net_cash_flow"] >= 0:
        actions.append("Raise the savings rate toward 10%-20% of income.")
    if not actions:
        actions.append("Maintain current habits and move on to selecting savings or investment goals.")
    return {"items": [{"pillar": a, "level": b, "status": c, "text": t} for a, b, c, t in items],
            "strengths": strengths, "vulnerabilities": weak, "actions": actions}


# --------------------------------------------------------------- simulation
def _run(p, inc, exp, ret, extra=0.0, debt_pay=None, save_cap=None, months=MAX_MONTHS):
    """Month-by-month waterfall simulation (see module docstring).

    inc/exp: monthly income and living expenses; ret: annual yield on investments;
    extra: unforeseen monthly expense; debt_pay: scheduled payment override;
    save_cap: optional monthly cap on money saved (the rest is spent)."""
    r = max(ret, -0.9) / 12
    rd = p["debt_rate"] / 1200
    sched = p["debt_payment"] if debt_pay is None else debt_pay
    em_t = LIQ_MONTHS[p["liquidity"]] * p["expenses"]
    wt = WEALTH_MONTHS * p["expenses"]
    cash, pool, debt = p["assets"], p["investments"], p["debt"]
    reach = {"g1": None, "g2": None, "g3": None}
    short = 0

    def chk(m):
        if reach["g1"] is None and cash >= em_t - 1e-9:
            reach["g1"] = m
        if reach["g2"] is None and debt <= 0.5:
            reach["g2"] = m
        if reach["g3"] is None and pool >= wt - 1e-9:
            reach["g3"] = m

    ys = {"assets": [cash + pool], "nw": [cash + pool - debt], "pool": [pool], "cash": [cash], "debt": [debt]}
    cf0 = None
    chk(0)
    for m in range(1, months + 1):
        interest = debt * rd
        pay = min(sched, debt + interest)
        debt = debt + interest - pay
        if debt < 0.5:
            debt = 0.0
        cf = inc - exp - extra - pay
        if cf0 is None:
            cf0 = cf
        if pool > 0:
            pool *= 1 + r
        if cf >= 0:
            s = cf if save_cap is None else min(cf, save_cap)
            if cash < em_t:
                add = min(s, em_t - cash)
                cash += add
                s -= add
            if debt > 0 and s > 0:
                x = min(s * DEBT_SURPLUS_SHARE, debt)
                debt -= x
                s -= x
            pool += s
        else:
            cash += cf
            if cash < 0:
                pool += cash
                cash = 0.0
        if pool < 0:
            short += 1
        chk(m)
        if m % 12 == 0:
            ys["assets"].append(cash + pool)
            ys["nw"].append(cash + pool - debt)
            ys["pool"].append(pool)
            ys["cash"].append(cash)
            ys["debt"].append(debt)
    return {"cf0": cf0, "reach": reach, "shortfall_months": short, **ys}


def simulate(p, sc):
    ret = BASE_RETURN[p["risk"]] + sc["ret"]
    inc = p["income"] * (1 + sc["income"])
    exp = p["expenses"] * (1 + sc["expense"])
    run = _run(p, inc, exp, ret)
    return {"key": sc["key"], "name": sc["name"], "short": sc["short"], "desc": sc["desc"],
            "assumptions": {"income_change": sc["income"], "expense_change": sc["expense"], "annual_return": max(ret, -0.9)},
            "monthly_income": inc, "monthly_expenses": exp, "net_cash_flow": run["cf0"],
            "savings_capacity": max(run["cf0"], 0), "assets_by_year": run["assets"], "net_worth_by_year": run["nw"],
            "pool_by_year": run["pool"], "debt_by_year": run["debt"], "reach": run["reach"],
            "shortfall_months": run["shortfall_months"]}


SCENARIOS = [
    {"key": "severe", "name": "Severely Conservative Scenario", "short": "Severely Conservative",
     "income": -0.25, "expense": 0.15, "ret": -0.04,
     "desc": "Sharp income drop (-25%), major expense surge (+15%) and investment yield 4 points below the base assumption."},
    {"key": "conservative", "name": "Conservative Scenario", "short": "Conservative",
     "income": -0.10, "expense": 0.05, "ret": -0.02,
     "desc": "Mild income decline (-10%), slight expense increase (+5%) and yield 2 points lower."},
    {"key": "baseline", "name": "Baseline Scenario", "short": "Baseline",
     "income": 0.0, "expense": 0.0, "ret": 0.0,
     "desc": "Your own income, expenses and debt payments with the base yield for your risk level."},
    {"key": "optimistic", "name": "Optimistic Scenario", "short": "Optimistic",
     "income": 0.10, "expense": 0.0, "ret": 0.01,
     "desc": "Income 10% higher than baseline, other declared assumptions unchanged, yield 1 point higher."},
    {"key": "high", "name": "Highly Optimistic Scenario", "short": "Highly Optimistic",
     "income": 0.25, "expense": 0.0, "ret": 0.02,
     "desc": "Significant growth: income +25% and yield 2 points higher, expenses unchanged."},
]
BASE_SCORE = {"severe": 40, "conservative": 85, "baseline": 95, "optimistic": 78, "high": 55}
RISK_ADJ = {"low": {"severe": 5, "conservative": 5, "baseline": 0, "optimistic": -6, "high": -10},
            "medium": {"severe": 0, "conservative": 0, "baseline": 0, "optimistic": 0, "high": 0},
            "high": {"severe": -5, "conservative": -5, "baseline": 0, "optimistic": 4, "high": 8}}


def _label(rank, score):
    if rank == 1:
        return "Most Suitable"
    return "Suitable" if score >= 80 else "Moderately Suitable" if score >= 60 else \
        "Use with Caution" if score >= 45 else "Risk Contingency"


def goal_targets(p):
    return {"g1": LIQ_MONTHS[p["liquidity"]] * p["expenses"], "g2": p["debt"], "g3": WEALTH_MONTHS * p["expenses"]}


def analysis(profile):
    p = clean_profile(profile)
    m = metrics(p)
    sims = [simulate(p, sc) for sc in SCENARIOS]
    base = next(s for s in sims if s["key"] == "baseline")
    n = p["years"]
    tg = goal_targets(p)
    for s in sims:
        sc = BASE_SCORE[s["key"]] + RISK_ADJ[p["risk"]][s["key"]]
        if m["net_cash_flow"] < 0:
            sc += {"baseline": -20, "optimistic": -15, "high": -20, "conservative": 3, "severe": 10}[s["key"]]
        if m["savings_rate"] >= 0.20:
            sc += {"optimistic": 4, "high": 3}.get(s["key"], 0)
        s["score"] = int(max(0, min(100, sc)))
        s["final_net_worth"] = s["net_worth_by_year"][n]
        s["final_assets"] = s["assets_by_year"][n]
        s["final_pool"] = s["pool_by_year"][n]
        s["goal_delay"] = {}
        for g in ("g1", "g2", "g3"):
            a, b = s["reach"][g], base["reach"][g]
            s["goal_delay"][g] = None if a is None or b is None else a - b
        s["wealth_gap"] = s["final_pool"] - tg["g3"]
    ranked = sorted(sims, key=lambda s: -s["score"])
    for i, s in enumerate(ranked, 1):
        s["rank"] = i
        s["status"] = _label(i, s["score"])
        s["title"] = f"{i}. {s['name']} ({s['status']} — {s['score']}%)"
    return {"profile": p, "metrics": m, "health": health(p, m), "scenarios": sims,
            "ranking": [s["key"] for s in ranked], "goals": default_goals(p), "goal_targets": tg,
            "years": list(range(0, n + 1)),
            "assumption_notes": [
                "Monthly surplus follows a waterfall: (1) refill the cash emergency reserve, (2) 50% to extra debt repayment while debt remains, (3) the rest is invested at the scenario's simulated annual yield. Each VND is used once.",
                "Cash (Assets) is the emergency reserve; investments are the invested pool. They are never counted for two goals.",
                f"Debt is amortised monthly with the declared payment and the interest rate you entered ({p['debt_rate']:.1f}% per year; 0% if left blank).",
                "Deficits are drawn from cash first, then from the investment pool.",
                f"Base annual yield by risk level: low {pc(BASE_RETURN['low'], 0)}, medium {pc(BASE_RETURN['medium'], 0)}, high {pc(BASE_RETURN['high'], 0)}; simulated assumptions, not guarantees.",
                f"Reference goals: Emergency Fund (cash = {LIQ_MONTHS[p['liquidity']]} months of expenses), Debt Freedom, Wealth Milestone (investment pool = {WEALTH_MONTHS} months of expenses)."]}


# ------------------------------------------------------------------ what-if
def _adj(adj, key):
    a = (adj or {}).get(key) or {}
    s = -1 if str(a.get("sign", "+")) in ("-", "−", "-1", "minus") else 1
    return max(s * min(max(_num(a.get("pct")), 0), 1000) / 100, -1.0)


def whatif(profile, adj):
    p = clean_profile(profile)
    m = metrics(p)
    n = p["years"]
    fi, fe, fu, fs, fd = (_adj(adj, k) for k in ("income", "expense", "unforeseen", "savings", "debt"))
    inc2 = p["income"] * (1 + fi)
    exp2 = p["expenses"] * (1 + fe)
    unf2 = max(fu, 0) * p["expenses"]            # '+' = emergency shock; '-' = no emergency spending
    debt2 = p["debt_payment"] * (1 + fd)
    net2 = inc2 - exp2 - unf2 - debt2
    planned = m["savings_capacity"] * (1 + fs)
    cap = None if fs == 0 else max(planned, 0)
    ret = BASE_RETURN[p["risk"]]
    b, a = _run(p, p["income"], p["expenses"], ret), _run(p, inc2, exp2, ret, extra=unf2, debt_pay=debt2, save_cap=cap)
    tm = m["target_months"]
    rows = [
        ("Monthly income", p["income"], inc2, "VND"),
        ("Living expenses", p["expenses"], exp2, "VND"),
        ("Unforeseen expenses", 0, unf2, "VND"),
        ("Monthly debt service", p["debt_payment"], debt2, "VND"),
        ("Net monthly cash flow", m["net_cash_flow"], net2, "VND"),
        ("Savings capacity", m["savings_capacity"], max(net2, 0), "VND"),
        ("Planned savings (after savings-rate change)", m["savings_capacity"], planned, "VND"),
        ("Savings feasibility gap (capacity - plan)", 0, max(net2, 0) - planned, "VND"),
        ("Liquidity surplus / (deficit) vs target reserve", p["assets"] - tm * p["expenses"], p["assets"] - tm * (exp2 + unf2), "VND"),
        ("Reserve coverage (months)", m["emergency_months"] or 0, p["assets"] / (exp2 + unf2) if exp2 + unf2 else 0, "months"),
        (f"Net worth after {n} years", b["nw"][n], a["nw"][n], "VND"),
        (f"Investment pool after {n} years", b["pool"][n], a["pool"][n], "VND"),
        (f"Remaining debt after {n} years", b["debt"][n], a["debt"][n], "VND"),
        ("Emergency Fund reached", b["reach"]["g1"], a["reach"]["g1"], "dur"),
        ("Debt Freedom reached", b["reach"]["g2"], a["reach"]["g2"], "dur"),
        ("Wealth Milestone reached", b["reach"]["g3"], a["reach"]["g3"], "dur"),
    ]
    out = []
    for lab, x, y, u in rows:
        out.append({"label": lab, "baseline": x, "adjusted": y, "unit": u,
                    "variance": (None if x is None or y is None else y - x)})
    warns = []
    if net2 < 0:
        warns.append("Net cash flow is negative after the adjustments: savings and assets would be drawn down.")
    if a["shortfall_months"]:
        warns.append(f"The investment pool would be depleted for {a['shortfall_months']} months (funding shortfall).")
    return {"adjustments": {"income": fi, "expense": fe, "unforeseen": fu, "savings": fs, "debt": fd},
            "rows": out,
            "chart": {"labels": ["Net cash flow", "Savings capacity", "Planned savings"],
                      "baseline": [m["net_cash_flow"], m["savings_capacity"], m["savings_capacity"]],
                      "adjusted": [net2, max(net2, 0), planned]},
            "series": {"labels": list(range(0, n + 1)), "baseline": b["nw"][:n + 1], "adjusted": a["nw"][:n + 1]},
            "net": net2, "base_net": m["net_cash_flow"], "liquidity": p["assets"] - tm * (exp2 + unf2),
            "planned": planned, "warnings": warns}


# -------------------------------------------------------------------- goals
def _factor(r, n):
    g = (1 + r) ** n
    return g, (n if r == 0 else (g - 1) / r)


def pmt(pv, r, n):
    """Level payment that amortises pv over n periods at periodic rate r."""
    if pv <= 0:
        return 0.0
    return pv / n if r == 0 else pv * r / (1 - (1 + r) ** -n)


def nper(pv, r, pay):
    """Months to repay pv with payment pay at periodic rate r (None if never)."""
    if pv <= 0.5:
        return 0
    if pay <= 0:
        return None
    if r == 0:
        return math.ceil(pv / pay - 1e-9)
    if pay <= pv * r:
        return None
    return math.ceil(-math.log(1 - pv * r / pay) / math.log(1 + r) - 1e-9)


def goal_plan(name, target, current, years, monthly_save, annual_ret, kind="savings", debt_rate=0.0, sched_payment=0.0):
    if kind == "debt":
        return _debt_plan(name, target, current, years, monthly_save, debt_rate, sched_payment)
    n = max(int(round(years * 12)), 1)
    r = annual_ret / 12
    g, fvf = _factor(r, n)
    projected = current * g + monthly_save * fvf
    need = max(target - current * g, 0)
    req = need / fvf if fvf > 0 else 0.0
    months_at = 0 if current >= target else None
    bal = current
    if months_at is None:
        for k in range(1, 1201):
            bal = bal * (1 + r) + monthly_save
            if bal >= target - 1e-9:
                months_at = k
                break
    completion = 1.0 if target <= 0 else min(projected / target, 1.0)
    series, rseries, b1, b2 = [current], [current], current, current
    for k in range(1, n + 1):
        b1 = b1 * (1 + r) + monthly_save
        b2 = b2 * (1 + r) + req
        if k % 12 == 0:
            series.append(b1)
            rseries.append(b2)
    miles = []
    for q in (0.25, 0.5, 0.75, 1.0):
        k = max(int(round(n * q)), 1)
        gk, fk = _factor(r, k)
        miles.append({"pct": q, "month": k, "balance": current * gk + req * fk, "projected": current * gk + monthly_save * fk})
    return {"kind": "savings", "name": name, "target": target, "current": current, "years": years, "monthly_save": monthly_save,
            "annual_return": annual_ret, "extra_needed": max(target - current, 0), "required_monthly": req,
            "months_at_rate": months_at, "gap": monthly_save - req, "projected": projected, "completion": completion,
            "shortfall": max(target - projected, 0), "surplus": max(projected - target, 0),
            "on_track": monthly_save >= req - 0.5,
            "options": {"extend_years": None if months_at is None else math.ceil(months_at / 12),
                        "reduced_target": min(projected, target), "required_monthly": req},
            "milestones": miles, "series": series, "required_series": rseries}


def _debt_plan(name, target, current, years, extra, debt_rate, sched):
    """Debt goal: `extra` is the additional monthly money (savings capacity) applied on top of the
    scheduled payment. `current` is money already set aside against the principal."""
    D = max(target - current, 0.0)
    rd = debt_rate / 1200
    n = max(int(round(years * 12)), 1)
    req_total = pmt(D, rd, n)
    req_extra = max(req_total - sched, 0.0)
    pay = sched + extra
    bal = D
    months_at = 0 if D <= 0.5 else None
    rem_n = 0.0 if D <= 0.5 else None
    series = [target - D]
    for k in range(1, 1201):
        if bal > 0:
            bal = bal * (1 + rd) - pay
            if bal <= 0.5:
                bal = 0.0
                if months_at is None:
                    months_at = k
        if k == n:
            rem_n = bal
        if k % 12 == 0 and k <= n:
            series.append(target - bal)
        if k >= n and (months_at is not None or pay <= bal * rd):
            break
    if rem_n is None:
        rem_n = bal
    projected = target - rem_n
    miles = []
    for q in (0.25, 0.5, 0.75, 1.0):
        kk = max(int(round(n * q)), 1)
        g_, f_ = _factor(rd, kk)
        b_ = max(D * g_ - req_total * f_, 0.0)
        miles.append({"pct": q, "month": kk, "balance": target - b_, "projected": None})
    completion = 1.0 if target <= 0 else min(projected / target, 1.0)
    return {"kind": "debt", "name": name, "target": target, "current": current, "years": years, "monthly_save": extra,
            "annual_return": 0.0, "debt_rate": debt_rate, "scheduled_payment": sched, "extra_needed": D,
            "required_monthly": req_extra, "required_total_payment": req_total, "months_at_rate": months_at,
            "gap": extra - req_extra, "projected": projected, "completion": completion,
            "shortfall": max(target - projected, 0), "surplus": 0.0, "on_track": extra >= req_extra - 0.5,
            "negative_amortization": pay + 1e-9 < D * rd,
            "options": {"extend_years": None if months_at is None else math.ceil(months_at / 12),
                        "reduced_target": min(projected, target), "required_monthly": req_extra},
            "milestones": miles, "series": series, "required_series": []}


PRIORITY = {"high": 100, "medium": 70, "low": 40}


def default_goals(p):
    m = metrics(p)
    tm = LIQ_MONTHS[p["liquidity"]]
    em = tm * p["expenses"]
    em_cur = min(p["assets"], em)
    spare = p["assets"] - em_cur
    g = [{"name": "Emergency Fund", "kind": "savings", "target": round(em), "current": int(math.floor(em_cur)),
          "years": 2, "priority": "High", "constraints": f"Cover {tm} months of living expenses (cash)"}]
    if p["debt"] > 0:
        mo = nper(p["debt"], p["debt_rate"] / 1200, p["debt_payment"])
        yrs = min(max(math.ceil(mo / 12), 1), 30) if mo else 5
        g.append({"name": "Debt Freedom", "kind": "debt", "target": round(p["debt"]), "current": 0, "years": yrs,
                  "priority": "Medium", "constraints": "Clear all current liabilities"})
    else:
        g.append({"name": "Home / Education Fund", "kind": "savings", "target": round(12 * p["income"]), "current": 0,
                  "years": max(p["years"] // 2, 3), "priority": "Medium", "constraints": "New savings equal to 12 months of income"})
    g.append({"name": "Wealth Milestone", "kind": "savings", "target": round(WEALTH_MONTHS * p["expenses"]),
              "current": int(math.floor(p["investments"] + spare)), "years": p["years"], "priority": "Medium",
              "constraints": f"Invested funds equal to {WEALTH_MONTHS} months of expenses"})
    return g


def clean_goals(goals, keep_blank=False):
    out = []
    for g in (goals or [])[:6]:
        if not isinstance(g, dict):
            continue
        name = str(g.get("name", "")).strip()[:80]
        if not name and not keep_blank:
            continue
        kind = "debt" if str(g.get("kind", "")).lower() == "debt" else "savings"
        out.append({"name": name, "kind": kind, "target": _pos(g.get("target")), "current": _pos(g.get("current")),
                    "years": min(max(_num(g.get("years", 5)) or 5, 1), 50),
                    "priority": g.get("priority") if g.get("priority") in ("High", "Medium", "Low") else "Medium",
                    "constraints": str(g.get("constraints", ""))[:200]})
    return out


def validate_goals(p, goals):
    errors, warnings = [], []
    if not goals:
        errors.append("Add at least one goal with a name and a target amount.")
    for g in goals:
        if g["target"] <= 0:
            errors.append(f"'{g['name']}': the target amount must be above 0.")
    names = [g["name"].lower() for g in goals]
    if len(set(names)) != len(names):
        warnings.append("Two goals share the same name; consider renaming one.")
    avail = p["assets"] + p["investments"]
    used = sum(g["current"] for g in goals)
    if used > avail + 1:
        errors.append(f"Existing funds assigned to goals ({vnd(used)}) exceed your total assets plus investments ({vnd(avail)}). "
                      "The same money cannot fund two goals - reduce the existing funds of one or more goals.")
    for g in goals:
        if g["kind"] == "debt" and p["debt"] > 0 and g["target"] > p["debt"] * 1.0001:
            warnings.append(f"'{g['name']}': the target is larger than your recorded total debt ({vnd(p['debt'])}).")
        if g["kind"] == "debt" and p["debt"] == 0:
            warnings.append(f"'{g['name']}': you recorded no debt in Financial Information.")
    if sum(1 for g in goals if g["kind"] == "debt") > 1:
        warnings.append("Several debt goals are not combined: each one is calculated against the same debt payment.")
    return errors, warnings


def _fit(p, m, goal, plan):
    notes, pen = [], 0
    is_em = "emergency" in goal["name"].lower()
    is_debt = goal["kind"] == "debt"
    if m["emergency_months"] is not None and m["emergency_months"] < m["target_months"] and not is_em:
        pen += 10
        notes.append(f"Emergency reserve is below the {m['target_months']}-month target (precondition not met).")
    if m["dti"] is not None and m["dti"] >= 0.36 and not is_debt:
        pen += 10
        notes.append("Debt-to-income is above 36%, so debt reduction should be handled in parallel.")
    if goal["years"] <= 2 and p["risk"] == "high":
        notes.append("Short timeframe: avoid high-volatility assets for this goal.")
    if plan.get("negative_amortization"):
        pen += 15
        notes.append("The payment does not cover the interest, so this debt would grow.")
    if goal["target"] > 0 and goal["current"] >= goal["target"]:
        pen += 60
        notes.append("This goal is already fully funded, so it needs no further saving.")
    pr = PRIORITY.get(str(goal.get("priority", "Medium")).lower(), 70)
    return max(0, min(100, round(0.7 * plan["completion"] * 100 + 0.3 * pr - pen))), notes


def _make_plan(p, g, years, save, ret):
    return goal_plan(g["name"], g["target"], g["current"], years, save, ret, g["kind"], p["debt_rate"], p["debt_payment"])


def _rank(p, m, goals, monthly_save, ret, years_override=None, idx_override=None):
    out = []
    for i, g in enumerate(goals):
        y = years_override if (years_override and i == idx_override) else g["years"]
        pl = _make_plan(p, g, y, monthly_save, ret)
        fit, notes = _fit(p, m, g, pl)
        out.append({"idx": i, "name": g["name"], "kind": g["kind"], "fit": fit, "completion": pl["completion"],
                    "required_monthly": pl["required_monthly"],
                    "share_of_capacity": (pl["required_monthly"] / monthly_save) if monthly_save else None,
                    "priority": g.get("priority", "Medium"), "years": y, "target": g["target"], "notes": notes, "plan": pl})
    return sorted(out, key=lambda x: (-x["fit"], -x["completion"], x["idx"]))


def allocate(ranked, capacity):
    """Share one monthly capacity across goals in ranking order so no VND is counted twice."""
    rem = capacity
    rows, tot_req = [], 0.0
    for x in ranked:
        req = x["plan"]["required_monthly"]
        got = min(req, rem)
        rem -= got
        tot_req += req
        rows.append({"idx": x["idx"], "name": x["name"], "required": req, "allocated": got,
                     "funded": 1.0 if req <= 0 else got / req})
    return {"rows": rows, "capacity": capacity, "total_required": tot_req, "total_allocated": capacity - rem,
            "unallocated": rem, "shortfall": max(tot_req - capacity, 0.0)}


def _slim(r):
    return {k: v for k, v in r.items() if k != "plan"}


def goals_analyze(profile, goals=None, chosen=None, assumptions=None):
    p = clean_profile(profile)
    m = metrics(p)
    goals = clean_goals(goals) or default_goals(p)
    errors, warnings = validate_goals(p, goals)
    if errors:
        return {"errors": errors, "warnings": warnings}
    base_ret = BASE_RETURN[p["risk"]]
    base_save = m["savings_capacity"]
    ranked = _rank(p, m, goals, base_save, base_ret)
    ai_pick = ranked[0]["idx"]
    primary = chosen if isinstance(chosen, int) and 0 <= chosen < len(goals) else ai_pick
    pg = goals[primary]
    plan_base = _make_plan(p, pg, pg["years"], base_save, base_ret)
    alloc = allocate(ranked, base_save)
    res = {"profile": p, "metrics": m, "goals": goals, "warnings": warnings,
           "ranking": [_slim(r) | {"rank": i + 1} for i, r in enumerate(ranked)],
           "ai_pick": ai_pick, "primary": primary, "plan_baseline": plan_base, "allocation": alloc,
           "baseline_capacity": {"monthly_income": p["income"], "net_cash_flow": m["net_cash_flow"], "monthly_save": base_save,
                                 "annual_return": base_ret, "savings_rate": m["savings_rate"]},
           "assumed": None, "secondary": None, "plan_assumed": None, "allocation_assumed": None}
    a = assumptions or None
    if a:
        inc2 = _pos(a.get("income")) or p["income"]
        rate = min(max(_num(a.get("save_rate", m["savings_rate"] * 100)), 0), 100) / 100
        sign = -1 if str(a.get("ret_sign", "+")) in ("-", "−") else 1
        ret2 = max(base_ret + sign * min(max(_num(a.get("ret_pct")), 0), 100) / 100, -0.9)
        yrs2 = min(max(_num(a.get("years", pg["years"])) or pg["years"], 1), 50)
        cf2 = inc2 - p["expenses"] - p["debt_payment"]
        req_save = rate * inc2
        save2 = min(req_save, max(cf2, 0))
        res["assumed"] = {"monthly_income": inc2, "net_cash_flow": cf2, "requested_save": req_save, "monthly_save": save2,
                          "annual_return": ret2, "savings_rate": rate, "years": yrs2, "exceeds_cash_flow": max(req_save - save2, 0)}
        res["plan_assumed"] = _make_plan(p, pg, yrs2, save2, ret2)
        p2 = dict(p, income=inc2)
        m2 = metrics(p2)
        r2_all = _rank(p2, m2, goals, save2, ret2, yrs2, primary)
        res["allocation_assumed"] = allocate(r2_all, save2)
        others = [g for i, g in enumerate(goals) if i != primary]
        suggested = False
        if not others:
            others = [{"name": "Additional Investment Fund", "kind": "savings", "target": round(12 * inc2), "current": 0,
                       "years": max(int(yrs2), 5), "priority": "Medium", "constraints": "AI-suggested optional goal"}]
            suggested = True
        r2 = _rank(p2, m2, others, save2, ret2)[0]
        sg = others[r2["idx"]]
        res["secondary"] = {"name": sg["name"], "kind": sg["kind"], "suggested": suggested, "fit": r2["fit"], "notes": r2["notes"],
                            "plan": r2["plan"], "years": sg["years"], "plan_baseline": _make_plan(p, sg, sg["years"], base_save, base_ret)}
    ylen = max(len(plan_base["series"]), len(res["plan_assumed"]["series"]) if res["plan_assumed"] else 0)
    pad = lambda s: s + [None] * (ylen - len(s))
    res["chart"] = {"labels": list(range(ylen)), "baseline": pad(plan_base["series"]),
                    "required": pad(plan_base["required_series"]) if plan_base["required_series"] else None,
                    "assumed": pad(res["plan_assumed"]["series"]) if res["plan_assumed"] else None,
                    "target": [pg["target"]] * ylen}
    return res


# ------------------------------------------------------------------- Excel
def _sheet(wb, title, rows, widths=(44, 26, 26, 26, 26)):
    from openpyxl.styles import Alignment, Font, PatternFill
    ws = wb.create_sheet(title)
    for r in rows:
        ws.append(list(r))
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(c.value, float):
                c.number_format = "#,##0.00" if abs(c.value) < 10 else "#,##0"
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="41734E")
    return ws


DISCLAIMER = ("FINOVA is a financial planning support platform for educational and informational purposes only. "
              "Results are mathematical estimates based on user-provided data and stated assumptions, not guarantees, "
              "audits or investment advice.")


def _safe(v):
    """Neutralise spreadsheet formula injection in exported text."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v


def report_xlsx(profile):
    from openpyxl import Workbook
    a = analysis(profile)
    p, m = a["profile"], a["metrics"]
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "Financial Summary", [
        ("Item", "Value", "Unit"),
        ("Monthly income", p["income"], "VND/month"), ("Monthly expenses", p["expenses"], "VND/month"),
        ("Monthly debt payment", p["debt_payment"], "VND/month"), ("Investments", p["investments"], "VND"),
        ("Assets", p["assets"], "VND"), ("Total debt", p["debt"], "VND"), ("Debt interest rate", p["debt_rate"], "% per year"),
        ("Time horizon", p["years"], "years"), ("Liquidity need", p["liquidity"], ""), ("Risk level", p["risk"], ""),
        ("Net monthly cash flow", m["net_cash_flow"], "VND/month"),
        ("Expense-to-income ratio", m["expense_ratio"] if m["expense_ratio"] is not None else "n/a", "ratio"),
        ("Debt-to-income (DTI)", m["dti"] if m["dti"] is not None else "n/a", "ratio"),
        ("Monthly savings capacity", m["savings_capacity"], "VND/month"), ("Total assets", m["total_assets"], "VND"),
        ("Total current liabilities", m["liabilities"], "VND"), ("Estimated net worth", m["net_worth"], "VND"),
        (), ("Disclaimer", DISCLAIMER)], widths=(46, 70, 16))
    _sheet(wb, "Health Assessment", [("Pillar", "Status", "Detail")] + [(i["pillar"], i["status"], i["text"]) for i in a["health"]["items"]]
           + [(), ("Actions",)] + [(x,) for x in a["health"]["actions"]], widths=(30, 24, 90))
    rows = [("Scenario", "Suitability %", "Net cash flow / month", "Savings capacity / month", "Annual yield", "Final net worth", "Assumptions")]
    for s in sorted(a["scenarios"], key=lambda s: s["rank"]):
        rows.append((s["title"], s["score"], s["net_cash_flow"], s["savings_capacity"], s["assumptions"]["annual_return"], s["final_net_worth"], s["desc"]))
    _sheet(wb, "Scenarios", rows, widths=(52, 14, 22, 24, 14, 22, 80))
    rows = [("Year",) + tuple(s["short"] for s in a["scenarios"])]
    for i, y in enumerate(a["years"]):
        rows.append((y,) + tuple(s["net_worth_by_year"][i] for s in a["scenarios"]))
    _sheet(wb, "Net Worth Projection", rows, widths=(10, 24, 24, 24, 24, 24))
    _sheet(wb, "Assumptions", [("Assumption",)] + [(x,) for x in a["assumption_notes"]], widths=(120,))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def plan_xlsx(profile, goals, chosen, assumptions):
    from openpyxl import Workbook
    r = goals_analyze(profile, goals, chosen, assumptions)
    if "errors" in r:
        raise ValueError(" ".join(r["errors"]))
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "Goals", [("Goal", "Type", "Target (VND)", "Existing funds (VND)", "Years", "Priority", "Constraints")] +
           [(_safe(g["name"]), g["kind"], g["target"], g["current"], g["years"], g["priority"], _safe(g["constraints"])) for g in r["goals"]],
           widths=(30, 10, 20, 22, 10, 12, 50))
    _sheet(wb, "AI Ranking", [("Rank", "Goal", "Fit score", "Completion", "Required monthly (VND)")] +
           [(x["rank"], _safe(x["name"]), x["fit"], x["completion"], x["required_monthly"]) for x in r["ranking"]], widths=(8, 34, 12, 14, 26))
    al = r["allocation"]
    _sheet(wb, "Funding Allocation", [("Goal", "Required / month", "Allocated / month", "Funded %")] +
           [(_safe(x["name"]), x["required"], x["allocated"], x["funded"]) for x in al["rows"]] +
           [(), ("Capacity", al["capacity"]), ("Unallocated", al["unallocated"]), ("Shortfall", al["shortfall"])], widths=(34, 22, 22, 14))

    def plan_rows(title, pl):
        return [(title,), ("Goal", _safe(pl["name"])), ("Type", pl["kind"]), ("Target", pl["target"]), ("Existing funds", pl["current"]), ("Years", pl["years"]),
                ("Monthly amount applied", pl["monthly_save"]), ("Annual return (simulated)", pl["annual_return"]),
                ("Additional total required", pl["extra_needed"]), ("Required monthly", pl["required_monthly"]),
                ("Time to goal at this rate", dur(pl["months_at_rate"])), ("Gap (applied - required)", pl["gap"]),
                ("Projected value at deadline", pl["projected"]), ("Completion", pl["completion"]), ()]
    rows = plan_rows("Plan on current baseline", r["plan_baseline"])
    if r["plan_assumed"]:
        rows += plan_rows("Plan on future assumptions (hypothetical)", r["plan_assumed"])
    if r["secondary"]:
        rows += plan_rows("Secondary goal (hypothetical)", r["secondary"]["plan"])
    rows += [("Disclaimer", DISCLAIMER)]
    _sheet(wb, "Plans", rows, widths=(40, 40))
    c = r["chart"]
    rows = [("Year", "Baseline plan", "Required path", "Assumed plan", "Target")] + [
        (y, c["baseline"][i], (c["required"] or [None] * 99)[i], (c["assumed"] or [None] * 99)[i], c["target"][i]) for i, y in enumerate(c["labels"])]
    _sheet(wb, "Projection", rows, widths=(10, 22, 22, 22, 22))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


ALIASES = {
    "income": ["monthly income", "income", "total monthly income", "thu nhập", "thu nhập hàng tháng", "thu nhap hang thang"],
    "expenses": ["monthly expenses", "expenses", "monthly spending", "living expenses", "chi tiêu", "chi tiêu hàng tháng", "chi tieu hang thang"],
    "investments": ["investments", "investment", "đầu tư", "dau tu"],
    "assets": ["assets", "savings", "cash", "tài sản", "tai san"],
    "years": ["time horizon (years)", "time horizon", "years", "horizon", "thời hạn", "thoi han"],
    "liquidity": ["liquidity need", "liquidity", "nhu cầu thanh khoản"],
    "risk": ["risk level", "risk", "risk tolerance", "mức độ rủi ro"],
    "debt": ["total current debt", "total debt", "debt", "liabilities", "tổng nợ", "tong no"],
    "debt_payment": ["monthly debt payment", "debt payment", "monthly debt service", "nợ phải trả hàng tháng"],
    "debt_rate": ["debt interest rate", "average debt interest rate", "interest rate", "lãi suất nợ"],
}
FIELD_MAP = {a: k for k, v in ALIASES.items() for a in v}
CATEGORY_WORDS = {"low": "low", "thấp": "low", "thap": "low", "medium": "medium", "moderate": "medium", "trung bình": "medium", "trung binh": "medium", "high": "high", "cao": "high"}
MAX_XLSX = 4 * 1024 * 1024


def _norm_label(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def sanitize_fields(d):
    """Keep only whitelisted, valid fields. Returns (clean, warnings)."""
    out, warns = {}, []
    for k, v in (d or {}).items():
        if k in ("liquidity", "risk"):
            w = CATEGORY_WORDS.get(_norm_label(v))
            if w:
                out[k] = w
            else:
                warns.append(f"'{k}' must be low, medium or high (got '{v}').")
        elif k in MONEY_KEYS or k in ("debt_rate", "years"):
            x = _clean_number(v)
            if x is None:
                warns.append(f"'{k}' is not a number ({v!r}).")
            elif x < 0:
                warns.append(f"'{k}' cannot be negative; it was ignored.")
            elif k == "years" and not 1 <= x <= 30:
                warns.append("'years' must be between 1 and 30.")
            elif k == "debt_rate" and x > 100:
                warns.append("'debt_rate' must be between 0 and 100 (% per year).")
            elif x > MAX_VALUE:
                warns.append(f"'{k}' is unrealistically large.")
            else:
                out[k] = int(x) if k == "years" else x
    return out, warns


def _clean_number(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    s = re.sub(r"(?i)\s*(vnd|đ|d|%|/month|per month)\s*$", "", str(v).strip())
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        x = float(s.replace(",", "."))
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def template_xlsx():
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "FINOVA Input", [
        ("Field", "Value", "Example / allowed values"),
        ("Monthly income", 25000000, "VND per month, 0 or more"), ("Monthly expenses", 12000000, "VND per month, 0 or more"),
        ("Investments", 50000000, "VND, 0 or more"), ("Assets", 120000000, "VND, 0 or more"),
        ("Time horizon (years)", 10, "Whole number from 1 to 30"), ("Liquidity need", "medium", "low / medium / high"),
        ("Risk level", "medium", "low / medium / high"), ("Total current debt", 80000000, "VND, 0 or more"),
        ("Monthly debt payment", 3000000, "VND per month, 0 or more"),
        ("Debt interest rate", 0, "% per year, optional (0 to 100)")], widths=(28, 20, 40))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def parse_xlsx(raw):
    """Parse an uploaded workbook deterministically (label/value rows). Raises ValueError with a
    user-friendly message for unreadable files."""
    from openpyxl import load_workbook
    if not raw or len(raw) > MAX_XLSX:
        raise ValueError("The file is empty or larger than 4 MB.")
    if raw[:2] != b"PK":
        raise ValueError("This is not a valid .xlsx workbook (wrong file signature).")
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        raise ValueError("The workbook is corrupted or password-protected and could not be read.")
    rows, data, warnings, seen, unrecognized = [], {}, [], set(), []
    try:
        for ws in wb.worksheets[:3]:
            for row in ws.iter_rows(values_only=True, max_row=300, max_col=6):
                cells = [c for c in (row or ()) if c not in (None, "")]
                if len(cells) >= 2:
                    rows.append((str(cells[0]).strip()[:80], cells[1]))
    except Exception:
        raise ValueError("The workbook content could not be read. Please use the FINOVA template.")
    if not rows:
        raise ValueError("No label/value rows were found. Please use the FINOVA template.")
    for label, value in rows:
        key = FIELD_MAP.get(_norm_label(label))
        if not key:
            if _norm_label(label) not in ("field", "item", "label"):
                unrecognized.append({"label": label, "value": value if isinstance(value, (int, float)) else str(value)[:60]})
            continue
        if key in seen:
            warnings.append(f"'{label}' appears more than once; the first value was used.")
            continue
        if isinstance(value, str) and value.startswith("#"):
            warnings.append(f"'{label}' contains a spreadsheet error ({value}).")
            seen.add(key)
            continue
        seen.add(key)
        clean, w = sanitize_fields({key: value})
        warnings += [f"'{label}': {x}" if "'" not in x else x for x in w]
        data.update(clean)
    missing = [k for k in ALIASES if k not in seen and k != "debt_rate"]
    return {"data": data, "warnings": warnings, "missing": missing, "unrecognized": unrecognized[:20], "rows": rows[:60]}


# --------------------------------------------------------- free-text numbers
UNITS = {"billion": 1e9, "bn": 1e9, "tỷ": 1e9, "ty": 1e9, "tỉ": 1e9, "million": 1e6, "mil": 1e6, "m": 1e6, "triệu": 1e6, "trieu": 1e6, "tr": 1e6,
         "thousand": 1e3, "k": 1e3, "nghìn": 1e3, "ngàn": 1e3}


def text_numbers(text):
    """All numeric quantities mentioned in free text, with unit words expanded (25 million -> 25e6)."""
    out = []
    for m in re.finditer(r"(\d[\d.,]*)\s*(billion|bn|tỷ|tỉ|ty|million|mil|triệu|trieu|tr|thousand|nghìn|ngàn|k|m)?(?![a-zà-ỹ])", str(text or ""), re.I):
        x = _clean_number(m.group(1).rstrip(".,"))
        if x is None:
            continue
        out.append(x * UNITS.get((m.group(2) or "").lower(), 1))
        out.append(x)
    return out


def verify_against_text(fields, text):
    """Accept an LLM-extracted field only if its value is traceable to the user's own text."""
    nums, low, ok, rejected = text_numbers(text), str(text or "").lower(), {}, []
    for k, v in fields.items():
        if k in ("liquidity", "risk"):
            hit = any(w in low for w, c in CATEGORY_WORDS.items() if c == v)
        else:
            hit = v == 0 or any(abs(v - c) <= 0.005 * max(abs(c), 1) for c in nums)
        (ok.__setitem__(k, v) if hit else rejected.append(k))
    return ok, rejected


# ------------------------------------------------------------- grounding
def _numbers_in(obj, out):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out)


def collect_numbers(obj):
    out = []
    _numbers_in(obj, out)
    return out


def grounded_rate(text, outputs, money_only=False):
    """(grounded, checked): money (comma-formatted) and percentage figures in `text` that exist in
    the engine outputs. Used for the Groundedness evaluation and to reject hallucinated LLM text."""
    vals = collect_numbers(outputs)
    checked = ok = 0
    for t in re.findall(r"\d[\d,]*\.?\d*%?", str(text)):
        pct_ = t.endswith("%")
        try:
            x = float(t.rstrip("%").replace(",", ""))
        except ValueError:
            continue
        if not pct_ and "," not in t:
            continue
        if pct_ and money_only:
            continue
        checked += 1
        if pct_:
            hit = any(abs(abs(v) * 100 - x) <= 0.06 or abs(abs(v) - x) <= 0.06 for v in vals)
        else:
            hit = any(abs(abs(v) - x) <= max(1.0, 0.002 * abs(v)) for v in vals)
        ok += hit
    return ok, checked
