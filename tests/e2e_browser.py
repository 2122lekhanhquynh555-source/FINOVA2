from playwright.sync_api import sync_playwright
errs=[]
def run():
  with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1400,'height':900}); pg=ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('PAGEERR '+str(e)))
    pg.on('console',lambda m: errs.append('CONSOLE '+m.text) if m.type=='error' and 'ERR_' not in m.text and 'Failed to load' not in m.text else None)
    pg.route("**/Chart.js/**", lambda r: r.fulfill(body="window.Chart=function(el,c){this.data=c.data;this.update=function(){};this.destroy=function(){}}",content_type="application/javascript"))
    pg.route("**/fonts.googleapis.com/**", lambda r: r.abort()); pg.route("**/commons.wikimedia.org/**", lambda r: r.abort())
    B="http://localhost:5057/"
    # forgot password with demo code (no account yet -> register first then logout)
    pg.goto(B+"#/register"); pg.fill("#n","An Nguyen"); pg.fill("#e","an@x.com"); pg.fill("#p","abc12345"); pg.fill("#c","abc12345"); pg.click("#go"); pg.wait_for_selector(".carousel")
    pg.click("#userBtn"); pg.click("#logout"); pg.wait_for_url("**/#/")
    pg.goto(B+"#/forgot"); pg.fill("#e","an@x.com"); pg.click("#s1 button"); pg.wait_for_selector("#s2:not([hidden])")
    code=pg.inner_text(".notice.warn b:nth-of-type(2)") if pg.query_selector(".notice.warn b:nth-of-type(2)") else pg.inner_text(".notice.warn b")
    code=[x for x in pg.inner_text(".notice.warn").split() if x.isdigit() and len(x)==6][0]
    pg.fill("#cd",code); pg.fill("#p","newpass99"); pg.fill("#c","newpass99"); pg.click("#s2 .btn"); pg.wait_for_timeout(1500); print("after reset:", pg.url, pg.inner_text("#m")[:150]); pg.wait_for_selector("#f")
    pg.fill("#e","an@x.com"); pg.fill("#p","newpass99"); pg.click("#go"); pg.wait_for_selector(".carousel"); print("reset+login ok")
    # finance with AI parse
    pg.goto(B+"#/finance"); pg.wait_for_selector("#aiText")
    pg.fill("#aiText","I earn 30 million and spend 14 million each month, hallucinate"); pg.click("#aiParse"); pg.wait_for_selector("#aiOut .msg")
    print("AI parse:", pg.inner_text("#aiOut")[:160].replace("\n"," | ")); print("income field:", pg.input_value("#income"), "assets:", repr(pg.input_value("#assets")))
    pg.fill("#assets","120,000,000"); pg.fill("#debt","80000000"); pg.fill("#debt_payment","3000000"); pg.fill("#debt_rate","8"); pg.fill("#investments","50000000")
    pg.click("#save"); pg.wait_for_selector("#m .msg.ok"); 
    # excel upload (template)
    tpl=ctx.request.get(B+"api/finance/template").body(); open("/tmp/tpl.xlsx","wb").write(tpl)
    pg.set_input_files("#file","/tmp/tpl.xlsx"); pg.wait_for_selector("#im .msg"); print("excel:", pg.inner_text("#im")[:140].replace("\n"," | "))
    pg.fill("#income","30000000"); pg.fill("#expenses","14000000"); pg.click("#save"); pg.wait_for_selector("#m .msg.ok")
    pg.click("button[type=submit]"); pg.wait_for_selector("#wiRun"); pg.locator("#nar-tag", has_text="AI-generated").wait_for(timeout=15000); print("tag:", pg.inner_text("#nar-tag"))
    pg.fill("#wi-p-income","20"); pg.select_option("#wi-s-income","-"); pg.fill("#wi-p-unforeseen","10"); pg.click("#wiRun"); pg.wait_for_selector("#wi-nar"); pg.locator("#wi-tag", has_text="AI-generated").wait_for(timeout=15000)
    print("whatif rows:", len(pg.query_selector_all("#wiOut tbody tr")), "|", pg.inner_text("#wi-tag"))
    pg.screenshot(path="/tmp/r3.png", full_page=True)
    # savings
    pg.goto(B+"#/savings"); pg.wait_for_selector("#analyze"); pg.click("#analyze"); pg.wait_for_selector("#recalc"); pg.locator(".sv-tag", has_text="AI-generated").first.wait_for(timeout=15000)
    print("alloc table:", len(pg.query_selector_all("#svResult table")), "tag:", pg.inner_text(".sv-tag"))
    pg.fill("#w2","40000000"); pg.click("#recalc"); pg.wait_for_selector("#sv-second")
    pg.fill("#pname","Plan A"); pg.click("#savePlan"); pg.wait_for_selector("#updPlan")
    pg.fill("#pname","Plan A v2"); pg.click("#updPlan"); pg.wait_for_timeout(500)
    pg.click("#savePlan"); pg.wait_for_timeout(500); pg.click("#newPlan"); pg.wait_for_timeout(300)
    for c in pg.query_selector_all(".pick"): c.check()
    pg.click("#cmp"); pg.wait_for_selector("#cmpOut table"); print("compare cols:", len(pg.query_selector_all("#cmpOut thead th")))
    # invalid goal (double counting) shows error
    pg.fill(".goal:nth-child(1) [data-k=current]","9999999999"); pg.click("#analyze"); pg.wait_for_selector("#gm .msg.err"); print("err:", pg.inner_text("#gm")[:90])
    pg.screenshot(path="/tmp/s3.png", full_page=True)
    pg.click("#aiGoals")
    # export download
    with pg.expect_download() as d: pg.click("#exPlan")
    print("download:", d.value.suggested_filename)
    # evaluation
    pg.goto(B+"#/evaluation"); pg.wait_for_selector("#confirm")
    for k in ["accuracy","groundedness","usability","processing"]: pg.click(f"#st-{k} button[data-v='4']")
    pg.click("#confirm"); pg.wait_for_selector(".star-meter"); pg.wait_for_selector("#dash table"); print("dash rows:", len(pg.query_selector_all("#dash tbody tr")), [x.inner_text() for x in pg.query_selector_all("#dash tbody tr td:last-child")])
    pg.screenshot(path="/tmp/e3.png", full_page=True)
    # support + chat
    pg.goto(B+"#/support"); pg.wait_for_selector("#tp")
    pg.click("[data-t=ticket]"); pg.click(".type-card >> nth=0"); pg.fill("#su","Cannot login"); pg.fill("#de","The page freezes after I press login."); pg.click("#tf button[type=submit]"); pg.wait_for_selector("#tm .msg.ok")
    pg.click("[data-t=mine]"); pg.wait_for_selector("#mineList table"); print("my ticket:", pg.inner_text("#mineList tbody tr")[:70].replace("\n"," "))
    pg.click("[data-t=chat]"); pg.fill("#ci","How is DTI calculated?"); pg.press("#ci","Enter"); pg.locator(".bubble.bot", has_text="MOCK-CHAT").wait_for(timeout=15000)
    print("chat:", pg.inner_text(".bubble.bot >> nth=1")[:150].replace("\n"," "))
    # admin
    ctx2=b.new_context(viewport={'width':1400,'height':900}); p2=ctx2.new_page(); p2.route("**/Chart.js/**", lambda r: r.fulfill(body="window.Chart=function(){this.update=function(){};this.destroy=function(){}}",content_type="application/javascript")); p2.route("**/fonts.googleapis.com/**", lambda r: r.abort()); p2.route("**/commons.wikimedia.org/**", lambda r: r.abort())
    p2.goto(B+"#/register"); p2.fill("#n","Admin"); p2.fill("#e","admin@x.com"); p2.fill("#p","abc12345"); p2.fill("#c","abc12345"); p2.click("#go"); p2.wait_for_selector(".carousel")
    p2.goto(B+"#/support"); p2.wait_for_selector("[data-t=admin]"); p2.click("[data-t=admin]"); p2.wait_for_selector("#adminList table"); p2.select_option("[data-st]","resolved"); p2.click("[data-save]"); p2.wait_for_timeout(400)
    pg.click("[data-t=mine]"); pg.wait_for_timeout(600); print("status now:", pg.inner_text("#mineList tbody tr td:nth-child(4)"))
    pg.click("#themeBtn"); pg.goto(B+"#/results"); pg.wait_for_selector("#wiRun"); pg.screenshot(path="/tmp/d3.png")
    b.close()
run(); print("\n".join(errs) or "no JS/CSP errors")
