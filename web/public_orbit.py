"""Public orbit/satellite visuals for AlientAI.

Presentation-only module.
No scanner execution, trading, account access, Schwab access, dashboard controls, or ML scoring.
"""

from __future__ import annotations

ORBIT_SPEED_SECONDS = 92


def hero_satellite_overlay_html() -> str:
    return r'''
    <div class="v167-back-orbit v167-orbit-layer" aria-hidden="true">
      <div class="v167-orbit-track"></div>
      <div class="v167-satellite-node">
        <div class="v167-sat-trail"></div>
        <div class="v167-sat-body"></div>
        <div class="v167-sat-wing left"></div>
        <div class="v167-sat-wing right"></div>
        <div class="v167-sat-antenna"></div>
      </div>
    </div>

    <div class="v167-front-orbit v167-orbit-layer" aria-hidden="true">
      <div class="v167-orbit-track"></div>
      <div class="v167-satellite-node">
        <div class="v167-sat-trail"></div>
        <div class="v167-sat-body"></div>
        <div class="v167-sat-wing left"></div>
        <div class="v167-sat-wing right"></div>
        <div class="v167-sat-antenna"></div>
      </div>
    </div>

    <button class="v167-audio-control" type="button" id="v167AudioControl" aria-label="Enable low volume Sputnik-style beep">
      <span class="v167-audio-dot"></span>
      <span class="v167-audio-text">Enable Sputnik Beep</span>
    </button>

    <style id="v167-hero-satellite-css">
      .v167-hero-wrap { position: relative !important; overflow: hidden !important; }
      .v167-hero-wrap > img { display: block !important; width: 100% !important; height: auto !important; }

      .v167-planet-cover {
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        z-index: 9 !important;
        pointer-events: none !important;
        clip-path: circle(17.2% at 77.8% 36.3%);
      }

      .v167-orbit-layer {
        position: absolute;
        right: 5.5%;
        top: 19%;
        width: 34%;
        max-width: 430px;
        min-width: 180px;
        aspect-ratio: 1 / 1;
        border-radius: 999px;
        transform-origin: 50% 50%;
      }

      .v167-back-orbit {
        z-index: 8;
        animation: v167OrbitSpin 92s linear infinite, v167BackVisibility 92s linear infinite;
      }

      .v167-front-orbit {
        z-index: 10;
        animation: v167OrbitSpin 92s linear infinite, v167FrontVisibility 92s linear infinite;
      }

      .v167-orbit-track {
        position: absolute;
        inset: 8%;
        border-radius: 999px;
        border: 1px solid rgba(125, 211, 252, 0.34);
        box-shadow: 0 0 22px rgba(56, 189, 248, 0.12), inset 0 0 14px rgba(56, 189, 248, 0.05);
      }

      .v167-satellite-node {
        position: absolute;
        left: 50%;
        bottom: 6%;
        width: 42px;
        height: 42px;
        transform: translateX(-50%);
        filter: drop-shadow(0 0 12px rgba(148, 220, 255, 0.85)) drop-shadow(0 0 22px rgba(56, 189, 248, 0.28));
      }

      .v167-back-orbit .v167-satellite-node {
        opacity: 0.66;
        filter: blur(0.15px) drop-shadow(0 0 8px rgba(125, 211, 252, 0.45));
      }

      .v167-sat-body {
        position: absolute;
        top: 13px;
        left: 13px;
        width: 16px;
        height: 16px;
        border-radius: 999px;
        background: linear-gradient(180deg, #ffffff, #93dcff);
        box-shadow: 0 0 16px rgba(125, 211, 252, 0.90), inset 0 1px 0 rgba(255, 255, 255, 0.38);
      }

      .v167-sat-wing {
        position: absolute;
        top: 20px;
        width: 13px;
        height: 3px;
        border-radius: 999px;
        background: rgba(226, 247, 255, 0.98);
        box-shadow: 0 0 10px rgba(125, 211, 252, 0.48);
      }

      .v167-sat-wing.left { left: 0; }
      .v167-sat-wing.right { right: 0; }

      .v167-sat-antenna {
        position: absolute;
        left: 20px;
        top: 1px;
        width: 2px;
        height: 14px;
        border-radius: 999px;
        background: rgba(226, 247, 255, 0.96);
        box-shadow: 0 0 8px rgba(125, 211, 252, 0.45);
      }

      .v167-sat-trail {
        position: absolute;
        top: 20px;
        right: 34px;
        width: 36px;
        height: 2px;
        border-radius: 999px;
        background: linear-gradient(90deg, transparent, rgba(125, 211, 252, 0.85));
        filter: blur(0.2px);
      }

      .v167-audio-control {
        position: absolute;
        right: 2.2%;
        bottom: 2.8%;
        z-index: 12;
        pointer-events: auto;
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 8px 11px;
        border-radius: 999px;
        border: 1px solid rgba(125, 211, 252, 0.38);
        background: linear-gradient(180deg, rgba(8,18,34,.82), rgba(2,6,23,.72));
        color: rgba(238,247,255,.92);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 12px;
        font-weight: 850;
        cursor: pointer;
        box-shadow: 0 12px 34px rgba(0,0,0,.28), 0 0 20px rgba(56,189,248,.10);
        backdrop-filter: blur(8px);
      }

      .v167-audio-control:hover { border-color: rgba(94, 234, 212, .58); color: #ffffff; }

      .v167-audio-dot {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: rgba(148,163,184,.9);
        box-shadow: 0 0 10px rgba(148,163,184,.30);
      }

      .v167-audio-control.active .v167-audio-dot {
        background: #5eead4;
        box-shadow: 0 0 12px rgba(94,234,212,.85);
        animation: v167AudioPulse .8s linear infinite;
      }

      @keyframes v167OrbitSpin {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
      }

      @keyframes v167FrontVisibility {
        0%, 47%   { opacity: 1; }
        50%, 100% { opacity: 0; }
      }

      @keyframes v167BackVisibility {
        0%, 47%   { opacity: 0; }
        50%, 100% { opacity: 1; }
      }

      @keyframes v167AudioPulse {
        0%, 45% { opacity: 1; transform: scale(1); }
        46%, 100% { opacity: .35; transform: scale(.78); }
      }

      @media (max-width: 900px) {
        .v167-orbit-layer { right: 2%; top: 18%; width: 38%; min-width: 150px; }
        .v167-satellite-node { width: 34px; height: 34px; }
        .v167-sat-body { top: 10px; left: 10px; width: 14px; height: 14px; }
        .v167-sat-wing { top: 17px; width: 10px; }
        .v167-sat-antenna { left: 16px; height: 11px; }
        .v167-planet-cover { clip-path: circle(19% at 77.8% 35.8%); }
      }

      @media (max-width: 560px) {
        .v167-orbit-layer { right: 0%; top: 17%; width: 44%; min-width: 118px; }
        .v167-audio-control { right: 8px; bottom: 8px; padding: 7px 9px; font-size: 10.5px; }
        .v167-planet-cover { clip-path: circle(20.5% at 77.8% 35.2%); }
      }
    </style>

    <script id="v167-sputnik-beep-script">
      (function () {
        if (window.__v167SputnikOrbitInstalled) return;
        window.__v167SputnikOrbitInstalled = true;

        function ensurePlanetCover() {
          var wrap = document.querySelector('.v167-hero-wrap');
          if (!wrap) return;
          if (wrap.querySelector('.v167-planet-cover')) return;

          var heroImg = wrap.querySelector('img');
          if (!heroImg) return;

          var clone = heroImg.cloneNode(true);
          clone.classList.add('v167-planet-cover');
          clone.setAttribute('aria-hidden', 'true');

          var frontOrbit = wrap.querySelector('.v167-front-orbit');
          if (frontOrbit) wrap.insertBefore(clone, frontOrbit);
          else wrap.appendChild(clone);
        }

        var audioContext = null;
        var gainNode = null;
        var timer = null;
        var isOn = false;

        function startBeepLoop(button) {
          if (isOn) return;

          var AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextClass) {
            if (button) button.querySelector('.v167-audio-text').textContent = 'Audio unavailable';
            return;
          }

          audioContext = audioContext || new AudioContextClass();
          gainNode = gainNode || audioContext.createGain();
          gainNode.gain.value = 0.018;
          gainNode.connect(audioContext.destination);

          function oneBeep() {
            if (!isOn || !audioContext) return;

            var osc = audioContext.createOscillator();
            var beepGain = audioContext.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(1050, audioContext.currentTime);

            beepGain.gain.setValueAtTime(0.0001, audioContext.currentTime);
            beepGain.gain.linearRampToValueAtTime(0.018, audioContext.currentTime + 0.015);
            beepGain.gain.setValueAtTime(0.018, audioContext.currentTime + 0.34);
            beepGain.gain.linearRampToValueAtTime(0.0001, audioContext.currentTime + 0.40);

            osc.connect(beepGain);
            beepGain.connect(gainNode);

            osc.start(audioContext.currentTime);
            osc.stop(audioContext.currentTime + 0.42);
          }

          isOn = true;
          button.classList.add('active');
          button.querySelector('.v167-audio-text').textContent = 'Sputnik Beep On';

          oneBeep();
          timer = window.setInterval(oneBeep, 800);
        }

        function stopBeepLoop(button) {
          isOn = false;

          if (timer) {
            window.clearInterval(timer);
            timer = null;
          }

          if (button) {
            button.classList.remove('active');
            button.querySelector('.v167-audio-text').textContent = 'Enable Sputnik Beep';
          }
        }

        function setup() {
          ensurePlanetCover();

          var button = document.getElementById('v167AudioControl');
          if (!button) return;

          button.addEventListener('click', function () {
            if (isOn) stopBeepLoop(button);
            else startBeepLoop(button);
          });
        }

        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
        else setup();
      })();
    </script>
    '''


