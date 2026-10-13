"""Rule-based explanations built only from engine outputs (no invented figures)."""
from engine import dur, pc, vnd

GOAL_NAMES = {"g1": "Emergency Fund (cash)", "g2": "Debt Freedom", "g3": "Wealth Milestone (investments)"}


def _delay_txt(d, reach):
    if reach is None:
        return "not reached within 50 years"
    if d is None:
        return f"reached in {dur(reach)}"
    if d == 0:
        return f"on track ({dur(reach)})"
    return f"{'delayed by' if d > 0 else 'reached earlier by'} {dur(abs(d))} (reached in {dur(reach)})"


def analysis(a):
    m, p = a["metrics"], a["profile"]
    sc = {s["key"]: s for s in a["scenarios"]}
    base = sc["baseline"]
    n = p["years"]
    ranked = [sc[k] for k in a["ranking"]]

    table = "\n".join([
        f"- **Total monthly income ({vnd(m['income'])})** is the starting point of every calculation.",
        f"- **Net available cash flow ({vnd(m['net_cash_flow'])})** is income minus living expenses ({vnd(m['expenses'])}) and debt service ({vnd(m['debt_payment'])}).",
        f"- **Monthly wealth accumulation** in the Baseline scenario is {vnd(base['savings_capacity'])}, i.e. {pc(m['savings_rate'])} of income.",
        f"- **Projected net worth** after {n} years is {vnd(base['final_net_worth'])} in the Baseline scenario, from {vnd(m['net_worth'])} today.",
        f"- **Expense-to-income ratio** is {pc(m['expense_ratio'])} and **DTI** is {pc(m['dti'])}."
        if m["income"] else "- Enter an income above 0 to unlock ratio analysis."])

    hi, lo = max(a["scenarios"], key=lambda s: s["final_net_worth"]), min(a["scenarios"], key=lambda s: s["final_net_worth"])
    g3 = a["goal_targets"]["g3"]
    chart = "\n".join([
        f"- The steepest accumulation slope belongs to the **{hi['short']}** scenario, ending at {vnd(hi['final_net_worth'])} after {n} years; the flattest is **{lo['short']}**, ending at {vnd(lo['final_net_worth'])}.",
        f"- The Wealth Milestone target (investment pool) is {vnd(g3)}. In the Baseline scenario it is {_delay_txt(None, base['reach']['g3'])}.",
        f"- At the end of the horizon the Baseline investment pool is {vnd(base['wealth_gap'])} relative to that target (negative = shortfall, positive = surplus).",
        f"- The gap between the highest and lowest trajectory is {vnd(hi['final_net_worth'] - lo['final_net_worth'])}, which shows how sensitive the plan is to income, expenses and yield."])

    adv = {
        "severe": ("Shows whether your plan survives a serious shock; forces a realistic emergency plan.",
                   "Cash flow is the most strained; goals are delayed the most.",
                   "Accept slower goals and protect liquidity before investing."),
        "conservative": ("Realistic cushion against a mild downturn.",
                         "Lower accumulation than baseline.",
                         "Give up some growth to keep a safety margin."),
        "baseline": ("Built on your own declared numbers, so it is the most transparent reference.",
                     "Assumes your income and spending stay unchanged for the whole horizon.",
                     "Requires disciplined, consistent saving."),
        "optimistic": ("Faster progress if income grows modestly.",
                       "Depends on income growth you do not control.",
                       "Do not commit spending to income you have not yet earned."),
        "high": ("Shows the upside if income and savings rise strongly.",
                 "Least likely path; over-relying on it can mask real risks.",
                 "Aim for it only with a clear plan to raise income, and keep a baseline fallback."),
    }
    per = {}
    for s in a["scenarios"]:
        ad, di, to = adv[s["key"]]
        asm = s["assumptions"]
        gl = "\n".join(f"  - {GOAL_NAMES[g]}: {_delay_txt(s['goal_delay'][g], s['reach'][g])}" for g in ("g1", "g2", "g3"))
        per[s["key"]] = (
            f"**Background & assumptions.** {s['desc']} Income change {pc(asm['income_change'], 0)}, expense change {pc(asm['expense_change'], 0)}, "
            f"simulated annual yield {pc(asm['annual_return'])}. Monthly cash flow becomes {vnd(s['net_cash_flow'])}.\n\n"
            f"**Impact on the 3 financial goals.**\n{gl}\n\n"
            f"**Advantages & disadvantages.** + {ad} − {di}\n\n"
            f"**Trade-offs.** {to} Projected net worth after {n} years: {vnd(s['final_net_worth'])}.")

    top = ranked[0]
    guidance = (f"Based on your cash flow of {vnd(m['net_cash_flow'])} and a {p['risk']} risk level, the **{top['short']}** scenario ranks as the most suitable "
                f"reference ({top['score']}%). Do not treat the most optimistic path as the best one: compare the downside case "
                f"({lo['short']}, {vnd(lo['final_net_worth'])} after {n} years) with the upside ({hi['short']}, {vnd(hi['final_net_worth'])}) "
                "and choose a plan you could still follow if conditions turn out worse than expected. All results are estimates that depend on the assumptions listed above.")
    return {"table": table, "chart": chart, "scenarios": per, "guidance": guidance, "recommendations": recommendations(a)}


