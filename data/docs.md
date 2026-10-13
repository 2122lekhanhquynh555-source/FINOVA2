## What is FINOVA
FINOVA is a goal-based personal finance planning platform for educational and informational purposes. A deterministic Python engine performs every calculation. An AI language model (Gemini) only parses language, explains results, and answers questions. FINOVA never guarantees returns, never recommends specific securities, and is not personalized investment advice.

## Pages and navigation
After logging in, the left toolbar contains Overview, Customer Account, Financial Information, Savings & Investment, Evaluation, and Contact & Support. The Results page opens after you confirm Financial Information. The toolbar can be closed and reopened with the menu button.

## Financial Information inputs
Inputs are monthly income (VND/month), monthly expenses (VND/month), investments (VND), assets (VND, treated as cash and liquid savings), time horizon (1-30 years), liquidity need (low, medium, high), risk level (low, medium, high), total current debt (VND), monthly debt payment (VND/month) and an optional average debt interest rate (% per year). Amounts cannot be negative and thousands are separated by commas. You can also describe your finances in words (AI parsing) or upload an Excel template.

## Missing or conflicting data
Python validates every input path. Income of 0 is an error. Debt without a payment, a payment without debt, expenses plus debt payments above income, or a payment that does not cover monthly interest produce warnings. AI-extracted values are accepted only if the number can be found in the text you wrote.

## Financial metrics and formulas
Net monthly cash flow = income - living expenses - monthly debt payment. Expense-to-income ratio = expenses / income. Debt-to-income (DTI) = monthly debt payment / income. Savings capacity = max(net cash flow, 0). Total assets = assets + investments. Net worth = total assets - total current debt. Reserve coverage = assets / monthly expenses. The emergency target is 3, 6 or 9 months of expenses for low, medium or high liquidity need.

## Health assessment thresholds
Cash flow is positive when net cash flow is at least 10% of income, balanced when between 0 and 10%, negative below 0. Debt burden is low below 20% DTI, moderate from 20% to 36%, high from 36% to 50%, severe above 50%. Savings capacity is strong from 20% of income, healthy from 10%, modest from 5%, low below 5%.

## Five scenarios
Severely Conservative: income -25%, expenses +15%, yield -4 points. Conservative: income -10%, expenses +5%, yield -2 points. Baseline: your numbers. Optimistic: income +10%, yield +1 point. Highly Optimistic: income +25%, yield +2 points. The base annual yield is 3%, 6% or 9% for low, medium or high risk. These are simulated assumptions, not predictions. The AI ranks the scenarios by a suitability score based on your cash flow and risk level.

## Simulation waterfall and no double counting
The engine simulates month by month for up to 50 years. Each month's surplus is used once: first to refill the cash emergency reserve up to its target, then 50% to extra debt repayment while debt remains, and the rest is invested at the scenario yield. Deficits are paid from cash first, then from the investment pool. Cash funds only the Emergency Fund goal; investments fund only the Wealth Milestone. Debt accrues interest at the entered rate and is reduced by the scheduled payment.

## Three reference goals
Emergency Fund: cash equal to the emergency target. Debt Freedom: repay all current debt. Wealth Milestone: investment pool equal to 36 months of expenses. If you have no debt, a Home / Education Fund of 12 months of income replaces Debt Freedom. The existing funds assigned to goals cannot exceed total assets plus investments.

## What-if analysis and stress testing
You can change income, living expenses, unforeseen expenses, savings rate and optionally debt repayment by a percentage with plus or minus. Plus on unforeseen expenses adds an emergency cost equal to that percentage of monthly expenses every month; minus means zero emergency spending. A savings-rate change raises or lowers planned savings relative to your baseline savings; you cannot save more than the surplus that exists. The engine reruns the whole projection and compares net worth, investment pool, remaining debt and goal dates with the baseline.

## Required monthly savings formula
For a savings goal with target T, existing funds C, monthly rate r and n months, the future value factor is F = ((1+r)^n - 1) / r. Required monthly savings = max(T - C(1+r)^n, 0) / F. The projected balance is C(1+r)^n + S x F for monthly savings S. Completion = min(projected / T, 100%). Deposits are made at month end and compounded monthly, with no taxes or fees.

## Debt goals
For a debt goal the required total payment is the level loan payment PMT = D x rd / (1 - (1+rd)^-n) where D is the outstanding debt, rd the monthly interest rate and n the months. The extra payment needed is PMT minus your scheduled payment. Time to payoff uses the loan formula for the payment you apply. If a payment does not cover monthly interest, the debt grows and the plan warns you.

## Milestones
Milestones at 25%, 50%, 75% and 100% of the timeframe show the balance you must reach on the required-savings path, so the last milestone equals the target. The projected balance shows what your actual monthly savings would reach.

## Goal ranking and the primary goal
Each goal gets a fit score: 70% completion estimate plus 30% priority (High 100, Medium 70, Low 40), minus penalties when the emergency reserve is below target (10), debt-to-income is above 36% (10), debt would grow (15) or the goal is already fully funded (60). The highest score is the AI-recommended primary goal. You may always choose another goal. Goals are evaluated one at a time against your full capacity; the Funding Allocation table then shares one monthly capacity across goals in ranking order.

## What-if goal planning and secondary goal
Sliders set the timeframe (1-50 years), assumed monthly income, savings rate (0-100% of income, limited to the available cash flow) and an investment-return change (plus or minus a percentage). The AI then recommends a secondary goal among the remaining goals under the hypothetical conditions. Future assumptions are shown separately and are never real income or realized returns.

## Excel import and export
Download the template, fill in the Value column and upload an .xlsx file up to 4 MB. FINOVA reads label and value rows, reports invalid or missing fields, and the AI can suggest mappings for unrecognized labels, which Python validates before use. Export the financial report from Results and the savings or investment plan from Savings & Investment.

## Saving and comparing plans
You can save several planning options with a name, load one to edit it, update or rename it, delete it, and compare two or more side by side by goal, target, timeframe, savings, required monthly amount and completion.

## Evaluation criteria
Accuracy is checked against independent exact-arithmetic recomputation. Groundedness measures how many money and percentage figures in AI text come from Python outputs. Usability combines your 1-5 star ratings with task-completion tracking. Processing Time records engine, analysis and AI generation latency with average, 95th percentile and slow cases.

## Support requests
Choose one of eight issue types, add subject, description, an optional screenshot (png, jpg, gif, webp) and your email. You receive a ticket number and can view the status of your requests under My requests.

## Privacy and security
Passwords are stored as salted hashes. Sessions use signed secure cookies and requests are protected against cross-site forgery. Login attempts are rate limited. The AI API key is stored only in server environment variables and is never sent to the browser. The chatbot can only see the signed-in user's own data.

## Limitations
Results depend entirely on your inputs and assumptions. Interest, taxes, fees and inflation are not modeled except the optional debt interest rate. Yields are hypothetical. FINOVA is not a certified financial audit.