def remove_orbit_sections(html: str) -> str:
    if not isinstance(html, str):
        return html

    updated = html

    tokens = [
        'v167-back-orbit',
        'v167-front-orbit',
        'v167AudioControl',
        'v167-sputnik-beep-script',
        'v167-hero-satellite-css',
        'v166-back-orbit',
        'v166-front-orbit',
        'v166AudioControl',
        'v166-sputnik-beep-script',
        'v166-hero-satellite-css',
        'v165-hero-orbit-overlay',
        'v165AudioControl',
        'v165-sputnik-beep-script',
        'v165-hero-satellite-css',
        'v164c-top-orbital',
        'v164b-orbital-banner',
        'v164-orbital-banner',
    ]

    lower = updated.lower()

    for token in tokens:
        while token.lower() in lower:
            idx = lower.find(token.lower())
            removed = False

            for tag, close in [
                ('<section', '</section>'),
                ('<div', '</div>'),
                ('<button', '</button>'),
                ('<script', '</script>'),
                ('<style', '</style>'),
            ]:
                start = lower.rfind(tag, 0, idx)
                end = lower.find(close, idx)

                if start != -1 and end != -1:
                    end += len(close)
                    updated = updated[:start] + updated[end:]
                    lower = updated.lower()
                    removed = True
                    break

            if not removed:
                break

    return updated


