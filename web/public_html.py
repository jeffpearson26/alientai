
# Public page HTML builders for AlientAI.
# Presentation-only module. No scanner calls, no trading, no account access.

from __future__ import annotations


def build_public_image_page_html(
    main_image_base64: str = "",
    extra_image_base64: str = "",
    ticker_analysis_enabled: bool = True,
) -> str:
    extra_html = ""

    if extra_image_base64:
        extra_html = (
            '<div class="image-wrap">'
            '<img class="public-image" src="data:image/png;base64,' + extra_image_base64 + '" '
            'alt="AlientAI supporting public image">'
            '</div>'
        )

    ticker_html = ""

    if ticker_analysis_enabled:
        ticker_html = '''
        <section class="ticker-card">
          <h2>Analyze a ticker</h2>
          <p>Public-safe research lookup placeholder. This section is read-only and does not buy, sell, expose balances, or change settings.</p>
          <div class="ticker-row">
            <input value="NVDA" aria-label="Ticker symbol">
            <button type="button">Analyze Ticker</button>
          </div>
          <p class="note">This module preview intentionally does not wire actions yet. The active page remains unchanged until the route refactor.</p>
        </section>
        '''

    if not main_image_base64:
        main_image_html = '''
        <section class="fallback">
          <h1>AlientAI Public Page Module</h1>
          <p>The public HTML module is loaded. Main image data was not supplied to this preview.</p>
        </section>
        '''
    else:
        main_image_html = (
            '<div class="image-wrap">'
            '<img class="public-image" src="data:image/png;base64,' + main_image_base64 + '" '
            'alt="AlientAI public dashboard">'
            '</div>'
        )

    return '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AlientAI</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      min-height: 100%;
      background: #020617;
      color: #eaf6ff;
      font-family: Arial, Helvetica, sans-serif;
      overflow-x: hidden;
    }

    body {
      background: radial-gradient(circle at top, #071a2f 0%, #020617 55%, #01040c 100%);
    }

    .page-shell {
      width: 100%;
      max-width: 1600px;
      margin: 0 auto;
    }

    .image-stack {
      display: flex;
      flex-direction: column;
      gap: 12px;
      align-items: center;
      width: 100%;
    }

    .image-wrap {
      width: 100%;
    }

    .public-image {
      display: block;
      width: 100%;
      max-width: 100%;
      height: auto;
      object-fit: contain;
      user-select: none;
      -webkit-user-drag: none;
    }

    .ticker-card,
    .fallback {
      width: min(1180px, calc(100% - 24px));
      margin: 12px auto;
      padding: 18px;
      border-radius: 24px;
      border: 1px solid rgba(94,234,212,.24);
      background: linear-gradient(180deg, rgba(8,18,34,.86), rgba(2,6,23,.84));
      box-shadow: 0 22px 70px rgba(0,0,0,.42);
    }

    .ticker-card h2,
    .fallback h1 {
      margin: 0 0 8px;
    }

    .ticker-card p,
    .fallback p,
    .note {
      color: #9fb6cf;
      line-height: 1.55;
    }

    .ticker-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      margin-top: 12px;
    }

    input {
      padding: 15px 16px;
      border-radius: 16px;
      border: 1px solid rgba(94,234,212,.26);
      background: rgba(2,6,23,.72);
      color: #eef7ff;
      font-size: 18px;
      text-transform: uppercase;
    }

    button {
      padding: 15px 20px;
      border-radius: 16px;
      border: 1px solid rgba(94,234,212,.34);
      background: linear-gradient(135deg, rgba(94,234,212,.26), rgba(96,165,250,.20));
      color: #ecfeff;
      font-weight: 900;
      font-size: 15px;
    }

    @media (max-width: 780px) {
      .ticker-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>

<!-- V164_ORBITAL_SATELLITE START -->
<style>
.v164-orbital-banner {
  max-width: 1180px;
  margin: 18px auto 30px auto;
  padding: 0 16px;
}

.v164-orbital-shell {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  align-items: center;
  gap: 24px;
  padding: 26px;
  border-radius: 30px;
  background:
    radial-gradient(circle at 18% 18%, rgba(0, 229, 255, 0.18), transparent 30%),
    radial-gradient(circle at 80% 22%, rgba(76, 125, 255, 0.16), transparent 28%),
    linear-gradient(135deg, rgba(5, 18, 40, 0.95), rgba(7, 28, 64, 0.92));
  border: 1px solid rgba(96, 165, 250, 0.28);
  box-shadow:
    0 18px 48px rgba(2, 10, 28, 0.45),
    inset 0 0 0 1px rgba(255, 255, 255, 0.03);
  overflow: hidden;
  position: relative;
}

.v164-orbital-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, transparent 0%, rgba(94, 234, 212, 0.05) 50%, transparent 100%);
  pointer-events: none;
}

