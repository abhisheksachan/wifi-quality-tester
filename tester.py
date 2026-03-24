"""
tester.py — Network measurement engine for wifi-meet-tester
Handles: ping/latency, jitter, packet loss, speed test, WiFi signal strength
"""

import re
import platform
import statistics
import subprocess
from datetime import datetime
from typing import Callable, Optional


# ─── Video-call thresholds (used for scoring) ─────────────────────────────────
THRESHOLDS = {
    "download_mbps":  {"excellent": 25,  "good": 10,   "fair": 3,    "poor": 1},
    "upload_mbps":    {"excellent": 10,  "good": 5,    "fair": 3,    "poor": 0.5},
    "ping_ms":        {"excellent": 20,  "good": 50,   "fair": 100,  "poor": 150},
    "jitter_ms":      {"excellent": 5,   "good": 15,   "fair": 30,   "poor": 50},
    "packet_loss_pct":{"excellent": 0,   "good": 0.5,  "fair": 1,    "poor": 3},
    "rssi_dbm":       {"excellent": -50, "good": -60,  "fair": -70,  "poor": -80},
}

VIDEO_CALL_REQS = {
    "download_mbps":  3.0,
    "upload_mbps":    3.0,
    "ping_ms":        150,
    "jitter_ms":      30,
    "packet_loss_pct": 1.0,
    "rssi_dbm":       -70,
}


# ─── Ping / Latency ───────────────────────────────────────────────────────────

def run_ping_test(host: str = "8.8.8.8", count: int = 10) -> dict:
    """
    Send `count` ICMP pings to `host`.
    Returns avg, min, max, jitter (stddev), packet_loss_pct, sample count.
    """
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", str(count), host]
    else:
        # -i 0.2 → shorter interval so test finishes in ~3s instead of 10s
        cmd = ["ping", "-c", str(count), "-i", "0.2", host]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = proc.stdout

        # Parse individual RTT values (works on macOS, Linux, Windows)
        rtts = [float(t) for t in re.findall(r"time[=<](\d+\.?\d*)\s*ms", output)]

        if not rtts:
            return {"error": "No ping responses received — host unreachable?"}

        # Packet loss
        loss_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*packet loss", output)
        packet_loss = float(loss_match.group(1)) if loss_match else 0.0

        jitter = round(statistics.stdev(rtts), 1) if len(rtts) > 1 else 0.0

        return {
            "host": host,
            "avg_ms": round(statistics.mean(rtts), 1),
            "min_ms": round(min(rtts), 1),
            "max_ms": round(max(rtts), 1),
            "jitter_ms": jitter,
            "packet_loss_pct": packet_loss,
            "samples": len(rtts),
            "total_sent": count,
        }

    except subprocess.TimeoutExpired:
        return {"error": "Ping timed out after 60 seconds"}
    except Exception as exc:
        return {"error": f"Ping failed: {exc}"}


# ─── Speed Test ───────────────────────────────────────────────────────────────

def run_speed_test(progress_callback: Optional[Callable[[str], None]] = None) -> dict:
    """
    Measure download & upload speed via speedtest-cli.
    Calls progress_callback(msg) at each phase so the UI can update.
    """
    try:
        import speedtest  # pip install speedtest-cli

        s = speedtest.Speedtest(secure=True)

        if progress_callback:
            progress_callback("Finding best server…")
        s.get_best_server()

        if progress_callback:
            progress_callback("Testing download speed…")
        download_bps = s.download()

        if progress_callback:
            progress_callback("Testing upload speed…")
        upload_bps = s.upload()

        r = s.results.dict()
        server = r.get("server", {})

        return {
            "download_mbps": round(download_bps / 1_000_000, 2),
            "upload_mbps":   round(upload_bps   / 1_000_000, 2),
            "server_name":    server.get("name",    "Unknown"),
            "server_country": server.get("country", ""),
            "latency_ms":     round(r.get("ping", 0), 1),
        }

    except ImportError:
        return {"error": "speedtest-cli not installed — run: pip install speedtest-cli"}
    except Exception as exc:
        return {"error": f"Speed test failed: {exc}"}


# ─── WiFi Signal ──────────────────────────────────────────────────────────────

