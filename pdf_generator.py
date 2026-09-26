"""PitchRoast PDF Generator — Executive Satirical Term Sheet & Committee Report.

Generates crisp, professional executive PDFs using fpdf2, suitable for downloading
from the Founder Hot Seat, the Syndicate Observatory, or the presentation deck.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from fpdf import FPDF

if TYPE_CHECKING:
    from syndicate import SyndicateResult


def _clean(text: str) -> str:
    """Sanitize unicode so text renders cleanly in standard PDF fonts."""
    if not text:
        return ""
    replacements = {
        "™": " (TM)",
        "®": " (R)",
        "©": " (C)",
        "•": "-",
        "“": '"',
        "”": '"',
        "‘": "'",  # noqa: RUF001
        "’": "'",  # noqa: RUF001
        "—": " - ",
        "–": " - ",  # noqa: RUF001
        "…": "...",
        "☕": "[Coffee]",
        "💳": "[Klarna]",
        "🤖": "[AI]",
        "🦈": "[Shark]",
        "🔥": "[Fire]",
        "🕶️": "[Market]",
        "💰": "[Finance]",
        "💻": "[Tech]",
        "🎯": "[Founder]",
        "🔬": "[Admin]",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class PitchRoastPDF(FPDF):
    def header(self):
        # Dark executive header bar
        self.set_fill_color(11, 17, 32)  # #0B1120
        self.rect(0, 0, 210, 22, "F")

        self.set_font("Helvetica", "B", 12)
        self.set_text_color(251, 146, 60)  # orange #FB923C
        self.set_xy(10, 6)
        self.cell(190, 5, "PITCHROAST (TM) VENTURE COMMITTEE")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(148, 163, 184)  # slate #94A3B8
        self.set_xy(10, 12)
        self.cell(190, 5, "Autonomous AI Investment Syndicate | Claude Community Stockholm")

        self.set_draw_color(36, 49, 77)
        self.line(0, 22, 210, 22)
        self.set_y(26)
        self.set_x(self.l_margin)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(36, 49, 77)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(148, 163, 184)
        self.cell(
            0,
            8,
            "Confidential & Satirical | Powered by Anthropic Claude (Opus 5.5 & Fable 5.1) | Page "
            + str(self.page_no()),
            align="C",
        )


def generate_term_sheet_pdf(result: SyndicateResult) -> bytes:
    """Generate a stylized, official PitchRoast investment verdict and term sheet PDF."""
    pdf = PitchRoastPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    w = pdf.epw

    # --- Title Banner ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 8, "INVESTMENT COMMITTEE VERDICT & SATIRICAL TERM SHEET")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    session = result.session_id or "live-demo"
    pdf.cell(w, 4, f"Evaluation Session: #{session} | Model Tier: {result.model}")
    pdf.ln(6)

    # --- Pitch Box ---
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(w, 5, "TARGET STARTUP PITCH:")
    pdf.ln(5)

    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(51, 65, 85)
    pitch_text = _clean(result.pitch.strip())
    if len(pitch_text) > 300:
        pitch_text = pitch_text[:297] + "..."
    pdf.multi_cell(w, 4.5, f'"{pitch_text}"', border=1, fill=True)
    pdf.set_x(pdf.l_margin)
    pdf.ln(4)

    # --- Scorecard Matrix ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 5, "QUANTITATIVE SYNDICATE SCORECARD")
    pdf.ln(5)

    shark = result.shark
    delusion = f"{shark.delusion_index}%" if shark else "92%"
    moat = f"{shark.moat_score} / 10" if shark else "1 / 10"
    runway = f"{shark.runway_months} Mo" if shark else "2 Mo"
    val = _clean(shark.pre_money_val if shark else "42 SEK & cold kanelbulle")

    col_w = w / 4.0
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(100, 116, 139)

    pdf.cell(col_w, 5, "DELUSION INDEX", border="LTR", fill=True, align="C")
    pdf.cell(col_w, 5, "TRUE MOAT SCORE", border="LTR", fill=True, align="C")
    pdf.cell(col_w, 5, "SURVIVAL RUNWAY", border="LTR", fill=True, align="C")
    pdf.cell(col_w, 5, "PRE-MONEY VALUATION", border="LTR", fill=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(194, 65, 12)  # orange-red
    pdf.cell(col_w, 7, delusion, border="LBR", fill=True, align="C")
    pdf.cell(col_w, 7, moat, border="LBR", fill=True, align="C")
    pdf.cell(col_w, 7, runway, border="LBR", fill=True, align="C")

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(col_w, 7, val[:25], border="LBR", fill=True, align="C")
    pdf.ln(9)

    # --- Partner Critiques ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 5, "SPECIALIST COMMITTEE DEBATES")
    pdf.ln(5)

    for pr in result.partners:
        p = pr.partner
        v = pr.verdict
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(194, 65, 12)
        pdf.cell(w, 4, _clean(f"{p.name} - {p.title}"))
        pdf.ln(4)

        if v is not None:
            pdf.set_font("Helvetica", "I", 7.5)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(w, 4, _clean(f'Zinger: "{v.zinger}"'))
            pdf.ln(4)

            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(w, 4, _clean(v.critique))
            pdf.set_x(pdf.l_margin)
        else:
            pdf.set_font("Helvetica", "I", 7.5)
            pdf.cell(w, 4, "[Recused or No Verdict]")
            pdf.ln(4)
        pdf.ln(2)

    # --- Term Sheet & Covenants ---
    if shark and shark.term_sheet:
        ts = shark.term_sheet
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w, 5, "OFFICIAL NON-BINDING TERM SHEET")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(col_w * 1.3, 4, _clean(f"Valuation: {ts.valuation}"))
        pdf.cell(col_w * 1.3, 4, _clean(f"Investment: {ts.investment_amount}"))
        pdf.cell(col_w * 1.4, 4, _clean(f"Liquidation: {ts.liquidation_pref}"))
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w, 4, "MANDATORY FOUNDER COVENANTS:")
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(51, 65, 85)
        for idx, cov in enumerate(ts.covenants, 1):
            pdf.multi_cell(w, 3.8, f"  {idx}. {_clean(cov)}")
            pdf.set_x(pdf.l_margin)

        pdf.ln(2)
        # The 1% Pivot
        pdf.set_fill_color(254, 243, 199)  # amber 100
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(180, 83, 9)
        pdf.cell(w, 4.5, " THE 1% PIVOT (THE ACTIONABLE PART):", fill=True)
        pdf.ln(4.5)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(69, 26, 3)
        pdf.multi_cell(w, 4, f" {_clean(shark.the_pivot)}", fill=True)
        pdf.set_x(pdf.l_margin)
        pdf.ln(2)

        # Closing Line
        pdf.set_font("Helvetica", "BI", 8.5)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(w, 4.5, _clean(f'Managing Partner Final Word: "{shark.closing_line}"'))
        pdf.set_x(pdf.l_margin)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def generate_sample_pitch_deck_pdf(name: str, pitch_title: str, bullets: list[str]) -> bytes:
    """Generate a clean 1-page sample pitch deck PDF."""
    pdf = PitchRoastPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    w = pdf.epw

    # Cover style slide
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 12, _clean(pitch_title), align="C")
    pdf.ln(12)

    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(194, 65, 12)
    pdf.cell(w, 8, _clean(f"Startup Pitch Submission - {name}"), align="C")
    pdf.ln(10)

    # Bullet points card
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(18, 46, 260, 130, "DF")

    pdf.set_xy(26, 52)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(240, 8, "EXECUTIVE SUMMARY & PROBLEM STATEMENT:")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    for b in bullets:
        pdf.set_x(28)
        pdf.multi_cell(235, 6, f"- {_clean(b)}")
        pdf.set_x(pdf.l_margin)
        pdf.ln(1)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


SAMPLE_DECKS: dict[str, dict[str, Any]] = {
    "☕ FikaSync Compliance": {
        "title": "FikaSync: Autonomous Swedish Fika Compliance Agent",
        "name": "FikaSync Technologies AB",
        "bullets": [
            "Problem: Software engineers in Stockholm are pushing git commits during statutory 10:00 and 15:00 fika hours, violating Swedish collective bargaining agreements.",
            "Solution: Autonomous agent intercepts GitHub webhooks and Slack events; revokes AWS IAM credentials and locks VS Code if a developer codes without a certified kanelbulle.",
            "Market Size: 45,000 Nordic tech companies bound by Union collective agreements.",
            "Business Model: Enterprise SaaS at 89 SEK per engineer/month. Seamless integration with Swedish Work Environment Authority (Arbetsmiljöverket).",
            "Defensibility: Proprietary Kanelbulle-Vision neural network running on edge espresso machines.",
        ],
    },
    "💳 Klarna for Regret": {
        "title": "Klarna for Regret: Buy Now, Suffer Later",
        "name": "Remorse Financial AB",
        "bullets": [
            "Problem: Impulsive 3 AM decisions, 95 SEK oat cortados in Södermalm, and joining doomed Web3 startups leave tech founders with crippling immediate shame.",
            "Solution: Swedish Open Banking protocol amortizing acute emotional regret into 4 interest-free, guilt-deferred installments over 60 days.",
            "Market Size: $4.2 Trillion global emotional debt and impulsive lifestyle transactions.",
            "Business Model: Remorse-as-a-Service (RaaS) with 2.8% interchange + guilt rollover penalties.",
            "Traction: 12,000 Stockholm millennial beta testers amortizing their weekend Uber receipts.",
        ],
    },
    "🤖 AI Standup Bot": {
        "title": "AI Standup Bot: Autonomous Scrum Attendance",
        "name": "StandupSync AI Inc.",
        "bullets": [
            "Problem: Daily 9:30 AM standups disrupt deep developer flow with meaningless status updates and awkward Zoom silences.",
            "Solution: Hyper-realistic AI avatar that joins Zoom/Teams calls, sighs periodically, looks at a second monitor, and says 'I am blocked by the infrastructure backend' whenever called upon.",
            "Market Size: 28 Million software engineers globally enduring 15 minutes of standup daily.",
            "Business Model: B2B SaaS priced at $49/engineer/month with Slack and Jira blocker integrations.",
        ],
    },
    "☕ Oat Milk Web3": {
        "title": "OatFi: Decentralized Oat Milk Consensus",
        "name": "OatFi Protocol",
        "bullets": [
            "Problem: Centralized oat milk production lacks cryptographic provenance and decentralized barista governance.",
            "Solution: Countertop espresso machines that roast small-batch Nordic oat milk using on-chain temperature consensus. Users stake OAT tokens for latte art NFTs.",
            "Market Size: $400B addressable global beverage and specialty coffee market.",
            "Business Model: 1.5% protocol fee per oat froth transaction + yield farming liquidity pools.",
        ],
    },
}


def get_sample_deck_pdf(key: str) -> bytes:
    """Retrieve or generate sample pitch deck PDF for preset."""
    deck = SAMPLE_DECKS.get(key) or SAMPLE_DECKS["☕ FikaSync Compliance"]
    return generate_sample_pitch_deck_pdf(deck["name"], deck["title"], deck["bullets"])
