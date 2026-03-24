# WiFi Quality Tester

A terminal utility to **find the best spot in your home for WiFi calls** — test from different rooms while the router stays put, and compare signal strength, speed, ping, jitter, and packet loss side-by-side.

---

## What it measures

| Metric | Video Call Requirement | Why it matters |
|--------|------------------------|----------------|
| Download Speed | ≥ 3 Mbps (HD) | Receiving video/audio from others |
| Upload Speed | ≥ 3 Mbps (HD) | Sending your video/audio |
| Avg Ping | ≤ 150 ms | Conversation delay |
| Jitter | ≤ 30 ms | Choppy / robotic audio |
| Packet Loss | ≤ 1% | Frozen frames, dropped audio |
| WiFi Signal (RSSI) | ≥ −70 dBm | Reliable wireless link |

---

## Setup

```bash
cd wifi-quality-tester
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

Interactive menu launches automatically.

---

## Workflow — finding the best spot

Router stays in its fixed position. You walk to each room with your laptop/device and run a test.

1. Go to **Room A** (e.g. Living Room) with your device
2. Run **Option 1** (Full Test) → name it `Living Room`
3. Move to **Room B** (e.g. Bedroom) — router doesn't move
4. Run **Option 1** again → name it `Bedroom`
5. Repeat for as many rooms as you want
6. Run **Option 4** (Compare) → side-by-side table with ⭐ best values highlighted

---

## Menu options

| Option | What it does | Time |
|--------|-------------|------|
| 1 — Full test | Ping + WiFi signal + download/upload speed | ~60 s |
| 2 — Quick test | Ping + WiFi signal only (no speed test) | ~5 s |
| 3 — Monitor mode | Repeated pings to check connection stability over time | configurable |
| 4 — Compare locations | Side-by-side table of all saved results | instant |
| 5 — View saved results | Summary list of past tests | instant |
| 6 — Clear saved results | Delete results.json | instant |

---

## Scoring

Each test is scored **0–100** from a weighted combination of metrics:

| Component | Weight |
|-----------|--------|
| Ping | 25 % |
| Jitter | 20 % |
| Packet Loss | 20 % |
| Download Speed | 20 % |
| Upload Speed | 10 % |
| WiFi Signal | 5 % |

**Grades:** A (85+) · B (70+) · C (55+) · D (40+) · F (below 40)

---

## My Results

Router is fixed in one spot. Tested from 4 different rooms to find which position in the home gets the best WiFi for calls.

| Metric | Requirement | Office | Living Room | Kitchen | Balcony |
|--------|-------------|--------|-------------|---------|---------|
| Download | ≥ 3 Mbps | 99.84 Mbps ✓ | 102.36 Mbps ✓ ⭐ | 96.39 Mbps ✓ | 100.52 Mbps ✓ |
| Upload | ≥ 3 Mbps | 88.14 Mbps ✓ | 100.21 Mbps ✓ | 102.58 Mbps ✓ ⭐ | 100.82 Mbps ✓ |
| Avg Ping | ≤ 150 ms | 9.9 ms ✓ | 10.0 ms ✓ | 10.1 ms ✓ | 47.0 ms ✓ |
| Jitter | ≤ 30 ms | 0.8 ms ✓ | 0.4 ms ✓ ⭐ | 0.4 ms ✓ ⭐ | 63.0 ms ✗ ⚠️ |
| Packet Loss | ≤ 1% | 0.0% ✓ | 0.0% ✓ | 0.0% ✓ | 0.0% ✓ |
| WiFi Signal | ≥ −70 dBm | −69 dBm (Fair) | −42 dBm (Excellent) | −38 dBm (Excellent) ⭐ | −52 dBm (Good) |
| SNR | — | 21 dB | 47 dB | 53 dB ⭐ | 37 dB |
| Link Speed | — | 130 Mbps | 433 Mbps | 585 Mbps ⭐ | 585 Mbps ⭐ |
| **Score** | — | **97.3 / 100 (A)** | **99.8 / 100 (A)** | **99.8 / 100 (A) ⭐** | **74.5 / 100 (B)** |

### Key takeaways

- **Kitchen & Living Room are the best spots to sit** — both closest to the router, scoring 99.8/100 with Excellent signal, 0.4 ms jitter, and zero packet loss.
- **Kitchen has the strongest raw signal** (−38 dBm, SNR 53 dB) and highest link speed (585 Mbps), making it the top pick if you need maximum headroom.
- **Office is solid** (97.3/A) but it's the furthest room from the router — weakest signal (−69 dBm, Fair), only 1 dBm from the threshold, so it's more vulnerable during congestion or interference.
- **Balcony should be avoided for calls** — jitter spiked to 63 ms (2× over the 30 ms limit) with pings ranging 9–210 ms, likely due to walls/distance causing intermittent signal drops. Speed was fine but the instability would cause choppy audio.

> **Verdict:** Sit in the **Kitchen** or **Living Room** for meetings — closest to the router. Avoid the Balcony for anything real-time.

---

## Requirements

- Python 3.8+
- macOS or Linux (WiFi signal info uses `system_profiler` on macOS, `iwconfig` on Linux)
- Internet connection for speed test

---

## Files

```
wifi-quality-tester/
├── main.py          # CLI menus, display, comparison
├── tester.py        # Network measurement engine
├── requirements.txt
├── results.json     # Auto-created when you save a test
└── README.md
```