def recommendations(a):
    m, p, h = a["metrics"], a["profile"], a["health"]
    issues = []
    if m["net_cash_flow"] < 0:
        issues.append(f"**Negative cash flow** of {vnd(-m['net_cash_flow'])} per month: expenses and debt service exceed income.")
    if m["dti"] is not None and m["dti"] >= 0.36:
        issues.append(f"**High debt burden**: debt service is {pc(m['dti'])} of income (guideline: below 36%).")
    if m["emergency_months"] is not None and m["emergency_months"] < m["target_months"]:
        issues.append(f"**Inadequate emergency fund**: {m['emergency_months']:.1f} months covered versus a {m['target_months']}-month target.")
    if m["savings_rate"] < 0.10:
        issues.append(f"**Low savings rate**: {pc(m['savings_rate'])} of income.")
    head = ("**High-priority issues**\n" + "\n".join(f"- {i}" for i in issues)) if issues else \
        "**No high-priority issues** were detected in cash flow, debt burden, liquidity or savings rate."
    strat = ("\n\n**Strategic orientation (general guidance, not product advice)**\n" +
             "\n".join(f"- {x}" for x in h["actions"]) +
             f"\n- Net worth today is {vnd(m['net_worth'])}; choose savings or investment goals only after the issues above are addressed.")
    return head + strat


def whatif(w, a_metrics):
    rows = {r["label"]: r for r in w["rows"]}
    net = rows["Net monthly cash flow"]
    liq = rows["Liquidity surplus / (deficit) vs target reserve"]
    gap = rows["Savings feasibility gap (capacity - plan)"]
    nwk = next(k for k in rows if k.startswith("Net worth after"))
    nw = rows[nwk]
    t = (f"- **Main finding:** net monthly cash flow moves from {vnd(net['baseline'])} to {vnd(net['adjusted'])} "
         f"(variance {vnd(net['variance'])}).\n"
         f"- **Long-term effect:** {nwk.lower()} changes from {vnd(nw['baseline'])} to {vnd(nw['adjusted'])} (variance {vnd(nw['variance'])}).\n"
         f"- **Liquidity:** the reserve position vs. the target reserve changes from {vnd(liq['baseline'])} to {vnd(liq['adjusted'])}.\n")
    if gap["adjusted"] < 0:
        t += f"- **Trade-off:** the planned savings exceed the new capacity by {vnd(-gap['adjusted'])} per month, so the savings plan is not fully funded.\n"
    else:
        t += f"- **Trade-off:** the new capacity covers the planned savings with {vnd(gap['adjusted'])} to spare each month.\n"
    for x in w.get("warnings", []):
        t += f"- **Risk:** {x}\n"
    t += "- Results are estimates built from your own inputs and the percentages you chose; they are not forecasts."
    return t


