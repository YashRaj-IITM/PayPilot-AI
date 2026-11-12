import os
import json

from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = """
You are PayPilot AI, an expert procurement intelligence assistant.

Your responsibilities:
1. Explain supplier rankings using the supplied numerical analysis.
2. Compare price, specifications and delivery.
3. Identify procurement risks and missing information.
4. Explain trade-offs clearly.
5. Recommend a supplier based on the available evidence.

Strict rules:
- Never invent supplier information.
- Never claim that a supplier is verified.
- Never invent product specifications.
- Treat the supplied scoring results as authoritative calculations.
- Clearly distinguish facts from assumptions.
- Do not authorize or execute payments.
- Human approval is required before any purchase.
"""


def generate_procurement_insights(procurement, analysis):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)

    procurement_data = {
        "title": procurement.title,
        "description": procurement.description,
        "budget": str(procurement.budget_amount),
        "currency": procurement.currency,
        "supplier_analysis": analysis
    }

    prompt = f"""
You are preparing a professional procurement decision report for a business manager.

Analyze ONLY the procurement data and calculated supplier analysis supplied below.

PROCUREMENT DATA:
{json.dumps(procurement_data, indent=2)}

FOLLOW THESE RULES:
- Preserve the supplied supplier rankings and numerical scores exactly.
- Never calculate alternative rankings or change the scoring methodology.
- Use actual prices, specifications, delivery days and budget figures.
- Never invent supplier credentials, warranties, availability or verification.
- Clearly distinguish supplied facts from missing information.
- Explain trade-offs rather than automatically choosing the cheapest supplier.
- Mention that product specifications are not independently verified.
- AI provides recommendations only. Human approval is mandatory before payment.
- Do not claim that AI authorizes, initiates or executes payments.

WRITE THE REPORT USING THESE MARKDOWN SECTIONS:

# Procurement Decision Report

## 1. Executive Summary
Summarize the procurement requirement, number of quotations,
recommended supplier and the main reason for the recommendation.

## 2. Supplier Ranking
Provide a Markdown table containing:
Rank | Supplier | Total Price | Delivery Days | Score | Budget Remaining

Use the exact ranking and figures from the supplied analysis.

## 3. Supplier Comparison
Compare each supplier's quoted specifications, price and delivery.
Explain meaningful differences between the quotations.

## 4. Price and Quality Trade-offs
Explain the advantages and disadvantages of each quotation.
Explain why the highest-ranked supplier offers the best weighted value
according to the supplied scoring methodology.

## 5. Procurement Risk Assessment
Discuss the actual risks supplied by the scoring analysis.
Identify missing information that should be verified before purchasing.

## 6. Budget Impact
Show the approved budget, recommended quotation amount,
budget utilization percentage and remaining budget.
Use the actual figures from the supplied data.

## 7. Final Recommendation
State the recommended supplier and its calculated score.
Explain the recommendation using evidence from the quotations.

## 8. Human Approval and Payment Controls
Clearly state that the recommendation is advisory.
A human must explicitly approve the quotation before PayPal payment.
Payment completion must be confirmed by PayPal.

Write a complete, informative report for a procurement manager.
Avoid generic filler. Do not omit sections.
"""



    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=3500
            )
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        candidates = response.candidates or []
        finish_reason = candidates[0].finish_reason if candidates else None

        if finish_reason == types.FinishReason.MAX_TOKENS:
            raise RuntimeError(
                "Gemini report was truncated by the output-token limit."
            )

        report = response.text.strip()

        required_sections = [
            "1. Executive Summary",
            "2. Supplier Ranking",
            "3. Supplier Comparison",
            "4. Price and Quality Trade-offs",
            "5. Procurement Risk Assessment",
            "6. Budget Impact",
            "7. Final Recommendation",
            "8. Human Approval and Payment Controls",
        ]

        missing_sections = [
            section for section in required_sections
            if section.lower() not in report.lower()
        ]

        if missing_sections:
            raise RuntimeError(
                "Gemini returned an incomplete report. Missing sections: "
                + ", ".join(missing_sections)
            )

        usage = response.usage_metadata

        return {
            "provider": "Google Gemini",
            "model": model,
            "report": report,
            "finish_reason": str(finish_reason),
            "token_usage": {
                "prompt_tokens": usage.prompt_token_count if usage else None,
                "response_tokens": usage.candidates_token_count if usage else None,
                "total_tokens": usage.total_token_count if usage else None,
            },
        }

    finally:
        client.close()
