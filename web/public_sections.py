
"""Reusable public-page sections for AlientAI.

Presentation-only module.
No scanner execution, no trading, no account access, no private controls.
"""

from __future__ import annotations


DEFAULT_CREDIT = "Developed with GPT-5.5 Thinking and JEP26"


def credit_note_html(credit: str = DEFAULT_CREDIT) -> str:
    html = """
    <div class="public-credit-note">
      __CREDIT__
    </div>
    <style>
      .public-credit-note {
        width: min(1180px, calc(100% - 24px));
        margin: 12px auto 20px;
        padding: 12px 14px;
        border-radius: 16px;
        border: 1px solid rgba(94,234,212,.18);
        background: rgba(2,6,23,.72);
        color: rgba(226,246,255,.82);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 13px;
        line-height: 1.45;
        text-align: center;
        letter-spacing: .2px;
        box-shadow: 0 16px 40px rgba(0,0,0,.25);
      }
    </style>
    """
    return html.replace("__CREDIT__", credit)


def sector_intelligence_board_html(
    ai_count: int = 47,
    healthcare_count: int = 64,
    energy_count: int = 81,
    sequential_count: int = 2209,
    credit: str = DEFAULT_CREDIT,
) -> str:
    html = """
    <section class="public-sector-board">
      <div class="public-section-header">
        <p class="public-eyebrow">Public Research Layer</p>
        <h2>Sector Intelligence Board</h2>
        <p>
          AlientAI monitors multiple market universes as separate research lanes so signal quality,
          momentum, and risk behavior can be studied by sector instead of blended into one noisy list.
        </p>
      </div>

      <div class="public-sector-grid">
        <article class="public-card">
          <span class="public-icon">AI</span>
          <h3>AI / Semiconductors</h3>
          <p>High-beta artificial intelligence, semiconductor, chip equipment, and related momentum names.</p>
          <strong>__AI_COUNT__ symbols</strong>
        </article>

        <article class="public-card">
          <span class="public-icon">HC</span>
          <h3>Healthcare</h3>
          <p>Pharma, biotech, devices, diagnostics, services, and healthcare ETF research lanes.</p>
          <strong>__HEALTHCARE_COUNT__ symbols</strong>
        </article>

        <article class="public-card">
          <span class="public-icon">EN</span>
          <h3>Energy</h3>
          <p>Oil, gas, E&amp;P, services, refiners, uranium, nuclear, clean power, coal, and ETFs.</p>
          <strong>__ENERGY_COUNT__ symbols</strong>
        </article>

        <article class="public-card">
          <span class="public-icon">MC</span>
          <h3>Mega Cap Tech</h3>
          <p>Large technology leaders that often influence broad market direction and risk appetite.</p>
          <strong>Core watch</strong>
        </article>

        <article class="public-card">
          <span class="public-icon">ETF</span>
          <h3>ETF Monitors</h3>
          <p>Sector and index ETFs used for market regime, relative strength, and broad participation.</p>
          <strong>Market context</strong>
        </article>

        <article class="public-card public-card-highlight">
          <span class="public-icon">SEQ</span>
          <h3>All Selections Sequential</h3>
          <p>Scans each universe one lane at a time for sector-by-sector research comparison.</p>
          <strong>__SEQUENTIAL_COUNT__ unique</strong>
        </article>
      </div>

      <div class="public-disclaimer">
        Public research display only. No balances, account values, owner controls, or trade actions are shown. __CREDIT__
      </div>
    </section>
    """

    html = html.replace("__AI_COUNT__", str(ai_count))
    html = html.replace("__HEALTHCARE_COUNT__", str(healthcare_count))
    html = html.replace("__ENERGY_COUNT__", str(energy_count))
    html = html.replace("__SEQUENTIAL_COUNT__", str(sequential_count))
    html = html.replace("__CREDIT__", credit)
    return html


def performance_snapshot_html(credit: str = DEFAULT_CREDIT) -> str:
    html = """
    <section class="public-performance-card">
      <div>
        <p class="public-eyebrow">Research Status</p>
        <h2>Under Active Development</h2>
        <p>
          AlientAI is building and stress-testing market-research models before making
          performance claims. This public page describes the research process, not live recommendations.
        </p>
      </div>

      <div class="public-win-orb">
        <span>R&amp;D</span>
        <small>Research in progress</small>
      </div>

      <div class="public-metric-grid">
        <div><label>Horizon</label><strong>5-day research</strong></div>
        <div><label>Methods</label><strong>ML &amp; neural models</strong></div>
        <div><label>Inputs</label><strong>Price, volume &amp; public events</strong></div>
        <div><label>Validation</label><strong>Chronological holdouts</strong></div>
        <div class="wide"><label>Goal</label><strong>Rare, high-quality research candidates</strong></div>
        <div class="wide"><label>Safety policy</label><strong>No public trade execution</strong></div>
      </div>

      <div class="public-disclaimer">
        Paper simulation only · Research display only · Not financial advice · __CREDIT__
      </div>
    </section>
    """

    html = html.replace("__CREDIT__", credit)
    return html


