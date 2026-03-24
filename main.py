"""
main.py — WiFi Meet Tester
Interactive CLI to test & compare WiFi spots for video conference calls.

Usage:
    python main.py
"""

import json
import statistics
import time
from datetime import datetime
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from tester import (
    VIDEO_CALL_REQS,
    calculate_score,
    get_wifi_info,
    run_ping_test,
    run_speed_test,
)

console = Console()
RESULTS_FILE = Path(__file__).parent / "results.json"

GRADE_COLOR = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}


# ─── Persistence ──────────────────────────────────────────────────────────────

def load_results() -> list:
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_result(result: dict):
    results = load_results()
    results.append(result)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"[dim]  Saved → {RESULTS_FILE}[/dim]")


# ─── Display helpers ──────────────────────────────────────────────────────────

def _status(value, threshold, lower_is_better: bool = True):
    """Return (icon, color) for pass/fail against threshold."""
    if not isinstance(value, (int, float)):
        return "?", "dim"
    ok = (value <= threshold) if lower_is_better else (value >= threshold)
    return ("✓", "green") if ok else ("✗", "red")


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def display_result(result: dict, score: dict):
    ping  = result.get("ping",  {}) or {}
    speed = result.get("speed", {}) or {}
    wifi  = result.get("wifi",  {}) or {}

    console.print()
    console.print(Panel(
        f"[bold cyan]📍 Location:[/bold cyan] [yellow]{result['location']}[/yellow]\n"
        f"[dim]{result['timestamp']}[/dim]",
        expand=False,
    ))

    # ── WiFi Signal ──
    if "error" not in wifi:
        wt = Table(title="📶 WiFi Signal", box=box.ROUNDED, show_header=False, expand=False)
        wt.add_column("Metric", style="bold", min_width=14)
        wt.add_column("Value")

        wt.add_row("Network (SSID)", wifi.get("ssid", "?"))

        rssi = wifi.get("rssi_dbm")
        quality = wifi.get("signal_quality", "?")
        qc = {"Excellent": "green", "Good": "green", "Fair": "yellow",
              "Poor": "red", "Very Poor": "red"}.get(quality, "white")
        icon, _ = _status(rssi, VIDEO_CALL_REQS["rssi_dbm"], lower_is_better=False)
        wt.add_row(
            "Signal (RSSI)",
            f"[{qc}]{rssi} dBm  ·  {quality}  {icon}[/{qc}]",
        )
        if wifi.get("snr_db") is not None:
            wt.add_row("SNR", f"{wifi['snr_db']} dB")
        if wifi.get("channel"):
            wt.add_row("Channel", str(wifi["channel"]))
        if wifi.get("tx_rate_mbps"):
            wt.add_row("Link Speed", f"{wifi['tx_rate_mbps']} Mbps")
        console.print(wt)
    else:
        console.print(f"[yellow]WiFi info unavailable: {wifi.get('error')}[/yellow]")

    # ── Latency & Stability ──
    if "error" not in ping and ping:
        lt = Table(
            title="🏓 Latency & Stability",
            box=box.ROUNDED, show_header=True, expand=False,
        )
        lt.add_column("Metric",    style="bold",  min_width=14)
        lt.add_column("Value",     justify="right")
        lt.add_column("Target",    justify="right", style="dim")
        lt.add_column("Status",    justify="center")

        avg = ping.get("avg_ms")
        icon, color = _status(avg, VIDEO_CALL_REQS["ping_ms"])
        lt.add_row("Avg Ping",    f"[{color}]{avg} ms[/{color}]",    "≤ 150 ms", f"[{color}]{icon}[/{color}]")
        lt.add_row("Best Ping",   f"{ping.get('min_ms')} ms",          "",         "")
        lt.add_row("Worst Ping",  f"{ping.get('max_ms')} ms",          "",         "")

        jitter = ping.get("jitter_ms")
        icon, color = _status(jitter, VIDEO_CALL_REQS["jitter_ms"])
        lt.add_row("Jitter",      f"[{color}]{jitter} ms[/{color}]",  "≤ 30 ms",  f"[{color}]{icon}[/{color}]")

        loss = ping.get("packet_loss_pct")
        icon, color = _status(loss, VIDEO_CALL_REQS["packet_loss_pct"])
        lt.add_row("Packet Loss", f"[{color}]{loss}%[/{color}]",      "≤ 1%",     f"[{color}]{icon}[/{color}]")
        console.print(lt)
    elif "error" in ping:
        console.print(f"[red]Ping failed: {ping['error']}[/red]")

    # ── Speed ──
    if speed and "error" not in speed:
        st = Table(
            title="⚡ Speed",
            box=box.ROUNDED, show_header=True, expand=False,
        )
        st.add_column("Metric",       style="bold",  min_width=14)
        st.add_column("Value",        justify="right")
        st.add_column("Min Required", justify="right", style="dim")
        st.add_column("Status",       justify="center")

        dl = speed.get("download_mbps")
        icon, color = _status(dl, VIDEO_CALL_REQS["download_mbps"], lower_is_better=False)
        st.add_row("Download", f"[{color}]{dl} Mbps[/{color}]", "≥ 3 Mbps",  f"[{color}]{icon}[/{color}]")

        ul = speed.get("upload_mbps")
        icon, color = _status(ul, VIDEO_CALL_REQS["upload_mbps"], lower_is_better=False)
        st.add_row("Upload",   f"[{color}]{ul} Mbps[/{color}]", "≥ 3 Mbps",  f"[{color}]{icon}[/{color}]")

        srv = speed.get("server_name", "?")
        cty = speed.get("server_country", "")
        st.add_row("Test Server", f"{srv}, {cty}", "", "")
        console.print(st)
    elif speed and "error" in speed:
        console.print(f"[red]Speed test failed: {speed['error']}[/red]")
    elif not speed:
        console.print("[dim]Speed test was skipped.[/dim]")

    # ── Score Panel ──
    overall = score["overall"]
    grade   = score["grade"]
    verdict = score["verdict"]
    gcolor  = GRADE_COLOR.get(grade, "white")

    bd = score["breakdown"]
    breakdown_lines = (
        f"  Ping {bd['ping']:>5.0f}/100  │  "
        f"Jitter {bd['jitter']:>5.0f}/100  │  "
        f"Packet Loss {bd['packet_loss']:>5.0f}/100\n"
        f"  Download {bd['download']:>5.0f}/100  │  "
        f"Upload {bd['upload']:>5.0f}/100  │  "
        f"Signal {bd['signal']:>5.0f}/100"
    )

    console.print(Panel(
        f"[bold][{gcolor}]{overall}/100  (Grade {grade})[/{gcolor}][/bold]\n"
        f"[{gcolor}]{_score_bar(overall)}[/{gcolor}]\n"
        f"[italic]{verdict}[/italic]\n\n"
        f"[dim]{breakdown_lines}[/dim]",
        title="🎯 Video-Call Readiness Score",
        border_style=gcolor,
        expand=False,
    ))


