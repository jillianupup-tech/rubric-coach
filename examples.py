# Built-in examples — NO API.
# Example 1 is the original Assignment 3 task and rubric (useful as the baseline comparison).
# Example 2 is a different subject, to show the app is not tied to one task.

EXAMPLES = {
    "Budget-to-actual variance analysis (business, original task)": {
        "task": """Task: Budget-to-Actual Variance Analysis

You are learning how to interpret a company's financial performance.

The company provided the following figures:
- Budgeted revenue: $100,000
- Budgeted expenses: $70,000
- Actual revenue: $90,000
- Actual expenses: $75,000

Write a short response that:
1. Calculates budgeted profit and actual profit.
2. Explains the revenue, expense, and profit variances.
3. Distinguishes what the figures show from possible causes
   that cannot be confirmed from the information provided.
4. Suggests one specific follow-up investigation.

Use only the information above. You may suggest possible causes,
but clearly label them as possibilities rather than established facts.""",
        "rubric": """Accept equivalent wording. Do not deduct points for writing style or grammar unless the meaning cannot be understood.

## Calculation accuracy | 0-4 step 0.5
Award 1 point for each correct item:
- Budgeted profit is $30,000.
- Actual profit is $15,000.
- Revenue is $10,000 below budget AND expenses are $5,000 above budget. Award 0.5 points if only one of these two variances is correct.
- Profit is $15,000 below budget.
Award 0 for an incorrect or missing item. In the feedback, list the credit for each of the four items and add them up.

## Explains the effect on profit | 0, 1, 2
- 2: Explains that both lower revenue and higher expenses reduced profit.
- 1: Explains only one of these factors.
- 0: Explains neither factor correctly.

## Distinguishes evidence from speculation | 0, 1, 2
- 2: Explicitly states that causes are unknown or labels any proposed causes as unverified possibilities, without unsupported factual claims.
- 1: Makes no unsupported causal claims but does not explicitly acknowledge the limits of the information.
- 0: Presents an unsupported cause as an established fact.

## Follow-up investigation | 0, 1, 2
- 2: Proposes a specific relevant investigation, such as comparing budgeted and actual sales volumes and prices, or examining expense categories to identify the source of the overrun.
- 1: Proposes only a vague investigation, such as "check the finances."
- 0: Provides no relevant follow-up investigation.""",
        "answers": {
            "Complete answer": """Budgeted profit was $30,000, calculated as $100,000 minus $70,000.
Actual profit was $15,000, calculated as $90,000 minus $75,000.

Revenue was $10,000 below budget, while expenses were $5,000 above budget. Together, lower revenue and higher expenses reduced profit by $15,000 compared with the budget.

The figures do not explain why revenue fell or expenses rose. Lower sales volume is one possible explanation for the revenue shortfall, but it cannot be confirmed from these figures alone.

I would compare budgeted and actual sales volumes and selling prices to investigate the revenue shortfall.""",
            "Flawed answer": """Budgeted profit was $30,000 and actual profit was $25,000.
Revenue was $10,000 below budget.
Profit therefore fell by $5,000.

Revenue fell because the sales team was lazy.
The company should check its finances.""",
        },
    },
    "Why does ice float? (middle-school science, claim-evidence-reasoning)": {
        "task": """Question (Grade 7 science): A student puts an ice cube in a glass of water and it floats.
Write a short claim-evidence-reasoning (CER) response that explains why ice floats on liquid water.
Use what you know about density and about how water molecules are arranged when water freezes.""",
        "rubric": """Students are in Grade 7. Accept everyday wording if the science idea is correct. Do not deduct points for spelling or grammar.

## Claim | 0, 1, 2
- 2: States clearly that ice floats because it is less dense than liquid water.
- 1: Gives a claim related to floating but vague or partly wrong (for example, "ice is lighter" without referring to density or to the same amount of water).
- 0: No claim, or an incorrect claim (for example, "ice floats because it has air bubbles" as the main reason).

## Evidence | 0, 1, 2
- 2: Gives relevant evidence, such as: the same mass of ice takes up more volume than liquid water; water expands when it freezes; ice density is about 0.92 g/cm³ compared with about 1.00 g/cm³ for liquid water.
- 1: Gives evidence that is relevant but incomplete or not clearly connected to density.
- 0: No relevant evidence.

## Reasoning | 0, 1, 2
- 2: Explains that when water freezes, its molecules form an open, spaced-out (hexagonal) structure held by hydrogen bonds, so ice has more volume for the same mass and therefore lower density; objects less dense than a liquid float in it.
- 1: Explains part of this chain (for example, mentions expansion or the less-dense rule) but leaves a gap.
- 0: No reasoning, or reasoning based on a misconception.""",
        "answers": {
            "Strong answer": """Claim: Ice floats because it is less dense than liquid water.
Evidence: When water freezes it expands, so the same mass of water takes up more space as ice. Ice has a density of about 0.92 g/cm3 and liquid water is about 1.0 g/cm3.
Reasoning: When water freezes, the molecules line up in an open pattern held together by hydrogen bonds, so there is more empty space between them. More volume with the same mass means lower density, and things that are less dense than a liquid float in it.""",
            "Answer with a misconception": """Ice floats because it is lighter than water and it has lots of air bubbles trapped inside it. Ice is a solid so it is lighter.""",
        },
    },
}

RUBRIC_FORMAT_HELP = """**How to write a rubric**

Start each criterion with a line `## Criterion name | allowed scores`, then describe what earns each score on the lines below it.

Allowed scores can be a list such as `0, 1, 2`, or a range such as `0-4 step 0.5` (0, 0.5, 1 … 4) or `1-5` (whole numbers).

Text before the first `##` line is treated as general grading notes (for example, "Do not deduct points for grammar").

```
Do not deduct points for spelling or grammar.

## Clear claim | 0, 1, 2
- 2: States a clear, arguable claim.
- 1: Claim is present but vague.
- 0: No claim.

## Use of evidence | 0-4 step 0.5
Award up to 4 points for relevant, accurate evidence ...
```
Up to 8 criteria. Use fictional or de-identified student work only."""