def get_wifi_info() -> dict:
    """
    Read WiFi signal strength (RSSI), noise, SNR, channel from the OS.
    Supports macOS and Linux; Windows returns a graceful fallback.
    """
    system = platform.system()

    if system == "Darwin":
        # system_profiler is the supported API (airport is deprecated on macOS 14+)
        try:
            proc = subprocess.run(
                ["system_profiler", "SPAirPortDataType"],
                capture_output=True, text=True, timeout=10,
            )
            out = proc.stdout

            # Isolate the "Current Network Information:" block
            block_match = re.search(
                r"Current Network Information:\s*\n(.*?)(?:\n\s*\n|\Z)",
                out, re.DOTALL,
            )
            block = block_match.group(1) if block_match else ""

            # SSID is the first indented label followed by ":"
            ssid_m   = re.search(r"^\s{12}(.+):$",                 block, re.MULTILINE)
            sig_m    = re.search(r"Signal / Noise:\s*(-\d+)\s*dBm\s*/\s*(-\d+)\s*dBm", block)
            chan_m   = re.search(r"Channel:\s*([\w]+)",             block)
            rate_m   = re.search(r"Transmit Rate:\s*(\d+)",         block)

            if not ssid_m:
                return {"error": "WiFi not connected or no current network found"}

            rssi_val  = int(sig_m.group(1)) if sig_m else None
            noise_val = int(sig_m.group(2)) if sig_m else None
            snr       = (rssi_val - noise_val) if (rssi_val is not None and noise_val is not None) else None

            return {
                "ssid":           ssid_m.group(1).strip(),
                "rssi_dbm":       rssi_val,
                "noise_dbm":      noise_val,
                "snr_db":         snr,
                "channel":        chan_m.group(1)        if chan_m  else "Unknown",
                "tx_rate_mbps":   int(rate_m.group(1))  if rate_m  else None,
                "signal_quality": _rssi_quality(rssi_val),
            }

        except FileNotFoundError:
            return {"error": "system_profiler not found — WiFi info unavailable"}
        except Exception as exc:
            return {"error": f"Could not read WiFi info: {exc}"}

    elif system == "Linux":
        try:
            proc = subprocess.run(
                ["iwconfig"], capture_output=True, text=True, timeout=5
            )
            out = proc.stdout
            ssid   = re.search(r'ESSID:"([^"]+)"',          out)
            signal = re.search(r"Signal level=(-\d+)\s*dBm", out)
            rssi_val = int(signal.group(1)) if signal else None
            return {
                "ssid":          ssid.group(1) if ssid else "Unknown",
                "rssi_dbm":      rssi_val,
                "signal_quality": _rssi_quality(rssi_val),
            }
        except Exception as exc:
            return {"error": f"Could not read WiFi info: {exc}"}

    return {"error": f"WiFi info not supported on {system}"}


def _rssi_quality(rssi: Optional[int]) -> str:
    if rssi is None:
        return "Unknown"
    if rssi >= -50: return "Excellent"
    if rssi >= -60: return "Good"
    if rssi >= -70: return "Fair"
    if rssi >= -80: return "Poor"
    return "Very Poor"


# ─── Scoring ──────────────────────────────────────────────────────────────────

def calculate_score(result: dict) -> dict:
    """
    Compute a 0–100 video-call readiness score from test results.

    Weights:
        Ping         25 %
        Jitter       20 %
        Packet Loss  20 %
        Download     20 %
        Upload       10 %
        WiFi Signal   5 %
    """
    ping  = result.get("ping",  {}) or {}
    speed = result.get("speed", {}) or {}
    wifi  = result.get("wifi",  {}) or {}

    def _s(val, neutral=50.0) -> float:
        return val if isinstance(val, (int, float)) else neutral

    # Ping: 20 ms → 100, 150 ms → 0 (linear)
    ping_score = max(0.0, min(100.0, 100 - (_s(ping.get("avg_ms")) - 20) * (100 / 130)))

    # Jitter: 0 ms → 100, 50 ms → 0
    jitter_score = max(0.0, min(100.0, 100 - (_s(ping.get("jitter_ms")) / 50) * 100))

    # Packet loss: 0 % → 100, 5 % → 0
    loss_score = max(0.0, min(100.0, 100 - (_s(ping.get("packet_loss_pct")) / 5) * 100))

    # Download: 0 → 0, 25 Mbps → 100
    dl = _s(speed.get("download_mbps")) if "error" not in speed else 50.0
    dl_score = max(0.0, min(100.0, (dl / 25) * 100))

    # Upload: 0 → 0, 10 Mbps → 100
    ul = _s(speed.get("upload_mbps")) if "error" not in speed else 50.0
    ul_score = max(0.0, min(100.0, (ul / 10) * 100))

    # Signal: -90 dBm → 0, -50 dBm → 100
    rssi = wifi.get("rssi_dbm")
    sig_score = max(0.0, min(100.0, ((rssi + 90) / 40) * 100)) if isinstance(rssi, int) else 50.0

    breakdown = {
        "ping":         round(ping_score,   1),
        "jitter":       round(jitter_score, 1),
        "packet_loss":  round(loss_score,   1),
        "download":     round(dl_score,     1),
        "upload":       round(ul_score,     1),
        "signal":       round(sig_score,    1),
    }

    weights = {
        "ping": 0.25, "jitter": 0.20, "packet_loss": 0.20,
        "download": 0.20, "upload": 0.10, "signal": 0.05,
    }
    overall = sum(breakdown[k] * weights[k] for k in weights)

    if   overall >= 85: grade, verdict = "A", "Excellent — perfect for HD video calls"
    elif overall >= 70: grade, verdict = "B", "Good — suitable for most video calls"
    elif overall >= 55: grade, verdict = "C", "Acceptable — occasional quality drops possible"
    elif overall >= 40: grade, verdict = "D", "Poor — expect degraded video / audio"
    else:               grade, verdict = "F", "Unsuitable for video calls"

    return {
        "overall":   round(overall, 1),
        "grade":     grade,
        "verdict":   verdict,
        "breakdown": breakdown,
    }