# ─── Quick Test ───────────────────────────────────────────────────────────────

def run_quick_test(location: str, skip_speed: bool = False) -> dict:
    console.print(
        f"\n[bold cyan]Starting test for:[/bold cyan] [yellow]{location}[/yellow]"
    )

    result = {
        "location":  location,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wifi":      {},
        "ping":      {},
        "speed":     None,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as prog:

        t = prog.add_task("Getting WiFi signal info…", total=None)
        result["wifi"] = get_wifi_info()
        prog.remove_task(t)

        t = prog.add_task("Running ping test (10 packets to 8.8.8.8)…", total=None)
        result["ping"] = run_ping_test(count=10)
        prog.remove_task(t)

        if not skip_speed:
            t = prog.add_task("Preparing speed test…", total=None)

            def on_progress(msg: str):
                prog.update(t, description=msg)

            result["speed"] = run_speed_test(progress_callback=on_progress)
            prog.remove_task(t)

    score = calculate_score(result)
    result["score"] = score
    display_result(result, score)
    return result


# ─── Continuous Monitor ───────────────────────────────────────────────────────

def monitor_mode(location: str, rounds: int = 5, interval: int = 30):
    console.print(
        f"\n[bold]📡 Continuous Monitor[/bold] — "
        f"[yellow]{location}[/yellow]  "
        f"[dim]{rounds} rounds · {interval}s interval[/dim]\n"
    )

    pings, jitters, losses = [], [], []

    for i in range(1, rounds + 1):
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(f"[cyan]Round {i}/{rounds}[/cyan]  [dim]{ts}[/dim]", end="  ")

        r = run_ping_test(count=5)

        if "error" in r:
            console.print(f"[red]{r['error']}[/red]")
        else:
            avg  = r["avg_ms"]
            jit  = r["jitter_ms"]
            loss = r["packet_loss_pct"]

            pings.append(avg)
            jitters.append(jit)
            losses.append(loss)

            pc = "green" if avg  <= 50  else ("yellow" if avg  <= 100 else "red")
            jc = "green" if jit  <= 15  else ("yellow" if jit  <= 30  else "red")
            lc = "green" if loss == 0   else ("yellow" if loss <= 1   else "red")

            console.print(
                f"Ping [{pc}]{avg:>6.1f} ms[/{pc}]  "
                f"Jitter [{jc}]{jit:>5.1f} ms[/{jc}]  "
                f"Loss [{lc}]{loss:>4.1f}%[/{lc}]"
            )

        if i < rounds:
            console.print(f"[dim]  ↳ next in {interval}s…[/dim]")
            time.sleep(interval)

    if pings:
        avg_ping   = round(statistics.mean(pings),   1)
        stdev_ping = round(statistics.stdev(pings),  1) if len(pings) > 1 else 0.0
        avg_jitter = round(statistics.mean(jitters), 1)
        avg_loss   = round(statistics.mean(losses),  1)

        # Stability rating
        if stdev_ping <= 5 and avg_loss == 0:
            stability, sc = "Very Stable ✓", "green"
        elif stdev_ping <= 15 and avg_loss <= 1:
            stability, sc = "Mostly Stable", "yellow"
        else:
            stability, sc = "Unstable — likely to drop calls", "red"

        console.print(Panel(
            f"[bold]Rounds:[/bold]        {len(pings)}/{rounds}\n"
            f"[bold]Avg Ping:[/bold]      {avg_ping} ms\n"
            f"[bold]Ping Variance:[/bold] {stdev_ping} ms  [dim](lower = more stable)[/dim]\n"
            f"[bold]Avg Jitter:[/bold]    {avg_jitter} ms\n"
            f"[bold]Avg Packet Loss:[/bold] {avg_loss}%\n"
            f"[bold]Best Ping:[/bold]     {min(pings)} ms   "
            f"[bold]Worst:[/bold] {max(pings)} ms\n\n"
            f"[{sc}]Stability: {stability}[/{sc}]",
            title="📈 Stability Report",
            border_style=sc,
            expand=False,
        ))


# ─── Comparison Table ─────────────────────────────────────────────────────────

def show_comparison(results: list):
    if len(results) < 2:
        console.print("[yellow]Need at least 2 saved locations to compare.[/yellow]")
        return

    console.print()
    table = Table(
        title="📊 Location Comparison — Video Call Readiness",
        box=box.DOUBLE_EDGE, show_header=True,
        header_style="bold cyan", expand=False,
    )

    table.add_column("Metric",    style="bold", min_width=16)
    table.add_column("Needed",    style="dim",  justify="center")
    for r in results:
        table.add_column(r["location"], justify="center", min_width=18)

    def _nested_get(d: dict, dotpath: str):
        for key in dotpath.split("."):
            if not isinstance(d, dict):
                return None
            d = d.get(key)
        return d

    def add_row(label, path, req, fmt_fn, lower_better=True):
        vals = [_nested_get(r, path) for r in results]
        # ── find best valid value ──
        valid = [(i, v) for i, v in enumerate(vals) if isinstance(v, (int, float))]
        if valid:
            best_idx = (
                min(valid, key=lambda x: x[1])[0]
                if lower_better
                else max(valid, key=lambda x: x[1])[0]
            )
        else:
            best_idx = -1

        cells = []
        for i, v in enumerate(vals):
            if not isinstance(v, (int, float)):
                cells.append("[dim]N/A[/dim]")
                continue
            ok = (v <= req) if lower_better else (v >= req)
            color = "green" if ok else "red"
            star  = " ⭐" if i == best_idx else ""
            cells.append(f"[{color}]{fmt_fn(v)}{star}[/{color}]")

        table.add_row(label, fmt_fn(req), *cells)

    add_row("Download",    "speed.download_mbps",  3,    lambda v: f"{v:.1f} Mbps", lower_better=False)
    add_row("Upload",      "speed.upload_mbps",    3,    lambda v: f"{v:.1f} Mbps", lower_better=False)
    add_row("Avg Ping",    "ping.avg_ms",           150,  lambda v: f"{v:.0f} ms")
    add_row("Jitter",      "ping.jitter_ms",        30,   lambda v: f"{v:.1f} ms")
    add_row("Packet Loss", "ping.packet_loss_pct",  1,    lambda v: f"{v:.1f}%")
    add_row("WiFi Signal", "wifi.rssi_dbm",         -70,  lambda v: f"{v} dBm", lower_better=False)

    # ── overall score row ──
    table.add_section()
    scores = [r.get("score", {}).get("overall", 0) for r in results]
    best_score_idx = scores.index(max(scores)) if scores else -1

    score_cells = []
    for i, r in enumerate(results):
        s = r.get("score", {})
        overall = s.get("overall", "?")
        grade   = s.get("grade",   "?")
        gc      = GRADE_COLOR.get(grade, "white")
        star    = " ⭐" if i == best_score_idx else ""
        score_cells.append(f"[{gc}]{overall}/100  ({grade}){star}[/{gc}]")

    table.add_row("[bold]Overall Score[/bold]", "—", *score_cells)
    console.print(table)

    best = results[best_score_idx]
    console.print(Panel(
        f"[bold green]🏆 Best location for video calls:[/bold green]  "
        f"[yellow]{best['location']}[/yellow]\n"
        f"Score: {best['score']['overall']}/100 — {best['score']['verdict']}",
        border_style="green",
        expand=False,
    ))


# ─── Saved results list ───────────────────────────────────────────────────────

def list_saved_results(results: list):
    if not results:
        console.print("[yellow]No saved results yet. Run a test first![/yellow]")
        return

    t = Table(title="Saved Results", box=box.ROUNDED, expand=False)
    t.add_column("#",          justify="right", style="dim")
    t.add_column("Location",   style="bold")
    t.add_column("Timestamp",  style="dim")
    t.add_column("Ping",       justify="right")
    t.add_column("Download",   justify="right")
    t.add_column("Upload",     justify="right")
    t.add_column("Score",      justify="center")

    for i, r in enumerate(results, 1):
        ping  = r.get("ping",  {}) or {}
        speed = r.get("speed", {}) or {}
        s     = r.get("score", {})
        grade = s.get("grade", "?")
        gc    = GRADE_COLOR.get(grade, "white")

        t.add_row(
            str(i),
            r.get("location", "?"),
            r.get("timestamp", "?"),
            f"{ping.get('avg_ms', 'N/A')} ms",
            f"{speed.get('download_mbps', 'N/A')} Mbps",
            f"{speed.get('upload_mbps',   'N/A')} Mbps",
            f"[{gc}]{s.get('overall', '?')}/100 ({grade})[/{gc}]",
        )

    console.print(t)


# ─── Main menu ────────────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold cyan]WiFi Quality Tester[/bold cyan]\n"
        "[dim]Measure & compare WiFi quality from any spot[/dim]\n\n"
        "[dim]Measures: ping · jitter · packet loss · download · upload · WiFi signal[/dim]",
        border_style="cyan",
        expand=False,
    ))

    while True:
        console.print("\n[bold]── Menu ────────────────────────────────[/bold]")
        console.print("  [cyan]1[/cyan]  Full test     [dim](ping + WiFi + speed ~60s)[/dim]")
        console.print("  [cyan]2[/cyan]  Quick test    [dim](ping + WiFi only, ~5s)[/dim]")
        console.print("  [cyan]3[/cyan]  Monitor mode  [dim](repeated pings — check stability)[/dim]")
        console.print("  [cyan]4[/cyan]  Compare saved locations")
        console.print("  [cyan]5[/cyan]  View saved results")
        console.print("  [cyan]6[/cyan]  Clear saved results")
        console.print("  [cyan]q[/cyan]  Quit")

        choice = Prompt.ask(
            "\nChoice",
            choices=["1", "2", "3", "4", "5", "6", "q"],
            default="1",
        )

        if choice == "q":
            console.print("[dim]Done. Good luck with your meeting![/dim]")
            break

        elif choice in ("1", "2"):
            location = Prompt.ask(
                "Name this location [dim](e.g. Living Room, Bedroom)[/dim]",
                default="My Location",
            )
            result = run_quick_test(location, skip_speed=(choice == "2"))
            if Confirm.ask("\nSave result for later comparison?", default=True):
                save_result(result)

        elif choice == "3":
            location = Prompt.ask("Location name", default="My Location")
            rounds   = int(Prompt.ask("Number of rounds", default="5"))
            interval = int(Prompt.ask("Seconds between rounds", default="30"))
            monitor_mode(location, rounds=rounds, interval=interval)

        elif choice == "4":
            results = load_results()
            if len(results) < 2:
                console.print(
                    "[yellow]Need at least 2 saved locations. "
                    "Run tests from different spots first![/yellow]"
                )
                continue

            console.print("\n[bold]Saved locations:[/bold]")
            for i, r in enumerate(results, 1):
                score = r.get("score", {}).get("overall", "?")
                console.print(
                    f"  [cyan]{i}[/cyan]. {r['location']}  "
                    f"[dim]{r['timestamp']}[/dim]  Score: {score}"
                )

            console.print("\n[dim]Enter 'all' or comma-separated numbers, e.g. 1,3[/dim]")
            sel = Prompt.ask("Select locations to compare", default="all")

            if sel.lower().strip() == "all":
                to_compare = results
            else:
                idxs = [
                    int(x.strip()) - 1
                    for x in sel.split(",")
                    if x.strip().isdigit()
                ]
                to_compare = [results[i] for i in idxs if 0 <= i < len(results)]

            if len(to_compare) >= 2:
                show_comparison(to_compare)
            else:
                console.print("[yellow]Select at least 2 locations.[/yellow]")

        elif choice == "5":
            list_saved_results(load_results())

        elif choice == "6":
            if Confirm.ask("[red]Delete all saved results?[/red]", default=False):
                RESULTS_FILE.unlink(missing_ok=True)
                console.print("[green]Cleared.[/green]")


if __name__ == "__main__":
    main()