.v164-orbital-copy {
  position: relative;
  z-index: 2;
}

.v164-orbital-kicker {
  display: inline-block;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(94, 234, 212, 0.32);
  color: #89f7ff;
  font-size: 0.82rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 14px;
}

.v164-orbital-title {
  margin: 0 0 12px 0;
  line-height: 1.05;
  font-size: clamp(2rem, 4.2vw, 3.35rem);
  font-weight: 800;
  color: #f4fbff;
  text-shadow: 0 0 18px rgba(96, 165, 250, 0.16);
}

.v164-orbital-title .accent {
  color: #63c8ff;
}

.v164-orbital-desc {
  margin: 0;
  max-width: 640px;
  color: rgba(226, 241, 255, 0.88);
  font-size: 1rem;
  line-height: 1.7;
}

.v164-orbital-pills {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.v164-orbital-pill {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(96, 165, 250, 0.24);
  background: rgba(12, 26, 58, 0.58);
  color: #d8ecff;
  font-size: 0.88rem;
  white-space: nowrap;
}

.v164-orbital-stage {
  position: relative;
  width: min(430px, 84vw);
  aspect-ratio: 1 / 1;
  margin: 0 auto;
  display: grid;
  place-items: center;
}

.v164-orbital-stage::before {
  content: "";
  position: absolute;
  inset: 4%;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(59, 130, 246, 0.12) 0%, rgba(14, 165, 233, 0.08) 35%, transparent 72%);
  filter: blur(14px);
}

.v164-grid-glow {
  position: absolute;
  inset: 7%;
  border-radius: 50%;
  background:
    repeating-linear-gradient(
      90deg,
      rgba(96, 165, 250, 0.06) 0px,
      rgba(96, 165, 250, 0.06) 1px,
      transparent 1px,
      transparent 18px
    ),
    repeating-linear-gradient(
      0deg,
      rgba(94, 234, 212, 0.05) 0px,
      rgba(94, 234, 212, 0.05) 1px,
      transparent 1px,
      transparent 18px
    );
  opacity: 0.35;
  filter: blur(0.4px);
  pointer-events: none;
}

.v164-globe {
  position: relative;
  width: 68%;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(162, 236, 255, 0.98), rgba(41, 148, 255, 0.88) 30%, rgba(9, 50, 128, 0.96) 60%, rgba(3, 10, 24, 1) 100%);
  box-shadow:
    0 0 24px rgba(56, 189, 248, 0.34),
    0 0 72px rgba(59, 130, 246, 0.22),
    inset -16px -18px 34px rgba(1, 8, 20, 0.5),
    inset 10px 10px 22px rgba(255, 255, 255, 0.12);
  overflow: hidden;
  animation: v164GlobePulse 5.8s ease-in-out infinite;
}

.v164-globe::before,
.v164-globe::after {
  content: "";
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(184, 232, 255, 0.28);
}

.v164-globe::before {
  inset: 12% 6%;
}

.v164-globe::after {
  inset: 30% 8%;
}

.v164-lat {
  position: absolute;
  left: 8%;
  right: 8%;
  height: 1px;
  background: rgba(202, 238, 255, 0.34);
}

.v164-lat.lat1 { top: 30%; }
.v164-lat.lat2 { top: 50%; }
.v164-lat.lat3 { top: 70%; }

.v164-long {
  position: absolute;
  top: 8%;
  bottom: 8%;
  width: 1px;
  background: rgba(202, 238, 255, 0.25);
}

.v164-long.long1 { left: 35%; }
.v164-long.long2 { left: 50%; }
.v164-long.long3 { left: 65%; }

.v164-orbit-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  animation: v164OrbitSpin 14s linear infinite;
}

.v164-orbit-ring::before {
  content: "";
  position: absolute;
  inset: 8%;
  border-radius: 50%;
  border: 1px solid rgba(123, 211, 255, 0.28);
  box-shadow: 0 0 20px rgba(96, 165, 250, 0.10);
}

.v164-orbit-ring.v164-orbit-two {
  animation-duration: 22s;
  animation-direction: reverse;
  transform: scale(0.88);
  opacity: 0.55;
}

.v164-orbit-ring.v164-orbit-two::before {
  inset: 16%;
  border-color: rgba(94, 234, 212, 0.18);
}

.v164-satellite {
  position: absolute;
  top: 8%;
  left: 50%;
  width: 34px;
  height: 34px;
  transform: translateX(-50%);
  filter: drop-shadow(0 0 10px rgba(148, 220, 255, 0.5));
}

