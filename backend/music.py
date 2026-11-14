"""Procedural music generation (numpy). Deterministic per seed/params; writes 16-bit mono WAV."""
import numpy as np, wave, random
SR = 22050
SC = {"EXCELLENT": [0, 2, 4, 7, 9], "GOOD": [0, 2, 4, 5, 7, 9, 11], "MODERATE": [0, 2, 3, 5, 7, 9, 10], "POOR": [0, 1, 3, 5, 7, 8, 10], "CRITICAL": [0, 1, 3, 5, 6, 8, 10]}
TENS = {"EXCELLENT": .0, "GOOD": .1, "MODERATE": .35, "POOR": .6, "CRITICAL": .9}

def tone(f, d, amp, hn):
    n = int(d * SR); x = np.arange(n) / SR
    w = sum(np.sin(2 * np.pi * f * (k + 1) * x) / (k + 1) ** 1.4 for k in range(hn))
    env = np.exp(-x * (1.2 if d < 3 else .4)); a = max(1, int(min(.04, d / 4) * SR)); r = max(1, int(min(.5, d / 2) * SR))
    env[:a] *= np.linspace(0, 1, a); env[-r:] *= np.linspace(1, 0, r)
    return amp * w * env

def voice(out, p, secs):
    rng = random.Random(p["seed"]); sc = SC[p["level"]]; ten = TENS[p["level"]]
    root = 45 + int(min(max(p["temp_c"], 0), 35) / 35 * 9) + p.get("shift", 0)
    tempo = (62 if p["level"] == "EXCELLENT" else 72) + p["rain_cv"] * 40; beat = 60 / tempo
    rest = min(.6, p["rain_cv"] * .35 + (1 - p["wetness"]) * .25); hn = 2 + int((1 - min(1, p["wetness"])) * 5)
    f = lambda m: 440 * 2 ** ((m - 69) / 12)
    t, deg, last_pad = 0.0, rng.randrange(len(sc)), -9
    durs = [1, 1, 2, 2] if ten < .3 else [.5, .75, 1, 1.5, .25]
    def pitch(d): return root + 12 + sc[d % len(sc)] + 12 * (d // len(sc))
    while t < secs:
        tn = min(1, max(0, ten - p["trend"] * 4 * t / secs))
        if t - last_pad >= 4 * beat:
            last_pad = t; base = rng.choice([0, 2, 3, 4]); 
            for k in (0, 2, 4):
                add(out, t, tone(f(root - 12 + sc[(base + k) % len(sc)] + 12 * ((base + k) // len(sc))), 4 * beat * 1.1, .10, 3))
            if tn > .6: add(out, t, tone(f(root - 24 + 6), 4 * beat, .08 * tn, 2))
        d = rng.choice(durs) * beat
        if rng.random() > rest:
            m = pitch(deg)
            if rng.random() < tn * .45: m += rng.choice([1, -1, 6])
            add(out, t, tone(f(m), d * 1.4, .16, hn))
        deg = max(0, min(len(sc) * 2, deg + rng.choice([-2, -1, -1, 0, 1, 1, 2]))); t += d

def add(out, t, x):
    i = int(t * SR); out[i:i + len(x)] += x[:len(out) - i]

def render(voices, secs, path):
    out = np.zeros(int(secs * SR) + SR * 6, dtype=np.float64)
    for v in voices: voice(out, v, secs)
    out = out[:int(secs * SR)]; fd = SR * 2
    out[:fd] *= np.linspace(0, 1, fd); out[-fd:] *= np.linspace(1, 0, fd)
    out = out / (np.max(np.abs(out)) + 1e-9) * .85
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype("<i2").tobytes())

TITLES = {"EXCELLENT": ["The Green Symphony", "Morning Dew Canon", "Golden Harvest"], "GOOD": ["Warm Furrows", "Golden Harvest", "Quiet Ridge"],
          "MODERATE": ["After the Storm", "Shifting Winds", "The Last Rain"], "POOR": ["The Silent Field", "Dust Lullaby", "Thin Clouds"], "CRITICAL": ["Desert Echoes", "Cracked Earth", "The Long Drought"]}