def ai_research_architecture_html(credit: str = DEFAULT_CREDIT) -> str:
    html = """
    <section class="public-ai-research">
      <div class="public-section-header">
        <p class="public-eyebrow">AI Research Architecture</p>
        <h2>The intelligence layer behind AlientAI</h2>
        <p>
          AlientAI combines live scanner observations, replay-trained machine learning,
          sector-specific universes, risk filters, and paper-trade feedback to study whether
          market setups have repeatable predictive value.
        </p>
      </div>

      <div class="public-flow-grid">
        <article><span>01</span><h3>Live Scanner Engine</h3><p>Reads quotes, movement, volume, spreads, trend context, and breakout quality.</p></article>
        <article><span>02</span><h3>Replay-Trained V84 Model</h3><p>Scores feature snapshots against replay-tested probability bands.</p></article>
        <article><span>03</span><h3>Risk and Safety Filters</h3><p>Blocks weak setups, wide spreads, low liquidity, danger-chase conditions, and inverse candidates.</p></article>
        <article><span>04</span><h3>Sector Intelligence</h3><p>Compares behavior across AI/semis, healthcare, energy, ETFs, and other market lanes.</p></article>
        <article><span>05</span><h3>Paper-Trade Feedback</h3><p>Grades outcomes so win percentage and scanner direction can be studied over time.</p></article>
        <article class="highlight"><span>06</span><h3>Future Transformer Sidecar</h3><p>Planned sequence model to study recent candle patterns as a challenger to V84.</p></article>
      </div>

      <div class="public-disclaimer">
        Experimental AI research platform · Public-safe design · __CREDIT__
      </div>
    </section>
    """
    return html.replace("__CREDIT__", credit)


def research_timeline_html(credit: str = DEFAULT_CREDIT) -> str:
    html = """
    <section class="public-timeline">
      <div class="public-section-header">
        <p class="public-eyebrow">Research Timeline</p>
        <h2>From scanner prototype to AI market-intelligence platform</h2>
        <p>
          AlientAI is being developed from live scanning into replay-tested machine learning,
          sector intelligence, public-safe presentation, and professional modular architecture.
        </p>
      </div>

      <div class="public-flow-grid">
        <article><span>Phase 01</span><h3>Live scanner foundation</h3><p>Core loop for quotes, movement, liquidity, spreads, trend context, and signals.</p></article>
        <article><span>Phase 02</span><h3>Paper-trade safety layer</h3><p>Paper-only execution, stop logic, cooldowns, and whole-share sizing.</p></article>
        <article><span>Phase 03</span><h3>Replay-trained V84 model</h3><p>Historical feature snapshots tested against future outcomes.</p></article>
        <article><span>Phase 04</span><h3>Sector universe expansion</h3><p>AI/semis, healthcare, energy, ETF, and sequential research lanes.</p></article>
        <article><span>Phase 05</span><h3>Professional refactor</h3><p>Modules for universes, paper sizing, web presentation, broker integrations, routes, ML, and tests.</p></article>
        <article class="highlight"><span>Roadmap</span><h3>Transformer sequence sidecar</h3><p>Research-only challenger model for candle-pattern sequence learning.</p></article>
      </div>

      <div class="public-architecture-strip">
        <strong>Scanner</strong><span>→</span><strong>Features</strong><span>→</span><strong>V84</strong><span>→</span><strong>Risk Gate</strong><span>→</span><strong>Paper Feedback</strong>
      </div>

      <div class="public-disclaimer">
        Experimental AI market research · Paper simulation only · __CREDIT__
      </div>
    </section>
    """
    return html.replace("__CREDIT__", credit)