.v164-sat-body {
  position: absolute;
  top: 11px;
  left: 11px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(180deg, #eefbff, #90d9ff);
  box-shadow: 0 0 12px rgba(125, 211, 252, 0.75);
}

.v164-sat-wing {
  position: absolute;
  top: 15px;
  width: 10px;
  height: 2px;
  background: rgba(213, 240, 255, 0.96);
  box-shadow: 0 0 8px rgba(125, 211, 252, 0.35);
}

.v164-sat-wing.left { left: 0; }
.v164-sat-wing.right { right: 0; }

.v164-sat-antenna {
  position: absolute;
  left: 16px;
  top: 2px;
  width: 2px;
  height: 10px;
  background: rgba(213, 240, 255, 0.9);
  border-radius: 999px;
}

.v164-dot {
  position: absolute;
  top: 14%;
  left: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translateX(-50%);
  background: rgba(94, 234, 212, 0.9);
  box-shadow: 0 0 10px rgba(94, 234, 212, 0.55);
}

@keyframes v164OrbitSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes v164GlobePulse {
  0%, 100% {
    transform: scale(1);
    box-shadow:
      0 0 24px rgba(56, 189, 248, 0.34),
      0 0 72px rgba(59, 130, 246, 0.22),
      inset -16px -18px 34px rgba(1, 8, 20, 0.5),
      inset 10px 10px 22px rgba(255, 255, 255, 0.12);
  }
  50% {
    transform: scale(1.018);
    box-shadow:
      0 0 32px rgba(56, 189, 248, 0.42),
      0 0 92px rgba(59, 130, 246, 0.28),
      inset -16px -18px 34px rgba(1, 8, 20, 0.45),
      inset 10px 10px 22px rgba(255, 255, 255, 0.16);
  }
}

@media (max-width: 900px) {
  .v164-orbital-shell {
    grid-template-columns: 1fr;
    padding: 22px 18px;
  }

  .v164-orbital-copy {
    text-align: center;
  }

  .v164-orbital-pills {
    justify-content: center;
  }
}

@media (max-width: 540px) {
  .v164-orbital-banner {
    margin-top: 12px;
    padding: 0 10px;
  }

  .v164-orbital-shell {
    border-radius: 22px;
    gap: 16px;
    padding: 18px 14px;
  }

  .v164-orbital-title {
    font-size: clamp(1.55rem, 7.2vw, 2.2rem);
  }

  .v164-orbital-desc {
    font-size: 0.95rem;
    line-height: 1.6;
  }
}
</style>

<section class="v164-orbital-banner" aria-label="Animated orbital hero visual">
  <div class="v164-orbital-shell">
    <div class="v164-orbital-copy">
      <div class="v164-orbital-kicker">Global Signal Network</div>
      <h2 class="v164-orbital-title">
        AI market research with a <span class="accent">live orbital visual</span>
      </h2>
      <p class="v164-orbital-desc">
        AlientAI studies price behavior, trend structure, replay-trained model scoring,
        sector intelligence, and risk-aware signal quality. This animated orbital globe
        is a public-facing visual metaphor for always-on market monitoring, machine-learning
        research, and cross-sector signal discovery.
      </p>
      <div class="v164-orbital-pills">
        <span class="v164-orbital-pill">Live scanner research</span>
        <span class="v164-orbital-pill">Replay-trained V84 model</span>
        <span class="v164-orbital-pill">Sector intelligence lanes</span>
        <span class="v164-orbital-pill">Public-safe presentation</span>
      </div>
    </div>

    <div class="v164-orbital-stage">
      <div class="v164-grid-glow"></div>

      <div class="v164-globe">
        <div class="v164-lat lat1"></div>
        <div class="v164-lat lat2"></div>
        <div class="v164-lat lat3"></div>

        <div class="v164-long long1"></div>
        <div class="v164-long long2"></div>
        <div class="v164-long long3"></div>
      </div>

      <div class="v164-orbit-ring v164-orbit-one">
        <div class="v164-satellite">
          <div class="v164-sat-body"></div>
          <div class="v164-sat-wing left"></div>
          <div class="v164-sat-wing right"></div>
          <div class="v164-sat-antenna"></div>
        </div>
      </div>

      <div class="v164-orbit-ring v164-orbit-two">
        <div class="v164-dot"></div>
      </div>
    </div>
  </div>
</section>
<!-- V164_ORBITAL_SATELLITE END -->


  <main class="page-shell">
    <div class="image-stack">
      ''' + main_image_html + ticker_html + extra_html + '''
    </div>
  </main>
</body>
</html>'''
