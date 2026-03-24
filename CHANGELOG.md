# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-03-24

### Added
- `tester.py` — core measurement engine: ping/jitter/packet loss, speed test, WiFi signal (RSSI/SNR)
- `main.py` — interactive terminal UI built with `rich`
- Full test (ping + WiFi + speed), quick test (ping + WiFi only), monitor mode, compare mode
- 0–100 video-call readiness scoring with A–F grades
- Save results to `results.json` and compare multiple locations side-by-side
- macOS WiFi info via `system_profiler`, Linux via `iwconfig`