def public_sections_css() -> str:
    return """
    <style>
      .public-sector-board,
      .public-performance-card,
      .public-ai-research,
      .public-timeline {
        width: min(1180px, calc(100% - 24px));
        margin: 14px auto 18px;
        padding: 24px;
        border-radius: 30px;
        border: 1px solid rgba(94,234,212,.22);
        background:
          radial-gradient(circle at top left, rgba(94,234,212,.12), transparent 36%),
          radial-gradient(circle at bottom right, rgba(96,165,250,.14), transparent 38%),
          linear-gradient(180deg, rgba(8,18,34,.92), rgba(2,6,23,.92));
        box-shadow: 0 30px 95px rgba(0,0,0,.48);
        color: #eaf6ff;
        font-family: Arial, Helvetica, sans-serif;
      }

      .public-section-header {
        max-width: 920px;
        margin-bottom: 20px;
      }

      .public-eyebrow {
        margin: 0 0 7px;
        color: #5eead4;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .18em;
        text-transform: uppercase;
      }

      .public-section-header h2,
      .public-performance-card h2 {
        margin: 0 0 10px;
        font-size: clamp(28px, 4.4vw, 52px);
        line-height: 1.02;
        letter-spacing: -1.2px;
      }

      .public-section-header p,
      .public-performance-card p {
        margin: 0;
        color: #a8bdd6;
        line-height: 1.58;
        font-size: 15px;
      }

      .public-sector-grid,
      .public-flow-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 14px;
      }

      .public-card,
      .public-flow-grid article,
      .public-metric-grid div {
        padding: 18px;
        border-radius: 22px;
        border: 1px solid rgba(148,163,184,.16);
        background: linear-gradient(180deg, rgba(15,23,42,.76), rgba(2,6,23,.62));
      }

      .public-card-highlight,
      .public-flow-grid article.highlight {
        border-color: rgba(167,139,250,.34);
        background:
          radial-gradient(circle at top right, rgba(167,139,250,.14), transparent 42%),
          linear-gradient(180deg, rgba(15,23,42,.80), rgba(2,6,23,.64));
      }

      .public-icon,
      .public-flow-grid article span {
        display: inline-grid;
        place-items: center;
        min-width: 40px;
        height: 40px;
        padding: 0 10px;
        border-radius: 15px;
        border: 1px solid rgba(94,234,212,.28);
        background: rgba(94,234,212,.10);
        color: #ccfbf1;
        font-weight: 950;
        font-size: 12px;
        margin-bottom: 14px;
      }

      .public-card h3,
      .public-flow-grid h3 {
        margin: 0 0 8px;
        font-size: 20px;
      }

      .public-card p,
      .public-flow-grid p {
        margin: 0;
        color: #9fb6cf;
        line-height: 1.5;
        font-size: 14px;
      }

      .public-card strong {
        display: block;
        margin-top: 14px;
        color: #f8fbff;
      }

      .public-performance-card {
        display: grid;
        grid-template-columns: 1.2fr 280px;
        gap: 18px;
        align-items: center;
      }

      .public-win-orb {
        width: 230px;
        height: 230px;
        justify-self: center;
        border-radius: 999px;
        display: grid;
        place-items: center;
        text-align: center;
        border: 1px solid rgba(52,211,153,.32);
        background:
          radial-gradient(circle, rgba(52,211,153,.18), rgba(14,165,233,.08) 58%, rgba(2,6,23,.72) 72%);
      }

      .public-win-orb span {
        font-size: 48px;
        font-weight: 950;
        color: #ecfdf5;
      }

      .public-win-orb small {
        color: #a7f3d0;
        text-transform: uppercase;
        letter-spacing: .08em;
        font-weight: 850;
      }

      .public-metric-grid {
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
      }

      .public-metric-grid .wide {
        grid-column: span 2;
      }

      .public-metric-grid label {
        display: block;
        color: #8aa2bd;
        font-size: 12px;
        margin-bottom: 7px;
        text-transform: uppercase;
        letter-spacing: .07em;
      }

      .public-metric-grid strong {
        display: block;
        color: #f8fbff;
        font-size: 22px;
      }

      .public-architecture-strip {
        display: grid;
        grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr auto 1fr;
        gap: 10px;
        align-items: center;
        margin-top: 16px;
        padding: 14px;
        border-radius: 20px;
        border: 1px solid rgba(94,234,212,.18);
        background: rgba(2,6,23,.46);
        text-align: center;
      }

      .public-architecture-strip span {
        color: #5eead4;
        font-weight: 900;
      }

      .public-disclaimer {
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 16px;
        border: 1px solid rgba(148,163,184,.14);
        background: rgba(2,6,23,.44);
        color: #9fb6cf;
        font-size: 13px;
        line-height: 1.5;
        text-align: center;
      }

      @media (max-width: 980px) {
        .public-sector-grid,
        .public-flow-grid {
          grid-template-columns: repeat(2, 1fr);
        }

        .public-performance-card {
          grid-template-columns: 1fr;
        }

        .public-metric-grid {
          grid-template-columns: repeat(2, 1fr);
        }

        .public-architecture-strip {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 620px) {
        .public-sector-board,
        .public-performance-card,
        .public-ai-research,
        .public-timeline {
          width: calc(100% - 20px);
          padding: 16px;
          border-radius: 22px;
        }

        .public-sector-grid,
        .public-flow-grid,
        .public-metric-grid {
          grid-template-columns: 1fr;
        }

        .public-metric-grid .wide {
          grid-column: span 1;
        }

        .public-win-orb {
          width: 190px;
          height: 190px;
        }

        .public-win-orb span {
          font-size: 38px;
        }
      }
    </style>
    """


def assemble_public_enhancement_sections(
    ai_count: int = 47,
    healthcare_count: int = 64,
    energy_count: int = 81,
    sequential_count: int = 2209,
    credit: str = DEFAULT_CREDIT,
) -> str:
    return (
        public_sections_css()
        + ai_research_architecture_html(credit=credit)
        + research_timeline_html(credit=credit)
        + sector_intelligence_board_html(
            ai_count=ai_count,
            healthcare_count=healthcare_count,
            energy_count=energy_count,
            sequential_count=sequential_count,
            credit=credit,
        )
        + performance_snapshot_html(credit=credit)
        + credit_note_html(credit=credit)
    )