def _plan_block(pl):
    what = "extra debt repayment above your scheduled payment" if pl.get("kind") == "debt" else "monthly savings"
    parts = [f"- Additional total to {'repay' if pl.get('kind') == 'debt' else 'accumulate'}: {vnd(pl['extra_needed'])}",
             f"- Required {what}: {vnd(pl['required_monthly'])} (you apply {vnd(pl['monthly_save'])})",
             f"- Time to reach the goal at this savings rate: {dur(pl['months_at_rate'])}",
             f"- Gap between savings capacity and requirement: {vnd(pl['gap'])} per month",
             f"- Projected value at the {pl['years']:g}-year deadline: {vnd(pl['projected'])} ({pc(pl['completion'], 0)} of target)"]
    return "\n".join(parts)


def goals(r):
    rk, pr, m = r["ranking"], r["plan_baseline"], r["metrics"]
    chosen = next(x for x in rk if x["idx"] == r["primary"])
    lines = []
    for x in rk:
        share = "n/a" if x["share_of_capacity"] is None else pc(x["share_of_capacity"], 0)
        lines.append(f"- **{x['rank']}. {x['name']}** — success estimate {pc(x['completion'], 0)}, fit {x['fit']}%. "
                     f"Needs {vnd(x['required_monthly'])} per month, which is {share} of your savings capacity ({vnd(m['savings_capacity'])}). "
                     + " ".join(x["notes"]))
    why = (f"**{chosen['name']}** is recommended because it has the best fit with your finances: a {pc(chosen['completion'], 0)} estimated chance of completion within "
           f"{chosen['years']:g} years, using monthly net cash flow of {vnd(m['net_cash_flow'])}, "
           f"emergency coverage of {(m['emergency_months'] or 0):.1f} months, and a {r['profile']['risk']} risk level. "
           "You keep full authority: accept it or choose another goal below.")
    steps = [f"- **Step 1 — Confirm the numbers.** Target {vnd(pr['target'])}, existing funds {vnd(pr['current'])}, {pr['years']:g} years.",
             f"- **Step 2 — Automate the saving.** Move {vnd(pr['required_monthly'])} per month on payday; your capacity is {vnd(pr['monthly_save'])}."]
    for i, ms in enumerate(pr["milestones"]):
        steps.append(f"- **Milestone {i + 1} (month {ms['month']}):** expected balance {vnd(ms['balance'])} ({pc(ms['pct'], 0)} of the timeline).")
    steps.append("- **Review** every quarter and recalculate if income, expenses or yields change. Yields are simulated assumptions with no guarantee.")
    al = r["allocation"]
    lines.append(f"\n**Funding allocation:** your savings capacity of {vnd(al['capacity'])} per month is shared across goals in ranking order, so no money is counted twice. "
                 f"Total required for all goals is {vnd(al['total_required'])} per month; {vnd(al['total_allocated'])} can be allocated and {vnd(al['unallocated'])} remains unallocated"
                 + (f" (shortfall {vnd(al['shortfall'])})." if al["shortfall"] > 0 else "."))
    return {"ranking": "\n".join(lines), "primary": why + "\n\n**Plan figures**\n" + _plan_block(pr), "process": "\n".join(steps)}


def secondary(r):
    s, a = r["secondary"], r["assumed"]
    if not s:
        return ""
    pl = s["plan"]
    kind = "an AI-suggested optional goal" if s["suggested"] else "the best remaining goal"
    return (f"Under your hypothetical assumptions (income {vnd(a['monthly_income'])}, savings {vnd(a['monthly_save'])} per month, yield {pc(a['annual_return'])}), "
            f"**{s['name']}** is {kind}.\n\n"
            f"- **Why it may fit:** estimated completion {pc(pl['completion'], 0)} with fit {s['fit']}%.\n"
            f"- **Required savings capacity:** {vnd(pl['required_monthly'])} per month.\n"
            f"- **Timeframe and preconditions:** {s['years']:g} years; " + (" ".join(s["notes"]) or "no extra preconditions detected") + ".\n"
            f"- **Risk:** if income or yields fall below the assumed levels the goal may be delayed or missed.\n\n"
            "This secondary goal is an optional reference, not a guarantee of achievability.")