def wrap_first_hero_image(html: str) -> str:
    if not isinstance(html, str):
        return html

    cleaned = remove_orbit_sections(html)
    overlay = hero_satellite_overlay_html()
    lower = cleaned.lower()

    markers = [
        'class="dashboard-image"',
        "class='dashboard-image'",
        'class="public-image"',
        "class='public-image'",
    ]

    for marker in markers:
        idx = lower.find(marker)

        if idx == -1:
            continue

        img_start = lower.rfind('<img', 0, idx)
        img_end = lower.find('>', idx)

        if img_start == -1 or img_end == -1:
            continue

        img_end += 1
        img_html = cleaned[img_start:img_end]

        wrapped = '<div class="v167-hero-wrap">' + img_html + "\n" + overlay + "\n</div>"
        return cleaned[:img_start] + wrapped + cleaned[img_end:]

    body_start = lower.find('<body')

    if body_start != -1:
        body_end = lower.find('>', body_start)

        if body_end != -1:
            body_end += 1
            fallback = (
                '<div class="v167-hero-wrap" '
                'style="width:min(1180px,calc(100% - 24px));height:420px;'
                'margin:14px auto;position:relative;border-radius:30px;background:#061426;">'
                + overlay
                + '</div>'
            )
            return cleaned[:body_end] + "\n" + fallback + "\n" + cleaned[body_end:]

    return cleaned + "\n" + overlay
