#!/usr/bin/env python3
"""
AlkaidSTART — Monochrome Kinetic Particle & Architectural Blueprint SVG Generator.

Zero external dependencies (Python 3 stdlib only).
Generates paired Dark (Obsidian/Graphite/Alabaster) and Light (Porcelain/Gray/Ink)
animated SVGs optimized for GitHub's strict <img> SVG renderer:
  - CSS @keyframes for smooth 60fps particle drift, breathing & signal pulse travel
  - SMIL <animateTransform> for exact-center cross-browser orbital rotations
  - Pure system precision typography (no blocked external @font-face imports)
  - 1000px master coordinate grid for near-1:1 sharpness inside GitHub README (896px)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import random
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "profile.config.json"
DATA_CACHE_PATH = ROOT_DIR / "scripts" / ".telemetry-cache.json"
ASSETS_DIR = ROOT_DIR / "assets"

THEMES: dict[str, dict[str, Any]] = {
    "dark": {
        "bg": "#09090B",
        "surface": "#0E0E11",
        "surface2": "#16161B",
        "border": "#222227",
        "hairline": "#27272E",
        "tick": "#3D3D47",
        "grid": "#FFFFFF",
        "grid_op": "0.032",
        "ink1": "#FAFAFA",
        "ink2": "#A1A1AA",
        "ink3": "#71717A",
        "ink4": "#484852",
        "particle": "#FFFFFF",
        "particle_dim": "#A1A1AA",
        "wire": "#FFFFFF",
        "glow_op": "0.065",
        "scan_color": "#FFFFFF",
        "scan_op": "0.10",
        "heat": ["#16161B", "#35353F", "#656573", "#A4A4B0", "#FAFAFA"],
        "langs": ["#FAFAFA", "#BEBEC8", "#8C8C98", "#646470", "#494954", "#363640", "#292932", "#1E1E25"],
    },
    "light": {
        "bg": "#FAFAFA",
        "surface": "#FFFFFF",
        "surface2": "#F0F0F3",
        "border": "#E2E2E7",
        "hairline": "#E7E7EC",
        "tick": "#C4C4CD",
        "grid": "#09090B",
        "grid_op": "0.042",
        "ink1": "#09090B",
        "ink2": "#52525B",
        "ink3": "#71717A",
        "ink4": "#A1A1AA",
        "particle": "#09090B",
        "particle_dim": "#52525B",
        "wire": "#09090B",
        "glow_op": "0.045",
        "scan_color": "#09090B",
        "scan_op": "0.065",
        "heat": ["#EFEFF2", "#D3D3DB", "#9A9AA6", "#54545F", "#09090B"],
        "langs": ["#09090B", "#3F3F47", "#63636E", "#8A8A96", "#A7A7B3", "#C2C2CC", "#D8D8E0", "#E8E8EE"],
    },
}

FONT_DISPLAY = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', 'Inter', system-ui, sans-serif"
FONT_BODY = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
FONT_MONO = "'SF Mono', 'JetBrains Mono', ui-monospace, Menlo, Monaco, Consolas, monospace"
FONT_SERIF = "'New York', 'Iowan Old Style', Georgia, 'Songti SC', 'Noto Serif SC', serif"


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def wrap_lines(text: str, max_chars: int = 44, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = f"{cur} {w}".strip()
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        tail = kept[-1]
        if len(tail) > max_chars - 3:
            tail = tail[: max_chars - 3].rstrip(" ,.;:-")
        kept[-1] = tail + "..."
        return kept
    return lines


def corner_brackets(w: int, h: int, inset: int, length: int, color: str, opacity: float = 0.65) -> str:
    i, l = inset, length
    segs = [
        f"M {i},{i + l} L {i},{i} L {i + l},{i}",
        f"M {w - i - l},{i} L {w - i},{i} L {w - i},{i + l}",
        f"M {i},{h - i - l} L {i},{h - i} L {i + l},{h - i}",
        f"M {w - i - l},{h - i} L {w - i},{h - i} L {w - i},{h - i - l}",
    ]
    return f'<path d="{" ".join(segs)}" fill="none" stroke="{color}" stroke-width="0.9" stroke-opacity="{opacity}" />'


def crosshair(x: float, y: float, r: float, color: str, opacity: float = 0.85) -> str:
    return (
        f'<g stroke="{color}" stroke-width="0.85" stroke-opacity="{opacity}">'
        f'<line x1="{x - r:.1f}" y1="{y:.1f}" x2="{x + r:.1f}" y2="{y:.1f}" />'
        f'<line x1="{x:.1f}" y1="{y - r:.1f}" x2="{x:.1f}" y2="{y + r:.1f}" />'
        f"</g>"
    )


def ruler_ticks(x1: float, x2: float, y: float, step: float, h: float, color: str, opacity: float = 0.45) -> str:
    paths = []
    x = x1
    idx = 0
    while x <= x2 + 0.01:
        th = h * (1.7 if idx % 5 == 0 else 1.0)
        paths.append(f"M {x:.1f},{y:.1f} v {th:.1f}")
        x += step
        idx += 1
    return f'<path d="{" ".join(paths)}" fill="none" stroke="{color}" stroke-width="0.7" stroke-opacity="{opacity}" />'


# ─────────────────────────────────────────────────────────────────────────────
# 1. HERO — 3D Kinetic Particle Manifold + Astrolabe + Ursa Major (Alkaid)
# ─────────────────────────────────────────────────────────────────────────────
def build_hero(theme_name: str, cfg: dict[str, Any], telemetry: dict[str, Any]) -> str:
    t = THEMES[theme_name]
    ident = cfg["identity"]
    W, H = 1000, 380

    # Generate true 3D perspective-projected harmonic particle manifold on right stage
    cx_stage, cy_stage = 746.0, 196.0
    pitch = math.radians(33.0)
    yaw = math.radians(-20.0)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)

    def project(x3: float, y3: float, z3: float) -> tuple[float, float, float]:
        # Rotate around Y (yaw), then X (pitch)
        xr = x3 * cos_y + z3 * sin_y
        zr = -x3 * sin_y + z3 * cos_y
        yr = y3 * cos_p - zr * sin_p
        zr2 = y3 * sin_p + zr * cos_p
        fov = 620.0
        scale = fov / (fov + zr2 + 120.0)
        sx = cx_stage + xr * scale
        sy = cy_stage + yr * scale
        return sx, sy, zr2

    nx, nz = 24, 12
    grid_pts: list[list[tuple[float, float, float, float]]] = []
    for iz in range(nz):
        row = []
        vz = (iz / (nz - 1) - 0.5) * 2.0  # [-1, 1]
        for ix in range(nx):
            ux = (ix / (nx - 1) - 0.5) * 2.0  # [-1, 1]
            # Sculpted mathematical interference wave
            r_dist = math.sqrt((ux * 1.15) ** 2 + (vz * 1.1) ** 2)
            env = math.exp(-0.55 * r_dist * r_dist)
            elev = (
                46.0 * math.sin(ux * 2.55 + vz * 1.25) * math.cos(vz * 1.65) * env
                + 22.0 * math.cos(ux * 3.8 - vz * 2.4) * env
                - 14.0 * (ux * vz)
            )
            x3 = ux * 235.0
            z3 = vz * 165.0
            y3 = -elev + 16.0
            sx, sy, depth = project(x3, y3, z3)
            row.append((sx, sy, depth, elev))
        grid_pts.append(row)

    # Wireframe latitude ribbons + sparse meridian hairlines
    wire_lines: list[str] = []
    for iz in range(nz):
        pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in grid_pts[iz])
        op = 0.055 + 0.065 * (1.0 - abs(iz / (nz - 1) - 0.5) * 2.0)
        wire_lines.append(
            f'<polyline points="{pts_str}" fill="none" stroke="{t["wire"]}" stroke-opacity="{op:.3f}" stroke-width="0.65" />'
        )
    for ix in range(0, nx, 3):
        pts_str = " ".join(f"{grid_pts[iz][ix][0]:.1f},{grid_pts[iz][ix][1]:.1f}" for iz in range(nz))
        wire_lines.append(
            f'<polyline points="{pts_str}" fill="none" stroke="{t["wire"]}" stroke-opacity="0.05" stroke-width="0.55" />'
        )

    # Flatten & Z-sort particles so near particles sit cleanly above far particles
    particles: list[tuple[float, float, float, float, int]] = []
    for iz, row in enumerate(grid_pts):
        for ix, (sx, sy, depth, elev) in enumerate(row):
            if 498 <= sx <= 992 and 48 <= sy <= 332:
                phase = (ix + iz * 2) % 5 + 1
                particles.append((depth, sx, sy, elev, phase))
    particles.sort(key=lambda item: -item[0])  # far to near

    particle_elems: list[str] = []
    for depth, sx, sy, elev, phase in particles:
        depth_norm = max(0.0, min(1.0, (160.0 - depth) / 310.0))
        crest_boost = max(0.0, min(1.0, (elev + 35.0) / 80.0))
        rad = 0.65 + 1.35 * depth_norm + 0.45 * crest_boost
        op = 0.14 + 0.58 * depth_norm + 0.22 * crest_boost
        op = min(0.95, op)
        particle_elems.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{rad:.2f}" fill="{t["particle"]}" fill-opacity="{op:.2f}" class="w{phase}" />'
        )

    # Ambient micro-stardust floating delicately in the right field
    rng = random.Random(202607)
    dust_elems: list[str] = []
    for i in range(42):
        dx = rng.uniform(508, 982)
        dy = rng.uniform(52, 324)
        dr = rng.uniform(0.45, 1.05)
        dop = rng.uniform(0.10, 0.36)
        cls = f"f{(i % 4) + 1}"
        dust_elems.append(
            f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="{dr:.2f}" fill="{t["particle_dim"]}" fill-opacity="{dop:.2f}" class="{cls}" />'
        )

    # Astrolabe precision degree ticks around (746, 189)
    ast_cx, ast_cy = 746.0, 189.0
    tick_paths: list[str] = []
    for deg in range(0, 360, 6):
        rad_a = math.radians(deg)
        r_in = 122.0 if deg % 30 == 0 else 125.5
        r_out = 131.0
        x1 = ast_cx + r_in * math.cos(rad_a)
        y1 = ast_cy + r_in * math.sin(rad_a)
        x2 = ast_cx + r_out * math.cos(rad_a)
        y2 = ast_cy + r_out * math.sin(rad_a)
        tick_paths.append(f"M {x1:.1f},{y1:.1f} L {x2:.1f},{y2:.1f}")

    # Authentic Ursa Major (Big Dipper / 北斗七星) geometric proportions — Alkaid (η UMa) at focal apex
    dipper_stars = [
        ("Dubhe", 560.0, 118.0, 1.8),
        ("Merak", 582.0, 162.0, 1.6),
        ("Phecda", 640.0, 166.0, 1.6),
        ("Megrez", 645.0, 128.0, 1.5),
        ("Alioth", 708.0, 114.0, 2.0),
        ("Mizar", 772.0, 102.0, 1.9),
        ("Alkaid", 848.0, 126.0, 3.0),
    ]
    dipper_pts = " ".join(f"{x:.1f},{y:.1f}" for _, x, y, _ in dipper_stars)
    dipper_nodes: list[str] = []
    for name, sx, sy, sr in dipper_stars:
        if name == "Alkaid":
            dipper_nodes.append(
                f'<g>'
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="16" fill="none" stroke="{t["ink1"]}" stroke-width="0.65" stroke-opacity="0.28" class="pulse-ring" />'
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="9" fill="none" stroke="{t["ink1"]}" stroke-width="0.8" stroke-opacity="0.55" />'
                f'<line x1="{sx - 13:.1f}" y1="{sy:.1f}" x2="{sx - 5:.1f}" y2="{sy:.1f}" stroke="{t["ink1"]}" stroke-width="0.7" stroke-opacity="0.6" />'
                f'<line x1="{sx + 5:.1f}" y1="{sy:.1f}" x2="{sx + 13:.1f}" y2="{sy:.1f}" stroke="{t["ink1"]}" stroke-width="0.7" stroke-opacity="0.6" />'
                f'<line x1="{sx:.1f}" y1="{sy - 13:.1f}" x2="{sx:.1f}" y2="{sy - 5:.1f}" stroke="{t["ink1"]}" stroke-width="0.7" stroke-opacity="0.6" />'
                f'<line x1="{sx:.1f}" y1="{sy + 5:.1f}" x2="{sx:.1f}" y2="{sy + 13:.1f}" stroke="{t["ink1"]}" stroke-width="0.7" stroke-opacity="0.6" />'
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3.2" fill="{t["ink1"]}" filter="url(#soft-bloom)" />'
                f'<polyline points="{sx + 12:.1f},{sy - 10:.1f} {sx + 26:.1f},{sy - 24:.1f} {sx + 120:.1f},{sy - 24:.1f}" fill="none" stroke="{t["ink3"]}" stroke-width="0.75" stroke-opacity="0.75" />'
                f'<text x="{sx + 30:.1f}" y="{sy - 29:.1f}" class="mono-micro" fill="{t["ink1"]}">η UMa · ALKAID</text>'
                f'<text x="{sx + 30:.1f}" y="{sy - 13:.1f}" class="mono-tiny" fill="{t["ink3"]}">MAG 1.86 · 104 LY</text>'
                f"</g>"
            )
        else:
            dipper_nodes.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr + 2.2:.1f}" fill="{t["ink1"]}" fill-opacity="0.14" />'
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr:.1f}" fill="{t["ink1"]}" fill-opacity="0.88" />'
            )

    # Telemetry footer strip metrics
    pub_repos = telemetry.get("publicRepos", 74)
    orig_repos = telemetry.get("originalRepos", 56)
    tot_contrib = telemetry.get("totalContributions", 2993)
    streak = telemetry.get("currentStreak", 13)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Alkaid — Full-Stack Architect and AI Agent Systems Engineer">
  <defs>
    <clipPath id="hero-clip">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" />
    </clipPath>
    <pattern id="hero-grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{t["grid"]}" stroke-width="0.6" stroke-opacity="{t["grid_op"]}" />
    </pattern>
    <radialGradient id="stage-glow" cx="74%" cy="51%" r="36%">
      <stop offset="0%" stop-color="{t["particle"]}" stop-opacity="{t["glow_op"]}" />
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="beam-h" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{t["ink1"]}" stop-opacity="0" />
      <stop offset="50%" stop-color="{t["ink1"]}" stop-opacity="0.75" />
      <stop offset="100%" stop-color="{t["ink1"]}" stop-opacity="0" />
    </linearGradient>
    <filter id="soft-bloom" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="2.2" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <style>
      .mono-meta {{ font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: 1.6px; fill: {t["ink3"]}; }}
      .mono-micro {{ font-family: {FONT_MONO}; font-size: 9.5px; font-weight: 600; letter-spacing: 1.2px; }}
      .mono-tiny {{ font-family: {FONT_MONO}; font-size: 8.5px; letter-spacing: 1.0px; }}
      .hero-title {{ font-family: {FONT_DISPLAY}; font-size: 64px; font-weight: 600; letter-spacing: -2.8px; fill: {t["ink1"]}; }}
      .hero-role {{ font-family: {FONT_BODY}; font-size: 14px; font-weight: 400; letter-spacing: -0.1px; fill: {t["ink2"]}; }}
      .hero-motto-en {{ font-family: {FONT_SERIF}; font-size: 13.5px; font-style: italic; fill: {t["ink2"]}; }}
      .hero-motto-zh {{ font-family: {FONT_BODY}; font-size: 11.5px; letter-spacing: 0.4px; fill: {t["ink3"]}; }}
      .pill-text {{ font-family: {FONT_MONO}; font-size: 9px; letter-spacing: 1.1px; fill: {t["ink2"]}; }}
      .foot-label {{ font-family: {FONT_MONO}; font-size: 8.5px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .foot-val {{ font-family: {FONT_MONO}; font-size: 10.5px; font-weight: 500; fill: {t["ink1"]}; }}

      .w1 {{ animation: waveA 6.4s ease-in-out infinite; }}
      .w2 {{ animation: waveB 7.8s ease-in-out infinite 0.7s; }}
      .w3 {{ animation: waveA 9.0s ease-in-out infinite 1.5s; }}
      .w4 {{ animation: waveC 7.1s ease-in-out infinite 2.3s; }}
      .w5 {{ animation: waveB 8.5s ease-in-out infinite 3.1s; }}

      .f1 {{ animation: floatDust 9s ease-in-out infinite; }}
      .f2 {{ animation: floatDust 11.5s ease-in-out infinite 2s; }}
      .f3 {{ animation: floatDust 8.2s ease-in-out infinite 4s; }}
      .f4 {{ animation: floatDust 10.4s ease-in-out infinite 1.2s; }}

      .beacon {{ animation: beaconPulse 2.8s ease-in-out infinite; }}
      .pulse-ring {{ animation: ringPulse 4.2s ease-in-out infinite; }}
      .constellation-flow {{ stroke-dasharray: 28 290; animation: flowConstellation 5.2s linear infinite; }}
      .rail-glint {{ animation: railSlide 7.5s cubic-bezier(0.45, 0, 0.55, 1) infinite; }}

      @keyframes waveA {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-5.5px); }}
      }}
      @keyframes waveB {{
        0%, 100% {{ transform: translate(0px, 0px); opacity: 0.92; }}
        50% {{ transform: translate(2.0px, 4.5px); opacity: 0.42; }}
      }}
      @keyframes waveC {{
        0%, 100% {{ transform: translate(0px, 0px); opacity: 0.88; }}
        50% {{ transform: translate(-2.2px, -4.0px); opacity: 0.48; }}
      }}
      @keyframes floatDust {{
        0%, 100% {{ transform: translateY(0px); opacity: 0.35; }}
        50% {{ transform: translateY(-7px); opacity: 0.85; }}
      }}
      @keyframes beaconPulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.28; }}
      }}
      @keyframes ringPulse {{
        0%, 100% {{ opacity: 0.55; }}
        50% {{ opacity: 0.14; }}
      }}
      @keyframes flowConstellation {{
        0% {{ stroke-dashoffset: 318; }}
        100% {{ stroke-dashoffset: 0; }}
      }}
      @keyframes railSlide {{
        0% {{ transform: translateX(-140px); opacity: 0; }}
        15% {{ opacity: 0.9; }}
        85% {{ opacity: 0.9; }}
        100% {{ transform: translateX(1040px); opacity: 0; }}
      }}
    </style>
  </defs>

  <g clip-path="url(#hero-clip)">
    <!-- Base Canvas & Subtle Architectural Grid -->
    <rect width="{W}" height="{H}" fill="{t["bg"]}" />
    <rect width="{W}" height="{H}" fill="url(#hero-grid)" />
    <rect width="{W}" height="{H}" fill="url(#stage-glow)" />

    <!-- Primary Structural Hairlines -->
    <line x1="0" y1="42" x2="{W}" y2="42" stroke="{t["hairline"]}" stroke-width="0.9" />
    <line x1="0" y1="334" x2="{W}" y2="334" stroke="{t["hairline"]}" stroke-width="0.9" />
    <line x1="492" y1="42" x2="492" y2="334" stroke="{t["hairline"]}" stroke-width="0.85" />
    <!-- Animated Photon Glint on Top Datum Line -->
    <rect x="0" y="41.4" width="110" height="1.2" fill="url(#beam-h)" class="rail-glint" />

    <!-- Top Status Telemetry Bar -->
    <text x="36" y="25" class="mono-meta">INDEX 00 // ALKAIDSTART</text>
    <text x="500" y="25" text-anchor="middle" class="mono-meta">{esc(ident["designation"])} · {esc(ident["coordinates"])}</text>
    <circle cx="820" cy="21.5" r="2.6" fill="{t["ink1"]}" class="beacon" />
    <text x="964" y="25" text-anchor="end" class="mono-meta">AVAILABLE · {esc(ident["timezone"])}</text>

    <!-- Left Editorial Column -->
    <text x="36" y="88" class="mono-meta">PROFILE ARCHIVE · EDITION 2026</text>

    <text x="34" y="160" class="hero-title">{esc(ident["displayName"])}</text>
    <text x="214" y="122" class="mono-micro" fill="{t["ink3"]}">/07</text>

    <text x="36" y="192" class="hero-role">{esc(ident["role"])}</text>

    <!-- Architectural Ruler Hairline Accent -->
    <line x1="36" y1="214" x2="452" y2="214" stroke="{t["hairline"]}" stroke-width="0.85" />
    {ruler_ticks(36, 156, 214, 12, 3.5, t["tick"], 0.7)}

    <text x="36" y="246" class="hero-motto-en">"{esc(ident["tagline"])}"</text>
    <text x="36" y="270" class="hero-motto-zh">{esc(ident["taglineZh"])}</text>

    <!-- Monochrome Technical Spec Tags -->
    <g transform="translate(36, 292)">
      <rect x="0" y="0" width="84" height="22" rx="3" fill="{t["surface2"]}" stroke="{t["border"]}" stroke-width="0.75" />
      <text x="42" y="14.2" text-anchor="middle" class="pill-text">CLI AGENTS</text>

      <rect x="92" y="0" width="116" height="22" rx="3" fill="{t["surface2"]}" stroke="{t["border"]}" stroke-width="0.75" />
      <text x="150" y="14.2" text-anchor="middle" class="pill-text">AGENT ROUTING</text>

      <rect x="216" y="0" width="96" height="22" rx="3" fill="{t["surface2"]}" stroke="{t["border"]}" stroke-width="0.75" />
      <text x="264" y="14.2" text-anchor="middle" class="pill-text">LOCAL-FIRST</text>

      <rect x="320" y="0" width="96" height="22" rx="3" fill="{t["surface2"]}" stroke="{t["border"]}" stroke-width="0.75" />
      <text x="368" y="14.2" text-anchor="middle" class="pill-text">OPEN SOURCE</text>
    </g>

    <!-- Right Sculptural Kinetic Particle & Astrolabe Stage -->
    <g>
      <!-- Orthogonal Sightline Axes & Micro Degree Markers -->
      <line x1="492" y1="189" x2="1000" y2="189" stroke="{t["wire"]}" stroke-opacity="0.06" stroke-width="0.75" stroke-dasharray="3 5" />
      <line x1="746" y1="42" x2="746" y2="334" stroke="{t["wire"]}" stroke-opacity="0.06" stroke-width="0.75" stroke-dasharray="3 5" />
      <text x="746" y="55" text-anchor="middle" class="mono-tiny" fill="{t["ink4"]}">000°</text>
      <text x="746" y="328" text-anchor="middle" class="mono-tiny" fill="{t["ink4"]}">180°</text>
      <text x="514" y="185" class="mono-tiny" fill="{t["ink4"]}">270°</text>
      <text x="978" y="185" text-anchor="end" class="mono-tiny" fill="{t["ink4"]}">090°</text>

      <!-- Rotating Astrolabe Calibration Ring -->
      <g>
        <animateTransform attributeName="transform" type="rotate" from="0 746 189" to="360 746 189" dur="120s" repeatCount="indefinite" />
        <circle cx="746" cy="189" r="128" fill="none" stroke="{t["wire"]}" stroke-opacity="0.12" stroke-width="0.75" />
        <path d="{" ".join(tick_paths)}" fill="none" stroke="{t["wire"]}" stroke-opacity="0.18" stroke-width="0.75" />
      </g>

      <!-- Counter-Rotating Inner Gyroscopic Orbital Ring -->
      <g>
        <animateTransform attributeName="transform" type="rotate" from="360 746 189" to="0 746 189" dur="80s" repeatCount="indefinite" />
        <circle cx="746" cy="189" r="92" fill="none" stroke="{t["wire"]}" stroke-opacity="0.14" stroke-width="0.75" stroke-dasharray="2 7" />
        <circle cx="838" cy="189" r="2.2" fill="{t["ink1"]}" fill-opacity="0.75" />
        <circle cx="654" cy="189" r="1.6" fill="{t["ink2"]}" fill-opacity="0.55" />
      </g>

      <circle cx="746" cy="189" r="54" fill="none" stroke="{t["wire"]}" stroke-opacity="0.09" stroke-width="0.65" />

      <!-- Ambient Floating Stardust -->
      {"".join(dust_elems)}

      <!-- 3D Sculpted Wireframe Ribbons -->
      {"".join(wire_lines)}

      <!-- 3D Depth-Sorted Kinetic Particle Manifold -->
      {"".join(particle_elems)}

      <!-- Ursa Major (北斗七星) Constellation Topology + Streaming Photon -->
      <polyline points="{dipper_pts}" fill="none" stroke="{t["ink1"]}" stroke-opacity="0.24" stroke-width="0.95" />
      <polyline points="{dipper_pts}" fill="none" stroke="{t["ink1"]}" stroke-opacity="0.92" stroke-width="1.35" stroke-linecap="round" class="constellation-flow" />
      {"".join(dipper_nodes)}
    </g>

    <!-- Bottom Architectural Telemetry Bar -->
    <line x1="276" y1="334" x2="276" y2="380" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="516" y1="334" x2="516" y2="380" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="766" y1="334" x2="766" y2="380" stroke="{t["hairline"]}" stroke-width="0.85" />

    <text x="36" y="352" class="foot-label">CORE STACK</text>
    <text x="36" y="369" class="foot-val">TypeScript · Go · Python · Rust</text>

    <text x="296" y="352" class="foot-label">REPOSITORIES</text>
    <text x="296" y="369" class="foot-val">{pub_repos} Public · {orig_repos} Original</text>

    <text x="536" y="352" class="foot-label">ACTIVITY PULSE</text>
    <text x="536" y="369" class="foot-val">{tot_contrib:,} Contrib · {streak}d Streak</text>

    <text x="786" y="352" class="foot-label">JOURNAL &amp; LAB</text>
    <text x="786" y="369" class="foot-val">alkaid.live ↗</text>

    <!-- Precision Intersection Crosshairs & Registration Brackets -->
    {crosshair(492, 42, 4.5, t["tick"])}
    {crosshair(492, 334, 4.5, t["tick"])}
    {crosshair(276, 334, 3.5, t["tick"], 0.7)}
    {crosshair(516, 334, 3.5, t["tick"], 0.7)}
    {crosshair(766, 334, 3.5, t["tick"], 0.7)}
    {corner_brackets(W, H, 10, 9, t["tick"], 0.6)}
  </g>

  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" />
</svg>'''


# ─────────────────────────────────────────────────────────────────────────────
# 2. SECTION DIVIDERS — Precision Datum Hairlines + Gliding Light Particle
# ─────────────────────────────────────────────────────────────────────────────
def build_divider(theme_name: str, index: str, title: str, code: str) -> str:
    t = THEMES[theme_name]
    W, H = 1000, 44
    # Dynamic rail start calculated from exact title length + generous breathing room
    line_start = min(560, max(320, 46 + int(len(title) * 8.6) + 22))
    line_end = 842
    ticks = ruler_ticks(line_start + 16, line_end - 16, 22, 24, 3.0, t["tick"], 0.55)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="{esc(index)} {esc(title)}">
  <defs>
    <linearGradient id="div-glint-{index}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{t["ink1"]}" stop-opacity="0" />
      <stop offset="50%" stop-color="{t["ink1"]}" stop-opacity="0.9" />
      <stop offset="100%" stop-color="{t["ink1"]}" stop-opacity="0" />
    </linearGradient>
    <clipPath id="div-rail-{index}">
      <rect x="{line_start}" y="19" width="{line_end - line_start}" height="6" />
    </clipPath>
    <style>
      .div-idx {{ font-family: {FONT_MONO}; font-size: 10.5px; font-weight: 600; letter-spacing: 1.4px; fill: {t["ink1"]}; }}
      .div-title {{ font-family: {FONT_MONO}; font-size: 10.5px; letter-spacing: 1.8px; fill: {t["ink2"]}; }}
      .div-code {{ font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .div-pulse {{ animation: divGlide 6.5s cubic-bezier(0.45, 0, 0.55, 1) infinite; }}
      @keyframes divGlide {{
        0% {{ transform: translateX({line_start - 90}px); opacity: 0; }}
        12% {{ opacity: 1; }}
        88% {{ opacity: 1; }}
        100% {{ transform: translateX({line_end + 20}px); opacity: 0; }}
      }}
    </style>
  </defs>

  <!-- Left Index Marker -->
  <rect x="2" y="13" width="28" height="18" rx="3" fill="{t["surface2"]}" stroke="{t["border"]}" stroke-width="0.8" />
  <text x="16" y="25.2" text-anchor="middle" class="div-idx">{esc(index)}</text>
  <text x="42" y="25.5" class="div-title">{esc(title)}</text>

  <!-- Precision Architectural Datum Rail -->
  <line x1="{line_start}" y1="22" x2="{line_end}" y2="22" stroke="{t["hairline"]}" stroke-width="0.9" />
  {ticks}
  {crosshair(line_start, 22, 3.2, t["tick"], 0.85)}
  {crosshair(line_end, 22, 3.2, t["tick"], 0.85)}

  <!-- Animated Travelling Particle Pulse -->
  <g clip-path="url(#div-rail-{index})">
    <rect x="0" y="21.3" width="84" height="1.4" fill="url(#div-glint-{index})" class="div-pulse" />
  </g>

  <!-- Right Spec Code -->
  <text x="994" y="25.2" text-anchor="end" class="div-code">{esc(code)}</text>
</svg>'''


# ─────────────────────────────────────────────────────────────────────────────
# 3. ARCHITECTURE TOPOLOGY — 4-Pillar Schematic + Animated Particle Signal Bus
# ─────────────────────────────────────────────────────────────────────────────
def build_architecture(theme_name: str, cfg: dict[str, Any]) -> str:
    t = THEMES[theme_name]
    pillars = cfg["architecturePillars"]
    W, H = 1000, 360

    # Four column x-centers
    col_w = W / 4.0  # 250px each
    centers = [125.0, 375.0, 625.0, 875.0]
    core_x, core_y = 500.0, 80.0

    # Ambient micro-particles in upper signal bus bay
    rng = random.Random(202611)
    bus_dust = []
    for i in range(46):
        px = rng.uniform(24, 976)
        py = rng.uniform(48, 128)
        pr = rng.uniform(0.45, 1.0)
        pop = rng.uniform(0.10, 0.34)
        bus_dust.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr:.2f}" fill="{t["particle"]}" fill-opacity="{pop:.2f}" class="bd{(i % 3) + 1}" />'
        )

    # Orthogonal PCB/architectural bus paths cleanly terminating on outer CORE ring perimeter
    bus_paths = [
        f"M {core_x - 32:.1f},{core_y:.1f} L {centers[0]:.1f},{core_y:.1f} L {centers[0]:.1f},134",
        f"M {core_x - 30:.1f},{core_y + 12:.1f} L {centers[1]:.1f},{core_y + 12:.1f} L {centers[1]:.1f},134",
        f"M {core_x + 30:.1f},{core_y + 12:.1f} L {centers[2]:.1f},{core_y + 12:.1f} L {centers[2]:.1f},134",
        f"M {core_x + 32:.1f},{core_y:.1f} L {centers[3]:.1f},{core_y:.1f} L {centers[3]:.1f},134",
    ]
    bus_svg = []
    for idx, d in enumerate(bus_paths):
        bus_svg.append(f'<path d="{d}" fill="none" stroke="{t["tick"]}" stroke-width="0.9" stroke-opacity="0.7" />')
        bus_svg.append(
            f'<path d="{d}" fill="none" stroke="{t["ink1"]}" stroke-width="1.5" stroke-linecap="round" '
            f'class="sig-flow s{idx + 1}" />'
        )
        # Terminal node dot at pillar entry
        cx = centers[idx]
        bus_svg.append(f'<circle cx="{cx:.1f}" cy="134" r="3.2" fill="{t["bg"]}" stroke="{t["ink1"]}" stroke-width="1.1" />')
        bus_svg.append(f'<circle cx="{cx:.1f}" cy="134" r="1.2" fill="{t["ink1"]}" />')

    # Render 4 clean pillar columns
    pillar_svg = []
    for idx, p in enumerate(pillars[:4]):
        x0 = idx * col_w
        pad = 20
        if idx > 0:
            pillar_svg.append(f'<line x1="{x0:.1f}" y1="134" x2="{x0:.1f}" y2="{H}" stroke="{t["hairline"]}" stroke-width="0.85" />')
            pillar_svg.append(crosshair(x0, 134, 4.0, t["tick"], 0.85))

        pillar_svg.append(f'<text x="{x0 + pad:.1f}" y="162" class="p-idx">{esc(p["index"])} // MODULE</text>')
        pillar_svg.append(f'<text x="{x0 + pad:.1f}" y="182" class="p-title">{esc(p["title"])}</text>')
        pillar_svg.append(f'<text x="{x0 + pad:.1f}" y="198" class="p-sub">{esc(p["subtitle"])}</text>')
        pillar_svg.append(
            f'<line x1="{x0 + pad:.1f}" y1="210" x2="{x0 + col_w - pad:.1f}" y2="210" stroke="{t["hairline"]}" stroke-width="0.75" />'
        )

        # 2-column × 5-row structured technical items with generous right breathing room
        items = p["items"][:10]
        for i, item in enumerate(items):
            col = i % 2
            row = i // 2
            ix = x0 + pad + col * 104
            iy = 232 + row * 23
            dot_op = "0.9" if row < 2 else "0.45"
            pillar_svg.append(f'<circle cx="{ix + 3:.1f}" cy="{iy - 3.5:.1f}" r="1.5" fill="{t["ink1"]}" fill-opacity="{dot_op}" />')
            pillar_svg.append(f'<text x="{ix + 10:.1f}" y="{iy:.1f}" class="p-item">{esc(item)}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="System Architecture and Engineering Stack Topology">
  <defs>
    <clipPath id="arch-clip">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" />
    </clipPath>
    <pattern id="arch-grid" width="25" height="25" patternUnits="userSpaceOnUse">
      <path d="M 25 0 L 0 0 0 25" fill="none" stroke="{t["grid"]}" stroke-width="0.5" stroke-opacity="{t["grid_op"]}" />
    </pattern>
    <style>
      .hdr-mono {{ font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: 1.5px; fill: {t["ink3"]}; }}
      .core-lbl {{ font-family: {FONT_MONO}; font-size: 8px; font-weight: 600; letter-spacing: 1.2px; fill: {t["ink1"]}; }}
      .p-idx {{ font-family: {FONT_MONO}; font-size: 9px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .p-title {{ font-family: {FONT_DISPLAY}; font-size: 12.2px; font-weight: 600; letter-spacing: 0.3px; fill: {t["ink1"]}; }}
      .p-sub {{ font-family: {FONT_BODY}; font-size: 10.5px; fill: {t["ink3"]}; }}
      .p-item {{ font-family: {FONT_MONO}; font-size: 9.7px; fill: {t["ink2"]}; }}

      .sig-flow {{ stroke-dasharray: 22 460; }}
      .s1 {{ animation: busMove 4.4s linear infinite; }}
      .s2 {{ animation: busMove 3.6s linear infinite 0.9s; }}
      .s3 {{ animation: busMove 3.8s linear infinite 1.7s; }}
      .s4 {{ animation: busMove 4.6s linear infinite 0.4s; }}

      .bd1 {{ animation: dustBreathe 6.5s ease-in-out infinite; }}
      .bd2 {{ animation: dustBreathe 8.2s ease-in-out infinite 1.4s; }}
      .bd3 {{ animation: dustBreathe 7.1s ease-in-out infinite 2.8s; }}

      @keyframes busMove {{
        0% {{ stroke-dashoffset: 482; opacity: 0.1; }}
        15% {{ opacity: 0.95; }}
        85% {{ opacity: 0.95; }}
        100% {{ stroke-dashoffset: 0; opacity: 0.1; }}
      }}
      @keyframes dustBreathe {{
        0%, 100% {{ opacity: 0.18; transform: translateY(0px); }}
        50% {{ opacity: 0.65; transform: translateY(-3.5px); }}
      }}
    </style>
  </defs>

  <g clip-path="url(#arch-clip)">
    <rect width="{W}" height="{H}" fill="{t["bg"]}" />
    <rect x="0" y="38" width="{W}" height="96" fill="url(#arch-grid)" />

    <!-- Header Strip -->
    <line x1="0" y1="38" x2="{W}" y2="38" stroke="{t["hairline"]}" stroke-width="0.9" />
    <text x="24" y="23" class="hdr-mono">SYSTEM TOPOLOGY // FOUR-PILLAR ENGINEERING ARCHITECTURE</text>
    <text x="976" y="23" text-anchor="end" class="hdr-mono">40 MODULES · MONOLITHIC CLARITY</text>

    <!-- Signal Bus Chamber -->
    {"".join(bus_dust)}
    <line x1="0" y1="134" x2="{W}" y2="134" stroke="{t["hairline"]}" stroke-width="0.9" />
    {"".join(bus_svg)}

    <!-- Central Orbital Core Node -->
    <g>
      <g>
        <animateTransform attributeName="transform" type="rotate" from="0 500 84" to="360 500 84" dur="36s" repeatCount="indefinite" />
        <circle cx="500" cy="84" r="30" fill="none" stroke="{t["tick"]}" stroke-width="0.8" stroke-dasharray="3 5" />
        <circle cx="530" cy="84" r="1.8" fill="{t["ink1"]}" />
        <circle cx="470" cy="84" r="1.4" fill="{t["ink2"]}" />
      </g>
      <circle cx="500" cy="84" r="22" fill="{t["surface"]}" stroke="{t["ink1"]}" stroke-width="0.9" stroke-opacity="0.7" />
      <text x="500" y="87" text-anchor="middle" class="core-lbl">CORE</text>
    </g>

    <!-- 4 Architectural Columns -->
    {"".join(pillar_svg)}

    {corner_brackets(W, H, 10, 8, t["tick"], 0.55)}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" />
</svg>'''


# ─────────────────────────────────────────────────────────────────────────────
# 4. FLAGSHIP WORKS — 2x2 Swiss Bento with 4 Bespoke Animated Particle Artworks
# ─────────────────────────────────────────────────────────────────────────────
def render_work_motif(motif: str, x: float, y: float, w: float, h: float, t: dict[str, Any]) -> str:
    cx, cy = x + w / 2.0, y + h / 2.0
    parts: list[str] = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{t["surface"]}" stroke="{t["hairline"]}" stroke-width="0.85" />'
    ]
    # Tiny inner corner ticks
    parts.append(
        f'<path d="M {x + 6:.1f},{y + 11:.1f} V {y + 6:.1f} H {x + 11:.1f} '
        f'M {x + w - 11:.1f},{y + 6:.1f} H {x + w - 6:.1f} V {y + 11:.1f} '
        f'M {x + 6:.1f},{y + h - 11:.1f} V {y + h - 6:.1f} H {x + 11:.1f} '
        f'M {x + w - 11:.1f},{y + h - 6:.1f} H {x + w - 6:.1f} V {y + h - 11:.1f}" '
        f'fill="none" stroke="{t["tick"]}" stroke-width="0.7" />'
    )

    if motif == "terminal_matrix":
        # Kinetic Particle Terminal Token Stream
        rng = random.Random(101)
        rows = 7
        cols = 12
        for r in range(rows):
            ry = y + 34 + r * 16.5
            active_cols = rng.randint(5, cols)
            parts.append(f'<line x1="{x + 18:.1f}" y1="{ry:.1f}" x2="{x + w - 18:.1f}" y2="{ry:.1f}" stroke="{t["hairline"]}" stroke-width="0.5" stroke-opacity="0.7" />')
            for c in range(active_cols):
                rx = x + 22 + c * 10.6
                rad = 1.75 if (r == 3 and c == active_cols - 1) else rng.uniform(0.8, 1.55)
                op = 0.95 if (r == 3 and c == active_cols - 1) else rng.uniform(0.22, 0.78)
                cls = f"m-p{(r + c) % 4 + 1}"
                parts.append(f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="{rad:.2f}" fill="{t["particle"]}" fill-opacity="{op:.2f}" class="{cls}" />')
        # Prompt chevron & pulsing cursor
        parts.append(f'<text x="{x + 16:.1f}" y="{y + 18:.1f}" class="motif-lbl">&gt;_ AGENT.TTY</text>')
        parts.append(f'<rect x="{x + 126:.1f}" y="{y + 79:.1f}" width="5" height="9" rx="1" fill="{t["ink1"]}" class="m-blink" />')

    elif motif == "orbital_router":
        # Multi-Agent Orbital Routing Topology
        nodes = [
            (cx - 52, cy - 34),
            (cx + 52, cy - 30),
            (cx - 48, cy + 36),
            (cx + 48, cy + 34),
        ]
        # Rotating faint radar ring
        parts.append(
            f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx:.1f} {cy:.1f}" to="360 {cx:.1f} {cy:.1f}" dur="42s" repeatCount="indefinite" />'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="50" fill="none" stroke="{t["tick"]}" stroke-width="0.7" stroke-dasharray="2 6" />'
            f'<circle cx="{cx + 50:.1f}" cy="{cy:.1f}" r="1.6" fill="{t["ink1"]}" /></g>'
        )
        for i, (nx, ny) in enumerate(nodes):
            parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{t["tick"]}" stroke-width="0.75" />')
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{t["ink1"]}" stroke-width="1.4" '
                f'stroke-linecap="round" class="route-pkt rp{i + 1}" />'
            )
            parts.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="5.5" fill="{t["bg"]}" stroke="{t["ink2"]}" stroke-width="0.9" />')
            parts.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="1.8" fill="{t["ink1"]}" class="m-p{(i % 4) + 1}" />')
        # Central relay core
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="{t["surface2"]}" stroke="{t["ink1"]}" stroke-width="1.0" />')
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.2" fill="{t["ink1"]}" />')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 17:.1f}" class="motif-lbl">ROUTE // 4 NODES</text>')

    elif motif == "silk_ribbon":
        # Harmonic Silk Particle Ribbon
        for strand in range(3):
            pts = []
            for k in range(28):
                u = k / 27.0
                px = x + 16 + u * (w - 32)
                py = cy + (strand - 1) * 14 + 24.0 * math.sin(u * math.pi * 2.1 + strand * 0.85) * math.cos(u * math.pi * 0.65)
                pts.append((px, py))
            poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
            parts.append(f'<polyline points="{poly}" fill="none" stroke="{t["wire"]}" stroke-opacity="0.14" stroke-width="0.7" />')
            for k, (px, py) in enumerate(pts):
                rad = 0.75 + 1.05 * (0.5 + 0.5 * math.sin(k * 0.4 + strand))
                op = 0.25 + 0.65 * (0.5 + 0.5 * math.cos(k * 0.35 - strand))
                parts.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{rad:.2f}" fill="{t["particle"]}" fill-opacity="{op:.2f}" class="m-p{(k + strand) % 4 + 1}" />'
                )
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 17:.1f}" class="motif-lbl">FLOW // STUDIO</text>')

    else:
        # gyro_core — Crystalline Desktop Hub
        parts.append(
            f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx:.1f} {cy:.1f}" to="360 {cx:.1f} {cy:.1f}" dur="50s" repeatCount="indefinite" />'
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="54" ry="22" fill="none" stroke="{t["tick"]}" stroke-width="0.85" />'
            f'<circle cx="{cx + 54:.1f}" cy="{cy:.1f}" r="2.2" fill="{t["ink1"]}" />'
            f'<circle cx="{cx - 54:.1f}" cy="{cy:.1f}" r="1.5" fill="{t["ink2"]}" /></g>'
        )
        parts.append(
            f'<g><animateTransform attributeName="transform" type="rotate" from="60 {cx:.1f} {cy:.1f}" to="-300 {cx:.1f} {cy:.1f}" dur="38s" repeatCount="indefinite" />'
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="48" ry="20" fill="none" stroke="{t["tick"]}" stroke-width="0.8" stroke-dasharray="3 4" />'
            f'<circle cx="{cx:.1f}" cy="{cy - 20:.1f}" r="1.9" fill="{t["ink1"]}" /></g>'
        )
        parts.append(
            f'<g><animateTransform attributeName="transform" type="rotate" from="-45 {cx:.1f} {cy:.1f}" to="315 {cx:.1f} {cy:.1f}" dur="64s" repeatCount="indefinite" />'
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="42" ry="18" fill="none" stroke="{t["wire"]}" stroke-opacity="0.18" stroke-width="0.7" />'
            f'<circle cx="{cx + 42:.1f}" cy="{cy:.1f}" r="1.6" fill="{t["ink2"]}" /></g>'
        )
        # Central crystalline diamond
        parts.append(
            f'<polygon points="{cx:.1f},{cy - 11:.1f} {cx + 11:.1f},{cy:.1f} {cx:.1f},{cy + 11:.1f} {cx - 11:.1f},{cy:.1f}" '
            f'fill="{t["surface2"]}" stroke="{t["ink1"]}" stroke-width="1.0" />'
        )
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.4" fill="{t["ink1"]}" />')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 17:.1f}" class="motif-lbl">TAURI 2 · RUST</text>')

    return "".join(parts)


def build_works(theme_name: str, cfg: dict[str, Any], repo_meta: dict[str, dict[str, Any]]) -> str:
    t = THEMES[theme_name]
    works = cfg["flagshipWorks"][:4]
    W, H = 1000, 444

    cards_svg: list[str] = []
    for idx, w in enumerate(works):
        col = idx % 2
        row = idx // 2
        x0 = col * 500.0
        y0 = 40.0 + row * 202.0
        live = repo_meta.get(w["repo"], {})
        stars = live.get("stars", w.get("fallbackStars", 0))
        lang = live.get("language") or w.get("fallbackLang", "TypeScript")
        status = "LIVE DEMO ↗" if w.get("demo") else "OPEN SOURCE ↗"

        desc_lines = wrap_lines(w["summary"], max_chars=43, max_lines=3)
        desc_svg = "".join(
            f'<text x="{x0 + 26:.1f}" y="{y0 + 88 + li * 17:.1f}" class="w-desc">{esc(line)}</text>'
            for li, line in enumerate(desc_lines)
        )

        # Left editorial metadata + Right bespoke animated particle artwork
        cards_svg.append(
            f'<g>'
            f'<text x="{x0 + 26:.1f}" y="{y0 + 30:.1f}" class="w-cat">{esc(w["index"])} // {esc(w["category"])}</text>'
            f'<text x="{x0 + 26:.1f}" y="{y0 + 62:.1f}" class="w-title">{esc(w["title"])}</text>'
            f'{desc_svg}'
            f'<line x1="{x0 + 26:.1f}" y1="{y0 + 152:.1f}" x2="{x0 + 296:.1f}" y2="{y0 + 152:.1f}" stroke="{t["hairline"]}" stroke-width="0.75" />'
            f'<circle cx="{x0 + 30:.1f}" cy="{y0 + 170:.1f}" r="2.6" fill="{t["ink1"]}" />'
            f'<text x="{x0 + 38:.1f}" y="{y0 + 173.5:.1f}" class="w-meta">{esc(lang)}</text>'
            f'<text x="{x0 + 132:.1f}" y="{y0 + 173.5:.1f}" class="w-meta">★ {stars}</text>'
            f'<text x="{x0 + 296:.1f}" y="{y0 + 173.5:.1f}" text-anchor="end" class="w-meta-dim">{status}</text>'
            f'{render_work_motif(w["motif"], x0 + 314, y0 + 24, 162, 154, t)}'
            f'</g>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Selected Flagship Engineering Works">
  <defs>
    <clipPath id="works-clip">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" />
    </clipPath>
    <style>
      .hdr-mono {{ font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: 1.5px; fill: {t["ink3"]}; }}
      .w-cat {{ font-family: {FONT_MONO}; font-size: 9px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .w-title {{ font-family: {FONT_DISPLAY}; font-size: 23px; font-weight: 600; letter-spacing: -0.7px; fill: {t["ink1"]}; }}
      .w-desc {{ font-family: {FONT_BODY}; font-size: 11.8px; fill: {t["ink2"]}; }}
      .w-meta {{ font-family: {FONT_MONO}; font-size: 10px; font-weight: 500; fill: {t["ink1"]}; }}
      .w-meta-dim {{ font-family: {FONT_MONO}; font-size: 9.2px; letter-spacing: 0.9px; fill: {t["ink3"]}; }}
      .motif-lbl {{ font-family: {FONT_MONO}; font-size: 7.8px; letter-spacing: 1.2px; fill: {t["ink3"]}; }}

      .m-p1 {{ animation: mpFloat 5.0s ease-in-out infinite; }}
      .m-p2 {{ animation: mpFloat 6.2s ease-in-out infinite 0.9s; }}
      .m-p3 {{ animation: mpFloat 7.0s ease-in-out infinite 1.8s; }}
      .m-p4 {{ animation: mpFloat 5.6s ease-in-out infinite 2.5s; }}
      .m-blink {{ animation: blinkCur 1.2s steps(2, start) infinite; }}

      .route-pkt {{ stroke-dasharray: 10 80; }}
      .rp1 {{ animation: rMove 2.8s linear infinite; }}
      .rp2 {{ animation: rMove 3.2s linear infinite 0.7s; }}
      .rp3 {{ animation: rMove 2.6s linear infinite 1.4s; }}
      .rp4 {{ animation: rMove 3.0s linear infinite 2.1s; }}

      @keyframes mpFloat {{
        0%, 100% {{ transform: translateY(0px); opacity: 0.9; }}
        50% {{ transform: translateY(-3.2px); opacity: 0.35; }}
      }}
      @keyframes blinkCur {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.1; }}
      }}
      @keyframes rMove {{
        0% {{ stroke-dashoffset: 90; }}
        100% {{ stroke-dashoffset: 0; }}
      }}
    </style>
  </defs>

  <g clip-path="url(#works-clip)">
    <rect width="{W}" height="{H}" fill="{t["bg"]}" />

    <!-- Header Strip -->
    <line x1="0" y1="40" x2="{W}" y2="40" stroke="{t["hairline"]}" stroke-width="0.9" />
    <text x="24" y="24" class="hdr-mono">SELECTED EXHIBITION // FLAGSHIP REPOSITORIES</text>
    <text x="976" y="24" text-anchor="end" class="hdr-mono">04 FEATURED · LIVE STAR SYNC</text>

    <!-- 2x2 Architectural Dividers -->
    <line x1="500" y1="40" x2="500" y2="{H}" stroke="{t["hairline"]}" stroke-width="0.9" />
    <line x1="0" y1="242" x2="{W}" y2="242" stroke="{t["hairline"]}" stroke-width="0.9" />

    {"".join(cards_svg)}

    <!-- Precision Crosshairs -->
    {crosshair(500, 40, 4.5, t["tick"])}
    {crosshair(500, 242, 5.0, t["tick"])}
    {corner_brackets(W, H, 10, 8, t["tick"], 0.55)}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" />
</svg>'''


# ─────────────────────────────────────────────────────────────────────────────
# 5. TELEMETRY OBSERVATORY — Self-Hosted Monochrome Instrument Panel
# ─────────────────────────────────────────────────────────────────────────────
def build_telemetry(theme_name: str, cfg: dict[str, Any], telemetry: dict[str, Any]) -> str:
    t = THEMES[theme_name]
    W, H = 1000, 496

    tot_contrib = telemetry.get("totalContributions", 2993)
    yr_contrib = telemetry.get("yearlyContributions", 2816)
    cur_streak = telemetry.get("currentStreak", 13)
    max_streak = telemetry.get("longestStreak", 15)
    total_prs = telemetry.get("totalPRs", 157)
    total_issues = telemetry.get("totalIssues", 21)
    pub_repos = telemetry.get("publicRepos", 74)
    orig_repos = telemetry.get("originalRepos", 56)
    tot_stars = telemetry.get("totalStars", 155)
    followers = telemetry.get("followers", 10)
    rank = telemetry.get("rank", "A")
    updated = telemetry.get("updatedAt", dt.datetime.now(dt.timezone.utc).strftime("%Y.%m.%d"))
    languages = telemetry.get("languages", cfg["fallbackTelemetry"]["languages"])[:8]
    contrib_days: list[dict[str, Any]] = telemetry.get("contributionDays", [])
    hourly_rhythm: list[int] = telemetry.get("hourlyRhythm", [])

    # ── KPI Circular Grade Gauge (x=900, y=99) ──
    gcx, gcy, gr = 900.0, 99.0, 34.0
    circ = 2.0 * math.pi * gr
    fill_ratio = 0.86 if rank in ("A+", "S", "A++") else (0.78 if rank == "A" else 0.68)
    dash_filled = circ * fill_ratio
    dash_gap = circ - dash_filled
    gauge_ticks = []
    for deg in range(0, 360, 15):
        a = math.radians(deg)
        r1 = gr + 5.5
        r2 = gr + (9.0 if deg % 90 == 0 else 7.2)
        gauge_ticks.append(
            f"M {gcx + r1 * math.cos(a):.1f},{gcy + r1 * math.sin(a):.1f} "
            f"L {gcx + r2 * math.cos(a):.1f},{gcy + r2 * math.sin(a):.1f}"
        )

    # ── Real 52-Week × 7-Day Contribution Dot Matrix ──
    # Normalize to exact 53×7 grid (371 days)
    if len(contrib_days) < 350:
        # Deterministic realistic fallback if offline
        rng = random.Random(20261128)
        contrib_days = []
        base = dt.date(2025, 11, 23)
        for d_i in range(371):
            dd = base + dt.timedelta(days=d_i)
            lv = rng.choices([0, 1, 2, 3, 4], weights=[45, 25, 16, 9, 5])[0]
            contrib_days.append({"date": dd.isoformat(), "level": lv, "count": lv * 14})

    # Ensure trailing 371 days aligned to 53 columns × 7 rows
    cells = contrib_days[-371:]
    cols = (len(cells) + 6) // 7
    pitch_x = 17.2
    pitch_y = 14.5
    grid_w = (cols - 1) * pitch_x + 11.0
    start_x = (W - grid_w) / 2.0
    start_y = 200.0

    matrix_elems: list[str] = []
    month_labels: list[str] = []
    seen_months: set[tuple[int, int]] = set()
    last_month_x = -999.0
    month_names = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    for idx, day in enumerate(cells):
        c = idx // 7
        r = idx % 7
        cx = start_x + c * pitch_x
        cy = start_y + r * pitch_y
        lv = max(0, min(4, int(day.get("level", 0))))
        fill = t["heat"][lv]
        cls = ' class="peak-cell"' if lv == 4 else ""
        matrix_elems.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="11.2" height="10.2" rx="2.2" fill="{fill}"{cls} />')

        if r == 0 and c >= 1 and c < cols - 1:
            try:
                y_m = day["date"].split("-")
                ym_key = (int(y_m[0]), int(y_m[1]))
                if ym_key not in seen_months:
                    seen_months.add(ym_key)
                    if cx - last_month_x >= 44.0:
                        last_month_x = cx
                        month_labels.append(
                            f'<text x="{cx:.1f}" y="{start_y + 7 * pitch_y + 13:.1f}" class="axis-lbl">{month_names[ym_key[1]]}</text>'
                        )
            except Exception:
                pass

    # Legend swatches
    legend_elems = []
    for lv in range(5):
        lx = 860 + lv * 14.5
        legend_elems.append(f'<rect x="{lx:.1f}" y="175" width="9.5" height="9.5" rx="2" fill="{t["heat"][lv]}" />')

    # ── Language Spectrum Bar & Tabular Legend (x=26..534) ──
    bar_x, bar_y, bar_w, bar_h = 26.0, 376.0, 508.0, 10.0
    total_pct = sum(float(l.get("percent", 0)) for l in languages) or 100.0
    lang_bars: list[str] = []
    lang_legend: list[str] = []
    cur_x = bar_x
    gap = 1.6
    usable_w = bar_w - gap * max(0, len(languages) - 1)
    for i, lang in enumerate(languages):
        pct = float(lang.get("percent", 0))
        seg_w = max(4.0, usable_w * (pct / total_pct))
        if cur_x + seg_w > bar_x + bar_w:
            seg_w = max(2.0, bar_x + bar_w - cur_x)
        color = t["langs"][i % len(t["langs"])]
        lang_bars.append(f'<rect x="{cur_x:.1f}" y="{bar_y:.1f}" width="{seg_w:.1f}" height="{bar_h:.1f}" rx="1.8" fill="{color}" />')
        cur_x += seg_w + gap

        lcol = i % 2
        lrow = i // 2
        lx = 26.0 + lcol * 260.0
        ly = 411.0 + lrow * 21.0
        lang_legend.append(
            f'<rect x="{lx:.1f}" y="{ly - 8:.1f}" width="7.5" height="7.5" rx="1.5" fill="{color}" stroke="{t["border"]}" stroke-width="0.4" />'
            f'<text x="{lx + 14:.1f}" y="{ly:.1f}" class="lang-name">{esc(lang["name"])}</text>'
            f'<text x="{lx + 236:.1f}" y="{ly:.1f}" text-anchor="end" class="lang-pct">{pct:.2f}%</text>'
        )

    # ── 24-Hour Circadian Coding Rhythm (x=584..974) ──
    if len(hourly_rhythm) != 24 or sum(hourly_rhythm) == 0:
        # Authentic developer UTC+8 circadian distribution
        hourly_rhythm = [18, 12, 6, 3, 2, 2, 4, 9, 16, 28, 42, 46, 34, 38, 52, 58, 61, 49, 44, 56, 68, 74, 58, 34]
    max_hr = max(hourly_rhythm) or 1
    rx0, ry_base, rw, rh = 586.0, 456.0, 386.0, 74.0
    hr_step = rw / 23.0
    hr_bars: list[str] = []
    curve_pts: list[tuple[float, float]] = []
    for h_idx, val in enumerate(hourly_rhythm):
        ratio = val / max_hr
        bh = max(4.0, ratio * rh)
        bx = rx0 + h_idx * hr_step
        by = ry_base - bh
        curve_pts.append((bx, by))
        op = 0.20 + 0.72 * ratio
        hr_bars.append(
            f'<line x1="{bx:.1f}" y1="{ry_base:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{t["ink1"]}" stroke-opacity="{op:.2f}" stroke-width="3.2" stroke-linecap="round" />'
        )
        if ratio >= 0.78:
            hr_bars.append(f'<circle cx="{bx:.1f}" cy="{by - 6:.1f}" r="1.7" fill="{t["ink1"]}" class="peak-cell" />')

    curve_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in curve_pts)
    area_str = f"{rx0:.1f},{ry_base:.1f} {curve_str} {rx0 + 23 * hr_step:.1f},{ry_base:.1f}"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="GitHub Telemetry Observatory for AlkaidSTART">
  <defs>
    <clipPath id="tel-clip">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" />
    </clipPath>
    <clipPath id="matrix-clip">
      <rect x="{start_x - 4:.1f}" y="{start_y - 4:.1f}" width="{grid_w + 8:.1f}" height="{7 * pitch_y + 4:.1f}" />
    </clipPath>
    <linearGradient id="radar-beam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{t["scan_color"]}" stop-opacity="0" />
      <stop offset="50%" stop-color="{t["scan_color"]}" stop-opacity="{t["scan_op"]}" />
      <stop offset="100%" stop-color="{t["scan_color"]}" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="rhythm-fill" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{t["ink1"]}" stop-opacity="0.14" />
      <stop offset="100%" stop-color="{t["ink1"]}" stop-opacity="0.0" />
    </linearGradient>
    <style>
      .hdr-mono {{ font-family: {FONT_MONO}; font-size: 9.5px; letter-spacing: 1.5px; fill: {t["ink3"]}; }}
      .kpi-lbl {{ font-family: {FONT_MONO}; font-size: 9px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .kpi-num {{ font-family: {FONT_DISPLAY}; font-size: 33px; font-weight: 600; letter-spacing: -1.4px; fill: {t["ink1"]}; }}
      .kpi-sub {{ font-family: {FONT_MONO}; font-size: 9.5px; fill: {t["ink2"]}; }}
      .rank-num {{ font-family: {FONT_DISPLAY}; font-size: 24px; font-weight: 600; fill: {t["ink1"]}; }}
      .rank-sub {{ font-family: {FONT_MONO}; font-size: 7.5px; letter-spacing: 1.2px; fill: {t["ink3"]}; }}
      .sec-lbl {{ font-family: {FONT_MONO}; font-size: 9.2px; letter-spacing: 1.4px; fill: {t["ink3"]}; }}
      .axis-lbl {{ font-family: {FONT_MONO}; font-size: 8.5px; letter-spacing: 0.8px; fill: {t["ink3"]}; }}
      .lang-name {{ font-family: {FONT_MONO}; font-size: 10.2px; fill: {t["ink1"]}; }}
      .lang-pct {{ font-family: {FONT_MONO}; font-size: 10px; fill: {t["ink3"]}; }}

      .radar-sweep {{ animation: sweepX 11s linear infinite; }}
      .peak-cell {{ animation: cellGlow 3.6s ease-in-out infinite; }}
      .rhythm-pulse {{ stroke-dasharray: 24 420; animation: rhythmTrace 6s linear infinite; }}
      .spark-flow {{ stroke-dasharray: 18 140; animation: sparkMove 4.5s linear infinite; }}

      @keyframes sweepX {{
        0% {{ transform: translateX({start_x - 70:.1f}px); }}
        100% {{ transform: translateX({start_x + grid_w + 30:.1f}px); }}
      }}
      @keyframes cellGlow {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.45; }}
      }}
      @keyframes rhythmTrace {{
        0% {{ stroke-dashoffset: 444; }}
        100% {{ stroke-dashoffset: 0; }}
      }}
      @keyframes sparkMove {{
        0% {{ stroke-dashoffset: 158; }}
        100% {{ stroke-dashoffset: 0; }}
      }}
    </style>
  </defs>

  <g clip-path="url(#tel-clip)">
    <rect width="{W}" height="{H}" fill="{t["bg"]}" />

    <!-- Header Strip -->
    <line x1="0" y1="38" x2="{W}" y2="38" stroke="{t["hairline"]}" stroke-width="0.9" />
    <text x="24" y="23" class="hdr-mono">GITHUB OBSERVATORY // LIVE TELEMETRY &amp; CONTRIBUTION MATRIX</text>
    <text x="976" y="23" text-anchor="end" class="hdr-mono">SYNCED {esc(updated)} · @ALKAIDSTART</text>

    <!-- Row 1: 5-Column Precision KPI Strip (y=38..158) -->
    <line x1="0" y1="158" x2="{W}" y2="158" stroke="{t["hairline"]}" stroke-width="0.9" />
    <line x1="200" y1="38" x2="200" y2="158" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="400" y1="38" x2="400" y2="158" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="600" y1="38" x2="600" y2="158" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="800" y1="38" x2="800" y2="158" stroke="{t["hairline"]}" stroke-width="0.85" />

    <!-- KPI 1: Contributions -->
    <text x="24" y="64" class="kpi-lbl">CONTRIBUTIONS</text>
    <text x="24" y="106" class="kpi-num">{tot_contrib:,}</text>
    <text x="24" y="130" class="kpi-sub">{yr_contrib:,} in last 12m</text>
    <polyline points="132,102 142,96 151,99 162,84 172,88 184,70" fill="none" stroke="{t["tick"]}" stroke-width="1.0" />
    <polyline points="132,102 142,96 151,99 162,84 172,88 184,70" fill="none" stroke="{t["ink1"]}" stroke-width="1.4" class="spark-flow" />

    <!-- KPI 2: Streak -->
    <text x="224" y="64" class="kpi-lbl">STREAK VELOCITY</text>
    <text x="224" y="106" class="kpi-num">{cur_streak}d</text>
    <circle cx="364" cy="60.5" r="2.6" fill="{t["ink1"]}" class="peak-cell" />
    <text x="224" y="130" class="kpi-sub">Longest {max_streak}d · Active</text>

    <!-- KPI 3: Pull Requests & Repos -->
    <text x="424" y="64" class="kpi-lbl">PULL REQUESTS</text>
    <text x="424" y="106" class="kpi-num">{total_prs}</text>
    <text x="424" y="130" class="kpi-sub">{total_issues} Issues · {pub_repos} Repos</text>

    <!-- KPI 4: Stars & Reach -->
    <text x="624" y="64" class="kpi-lbl">STARS EARNED</text>
    <text x="624" y="106" class="kpi-num">{tot_stars}</text>
    <text x="624" y="130" class="kpi-sub">{orig_repos} Original · {followers} Followers</text>

    <!-- KPI 5: Precision Rank Gauge -->
    <path d="{" ".join(gauge_ticks)}" fill="none" stroke="{t["tick"]}" stroke-width="0.75" />
    <circle cx="{gcx:.1f}" cy="{gcy:.1f}" r="{gr:.1f}" fill="none" stroke="{t["surface2"]}" stroke-width="3.2" />
    <circle cx="{gcx:.1f}" cy="{gcy:.1f}" r="{gr:.1f}" fill="none" stroke="{t["ink1"]}" stroke-width="3.2"
            stroke-dasharray="{dash_filled:.1f} {dash_gap:.1f}" stroke-linecap="round"
            transform="rotate(-90 {gcx:.1f} {gcy:.1f})" />
    <g>
      <animateTransform attributeName="transform" type="rotate" from="0 {gcx:.1f} {gcy:.1f}" to="360 {gcx:.1f} {gcy:.1f}" dur="18s" repeatCount="indefinite" />
      <circle cx="{gcx:.1f}" cy="{gcy - gr - 11.5:.1f}" r="1.7" fill="{t["ink1"]}" />
    </g>
    <text x="{gcx:.1f}" y="{gcy + 4:.1f}" text-anchor="middle" class="rank-num">{esc(rank)}</text>
    <text x="{gcx:.1f}" y="{gcy + 17:.1f}" text-anchor="middle" class="rank-sub">GRADE</text>

    <!-- Row 2: 52-Week Monochrome Contribution Particle Matrix (y=158..332) -->
    <line x1="0" y1="332" x2="{W}" y2="332" stroke="{t["hairline"]}" stroke-width="0.9" />
    <text x="24" y="183" class="sec-lbl">CONTRIBUTION DENSITY MATRIX · 52 WEEKS · {yr_contrib:,} RECORDED</text>
    <text x="850" y="183" text-anchor="end" class="axis-lbl">LESS</text>
    {"".join(legend_elems)}
    <text x="940" y="183" class="axis-lbl">MORE</text>

    {"".join(matrix_elems)}
    {"".join(month_labels)}

    <!-- Radar Scanline Sweep over Matrix -->
    <g clip-path="url(#matrix-clip)">
      <rect x="0" y="{start_y - 4:.1f}" width="64" height="{7 * pitch_y + 4:.1f}" fill="url(#radar-beam)" class="radar-sweep" />
    </g>

    <!-- Row 3: Dual Instrument Panel (y=332..496) -->
    <line x1="560" y1="332" x2="560" y2="{H}" stroke="{t["hairline"]}" stroke-width="0.9" />

    <!-- Left: Language Composition Spectrum -->
    <text x="26" y="360" class="sec-lbl">LANGUAGE SPECTRUM // CODEBASE DISTRIBUTION</text>
    {"".join(lang_bars)}
    {"".join(lang_legend)}

    <!-- Right: 24h Circadian Coding Rhythm -->
    <text x="586" y="360" class="sec-lbl">CIRCADIAN RHYTHM // UTC+8 HOURLY PULSE</text>
    <line x1="{rx0:.1f}" y1="{ry_base:.1f}" x2="{rx0 + rw:.1f}" y2="{ry_base:.1f}" stroke="{t["hairline"]}" stroke-width="0.85" />
    <line x1="{rx0:.1f}" y1="{ry_base - rh * 0.5:.1f}" x2="{rx0 + rw:.1f}" y2="{ry_base - rh * 0.5:.1f}" stroke="{t["hairline"]}" stroke-width="0.6" stroke-dasharray="2 4" />
    <polygon points="{area_str}" fill="url(#rhythm-fill)" />
    {"".join(hr_bars)}
    <polyline points="{curve_str}" fill="none" stroke="{t["ink2"]}" stroke-opacity="0.45" stroke-width="0.9" />
    <polyline points="{curve_str}" fill="none" stroke="{t["ink1"]}" stroke-width="1.5" stroke-linecap="round" class="rhythm-pulse" />

    <text x="{rx0:.1f}" y="474" class="axis-lbl">00:00</text>
    <text x="{rx0 + 6 * hr_step:.1f}" y="474" text-anchor="middle" class="axis-lbl">06:00</text>
    <text x="{rx0 + 12 * hr_step:.1f}" y="474" text-anchor="middle" class="axis-lbl">12:00</text>
    <text x="{rx0 + 18 * hr_step:.1f}" y="474" text-anchor="middle" class="axis-lbl">18:00</text>
    <text x="{rx0 + 23 * hr_step:.1f}" y="474" text-anchor="end" class="axis-lbl">23:00</text>

    <!-- Precision Crosshairs & Corner Registration -->
    {crosshair(200, 158, 3.8, t["tick"])}
    {crosshair(400, 158, 3.8, t["tick"])}
    {crosshair(600, 158, 3.8, t["tick"])}
    {crosshair(800, 158, 3.8, t["tick"])}
    {crosshair(560, 332, 4.5, t["tick"])}
    {corner_brackets(W, H, 10, 8, t["tick"], 0.55)}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" />
</svg>'''


# ─────────────────────────────────────────────────────────────────────────────
# 6. FOOTER — Atmospheric Particle Horizon & Celestial Colophon
# ─────────────────────────────────────────────────────────────────────────────
def build_footer(theme_name: str, cfg: dict[str, Any]) -> str:
    t = THEMES[theme_name]
    ident = cfg["identity"]
    W, H = 1000, 196
    horizon_y = 112.0

    # Rising stardust particle mist clustered softly around the horizon line
    rng = random.Random(202699)
    mist: list[str] = []
    for i in range(115):
        px = rng.uniform(22, W - 22)
        # Gaussian vertical clustering right above horizon line
        dy = abs(rng.gauss(0, 34))
        py = max(14.0, horizon_y - dy)
        dist_center = abs(px - W / 2.0) / (W / 2.0)
        rad = rng.uniform(0.45, 1.35) * (1.15 - 0.35 * dist_center)
        op = rng.uniform(0.10, 0.56) * (1.0 - min(0.75, dy / 108.0))
        cls = f"r{(i % 5) + 1}"
        mist.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{rad:.2f}" fill="{t["particle"]}" fill-opacity="{op:.2f}" class="{cls}" />'
        )

    # Fine converging horizon perspective hairlines
    persp_lines = []
    for dx in (-380, -260, -150, -60, 60, 150, 260, 380):
        persp_lines.append(
            f'<line x1="500" y1="60" x2="{500 + dx}" y2="{horizon_y:.1f}" stroke="{t["wire"]}" stroke-opacity="0.045" stroke-width="0.6" />'
        )

    # Subtle harmonic particle horizon wave ribbon right above horizon_y
    wave_pts = []
    wave_dots = []
    for k in range(56):
        u = k / 55.0
        wx = 30.0 + u * (W - 60.0)
        wy = horizon_y - 16.0 - 11.0 * math.sin(u * math.pi * 2.4) * math.sin(u * math.pi)
        wave_pts.append(f"{wx:.1f},{wy:.1f}")
        rad = 0.65 + 0.75 * math.sin(u * math.pi)
        op = 0.14 + 0.44 * math.sin(u * math.pi)
        wave_dots.append(
            f'<circle cx="{wx:.1f}" cy="{wy:.1f}" r="{rad:.2f}" fill="{t["particle"]}" fill-opacity="{op:.2f}" class="r{(k % 5) + 1}" />'
        )
    wave_poly = f'<polyline points="{" ".join(wave_pts)}" fill="none" stroke="{t["wire"]}" stroke-opacity="0.09" stroke-width="0.65" />'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Alkaid Colophon">
  <defs>
    <clipPath id="foot-clip">
      <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" />
    </clipPath>
    <radialGradient id="foot-glow" cx="50%" cy="56%" r="44%">
      <stop offset="0%" stop-color="{t["particle"]}" stop-opacity="{t["glow_op"]}" />
      <stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="foot-beam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{t["ink1"]}" stop-opacity="0" />
      <stop offset="50%" stop-color="{t["ink1"]}" stop-opacity="0.85" />
      <stop offset="100%" stop-color="{t["ink1"]}" stop-opacity="0" />
    </linearGradient>
    <style>
      .f-quote-zh-main {{ font-family: {FONT_SERIF}; font-size: 13px; font-style: normal; letter-spacing: 1.0px; fill: {t["ink1"]}; }}
      .f-quote-en {{ font-family: {FONT_SERIF}; font-size: 13.5px; font-style: italic; fill: {t["ink2"]}; }}
      .f-quote-zh {{ font-family: {FONT_BODY}; font-size: 11px; letter-spacing: 0.9px; fill: {t["ink3"]}; }}
      .f-meta {{ font-family: {FONT_MONO}; font-size: 9px; letter-spacing: 1.5px; fill: {t["ink3"]}; }}

      .r1 {{ animation: riseA 6.5s ease-in-out infinite; }}
      .r2 {{ animation: riseB 8.0s ease-in-out infinite 1.1s; }}
      .r3 {{ animation: riseA 9.4s ease-in-out infinite 2.2s; }}
      .r4 {{ animation: riseB 7.2s ease-in-out infinite 3.3s; }}
      .r5 {{ animation: riseA 10.5s ease-in-out infinite 0.5s; }}
      .f-glint {{ animation: fSlide 8.5s cubic-bezier(0.45, 0, 0.55, 1) infinite; }}
      .star-breathe {{ animation: starPulse 4.5s ease-in-out infinite; }}

      @keyframes riseA {{
        0%, 100% {{ transform: translateY(0px); opacity: 0.9; }}
        50% {{ transform: translateY(-7px); opacity: 0.22; }}
      }}
      @keyframes riseB {{
        0%, 100% {{ transform: translate(0px, 0px); opacity: 0.85; }}
        50% {{ transform: translate(1.8px, -9px); opacity: 0.18; }}
      }}
      @keyframes fSlide {{
        0% {{ transform: translateX(-140px); opacity: 0; }}
        15% {{ opacity: 0.9; }}
        85% {{ opacity: 0.9; }}
        100% {{ transform: translateX(1060px); opacity: 0; }}
      }}
      @keyframes starPulse {{
        0%, 100% {{ opacity: 0.85; }}
        50% {{ opacity: 0.25; }}
      }}
    </style>
  </defs>

  <g clip-path="url(#foot-clip)">
    <rect width="{W}" height="{H}" fill="{t["bg"]}" />
    <rect width="{W}" height="{H}" fill="url(#foot-glow)" />

    {"".join(persp_lines)}
    {wave_poly}
    {"".join(wave_dots)}
    {"".join(mist)}

    <!-- Celestial Alkaid Emblem above Horizon -->
    <g>
      <circle cx="500" cy="58" r="22" fill="none" stroke="{t["tick"]}" stroke-width="0.7" stroke-dasharray="2 5" class="star-breathe" />
      <g>
        <animateTransform attributeName="transform" type="rotate" from="0 500 58" to="360 500 58" dur="55s" repeatCount="indefinite" />
        <polygon points="500,43 515,58 500,73 485,58" fill="none" stroke="{t["ink2"]}" stroke-width="0.8" stroke-opacity="0.55" />
      </g>
      <path d="M 500,49 L 502.2,55.8 L 509,58 L 502.2,60.2 L 500,67 L 497.8,60.2 L 491,58 L 497.8,55.8 Z" fill="{t["ink1"]}" />
    </g>

    <!-- Horizon Datum Line + Calibration Ticks + Glint -->
    <line x1="0" y1="{horizon_y:.1f}" x2="{W}" y2="{horizon_y:.1f}" stroke="{t["hairline"]}" stroke-width="0.9" />
    {ruler_ticks(40, 960, horizon_y, 20, 3.0, t["tick"], 0.45)}
    <rect x="0" y="{horizon_y - 0.6:.1f}" width="120" height="1.2" fill="url(#foot-beam)" class="f-glint" />
    {crosshair(500, horizon_y, 4.5, t["tick"])}

    <!-- Editorial Colophon -->
    <text x="500" y="142" text-anchor="middle"><tspan class="f-quote-zh-main">「{esc(ident["quote"])}」</tspan><tspan class="f-quote-en">  ·  Gaze at the stars, yet stay grounded.</tspan></text>
    <text x="500" y="164" text-anchor="middle" class="f-quote-zh">{esc(ident["philosophy"])}</text>

    <text x="26" y="184" class="f-meta">ALKAIDSTART // {esc(ident["location"])}</text>
    <text x="500" y="184" text-anchor="middle" class="f-meta">η URSAE MAJORIS · ORDER AGAINST ENTROPY</text>
    <text x="974" y="184" text-anchor="end" class="f-meta">ALKAID.LIVE · MIT</text>

    {corner_brackets(W, H, 10, 8, t["tick"], 0.55)}
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}" stroke-width="1" />
</svg>'''


def generate_all(telemetry: dict[str, Any] | None = None) -> list[Path]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if telemetry is None:
        if DATA_CACHE_PATH.exists():
            telemetry = json.loads(DATA_CACHE_PATH.read_text(encoding="utf-8"))
        else:
            telemetry = dict(cfg["fallbackTelemetry"])

    repo_meta = telemetry.get("repoMeta", {})
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    dividers = [
        ("01", "ARCHITECTURE & SYSTEM TOPOLOGY", "SYS.SPEC.01"),
        ("02", "SELECTED WORKS & ENGINEERING LABS", "WORKS.INDEX.02"),
        ("03", "TELEMETRY OBSERVATORY & LIVE PULSE", "OBSERVATORY.03"),
        ("04", "WRITING, PHILOSOPHY & OPEN CHANNELS", "JOURNAL.NET.04"),
    ]

    written: list[Path] = []
    for theme in ("dark", "light"):
        files = {
            f"hero-{theme}.svg": build_hero(theme, cfg, telemetry),
            f"architecture-{theme}.svg": build_architecture(theme, cfg),
            f"works-{theme}.svg": build_works(theme, cfg, repo_meta),
            f"telemetry-{theme}.svg": build_telemetry(theme, cfg, telemetry),
            f"footer-{theme}.svg": build_footer(theme, cfg),
        }
        for idx, title, code in dividers:
            files[f"divider-{idx}-{theme}.svg"] = build_divider(theme, idx, title, code)

        for fname, svg_content in files.items():
            out_path = ASSETS_DIR / fname
            out_path.write_text(svg_content, encoding="utf-8")
            written.append(out_path)

    return written


def main() -> None:
    written = generate_all()
    total_kb = sum(p.stat().st_size for p in written) / 1024.0
    print(f"[+] Generated {len(written)} monochrome animated SVGs ({total_kb:.1f} KB total) in {ASSETS_DIR}")


if __name__ == "__main__":
    main()
