#!/usr/bin/env python3
from __future__ import annotations

import bisect
import datetime as dt
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

KBD_INJECTED_MASK = 0x10 | 0x02
MOUSE_INJECTED_MASK = 0x01 | 0x02

INJECTED_RATE_MEDIUM = 0.01
INJECTED_RATE_HIGH = 0.05

BURST_WINDOW_MS = 5000
BURST_CPS_MEDIUM = 8.0
BURST_CPS_HIGH = 13.0
BURST_MIN_CLICKS = 30

MINUTE_WINDOW_MS = 60_000
MINUTE_CPM_MEDIUM = 420
MINUTE_CPM_HIGH = 600
MINUTE_MIN_CLICKS = 50
MINUTE_MIN_DURATION_MS = 60_000

FAST_INTERVAL_MS = 20
FAST_RUN_MEDIUM = 3
FAST_RUN_HIGH = 5
FAST_MIN_CLICKS = 4

CLUSTER_WINDOW_MS = 5000
CLUSTER_TIGHT_GRID = 6
CLUSTER_TIGHT_THRESHOLD = 15
CLUSTER_WIDE_GRID = 20
CLUSTER_WIDE_THRESHOLD = 25
CLUSTER_CV_THRESHOLD = 0.03
CLUSTER_MAX_DISTINCT = 3
CLUSTER_PIXEL_MIN = 30


KBD_SHORT_MS = 15
KBD_SHORT_COUNT = 10

SAME_PIXEL_HIGH = 50
SAME_PIXEL_MEDIUM = 30


# Check 1b: window-input pairing. Each window click should have a matching
# low-level physical click within +/- this many ms. Unmatched window clicks
# are injected via PostMessage/SendMessage/ControlClick.
WINDOW_PAIR_WINDOW_MS = 200
WINDOW_INJECTED_MIN_CLICKS = 30
WINDOW_INJECTED_MEDIUM = 5
WINDOW_INJECTED_HIGH = 20

TOP_N = 5

VK_NAMES = {
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x10: "Shift",
    0x11: "Ctrl", 0x12: "Alt", 0x13: "Pause", 0x14: "CapsLock",
    0x1B: "Esc", 0x20: "Space", 0x21: "PgUp", 0x22: "PgDn",
    0x23: "End", 0x24: "Home",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x2C: "PrtSc", 0x2D: "Insert", 0x2E: "Delete",
    0xA0: "LShift", 0xA1: "RShift", 0xA2: "LCtrl", 0xA3: "RCtrl",
    0xA4: "LAlt", 0xA5: "RAlt",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}
for _i in range(10):
    VK_NAMES[0x30 + _i] = str(_i)
for _i in range(26):
    VK_NAMES[0x41 + _i] = chr(ord("A") + _i)
for _i in range(12):
    VK_NAMES[0x70 + _i] = f"F{_i + 1}"


def _vk_name(vk):
    if vk is None:
        return "?"
    return VK_NAMES.get(vk, f"vk={vk}")


def _fmt_time(unix_ms):
    return dt.datetime.fromtimestamp(unix_ms / 1000).strftime("%H:%M:%S")


def _fmt_datetime(unix_ms):
    return dt.datetime.fromtimestamp(unix_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def load_events(jsonl_path, match_id):
    events = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("matchId") == match_id:
                events.append(e)
    return events


def _has_window_layer(events):
    return any(e.get("source") == "ra1_window_mouse" for e in events)


def _effective_mouse_events(events):
    """Mouse events to feed into mouse-checks.

    If the window-hook layer captured events (source="ra1_window_mouse"),
    those represent everything the game actually received - including any
    injected PostMessage/ControlClick clicks. Each event is tagged with
    `_injected=True/False` based on pairing with the physical low-level
    mouse stream (the same pairing rule as check 9).

    If the window layer was inactive for this match, we fall back to the
    physical low-level mouse events as before; all tagged _injected=False
    by definition (we cannot see what bypassed the hook).
    """
    window_mouse = [e for e in events if e.get("source") == "ra1_window_mouse"]
    if not window_mouse:
        return [
            dict(e, _injected=False)
            for e in events
            if e.get("source") == "mouse"
        ]

    phys_by_button = defaultdict(list)
    for e in events:
        if (e.get("source") == "mouse"
                and e.get("eventType") == "down"
                and e.get("button") in ("left", "right", "middle", "x1", "x2")):
            phys_by_button[e["button"]].append(e["unixMs"])
    for k in phys_by_button:
        phys_by_button[k].sort()
    consumed = {b: [False] * len(phys_by_button[b]) for b in phys_by_button}

    tagged = []
    for w in sorted(window_mouse, key=lambda x: x["unixMs"]):
        injected = False
        button = w.get("button")
        if (w.get("eventType") == "down"
                and button in ("left", "right", "middle", "x1", "x2")):
            candidates = phys_by_button.get(button, [])
            cons = consumed.get(button, [])
            t = w["unixMs"]
            lo = bisect.bisect_left(candidates, t - WINDOW_PAIR_WINDOW_MS)
            hi = bisect.bisect_right(candidates, t + WINDOW_PAIR_WINDOW_MS)
            best = -1
            best_dt = WINDOW_PAIR_WINDOW_MS + 1
            for j in range(lo, hi):
                if cons[j]:
                    continue
                d = abs(candidates[j] - t)
                if d < best_dt:
                    best_dt = d
                    best = j
            if best >= 0:
                cons[best] = True
            else:
                injected = True
        tagged.append(dict(w, _injected=injected))
    return tagged


def _injected_suffix(items, events):
    """Return ' (N injected)' if the window layer is active, else ''."""
    if not _has_window_layer(events):
        return ""
    n = sum(1 for x in items if x.get("_injected"))
    return f" ({n} injected)"


def _mouse_downs(events):
    return sorted(
        (e for e in _effective_mouse_events(events)
         if e.get("eventType") == "down"),
        key=lambda x: x["unixMs"],
    )


def _find_meta(events, event_type):
    return next((e for e in events
                 if e.get("source") == "meta" and e.get("eventType") == event_type),
                None)


def _match_duration_ms(events):
    start = _find_meta(events, "match_start")
    end = _find_meta(events, "match_end")
    if start and end:
        return end["unixMs"] - start["unixMs"]
    ts = sorted(e["unixMs"] for e in events)
    return ts[-1] - ts[0] if len(ts) >= 2 else 0


def _cv(intervals):
    intervals = [iv for iv in intervals if iv >= 0]
    if len(intervals) < 2:
        return None
    mean = statistics.mean(intervals)
    if mean <= 0:
        return 0.0
    return statistics.pstdev(intervals) / mean


def _busiest_window(times, window_ms):
    """Return (max clicks in any window_ms span, start index)."""
    max_count = 0
    best_i = 0
    j = 0
    for i in range(len(times)):
        if j < i:
            j = i
        while j < len(times) and times[j] - times[i] <= window_ms:
            j += 1
        if j - i > max_count:
            max_count = j - i
            best_i = i
    return max_count, best_i


# --- Check 1a: injection flag (OS low-level layer) ---------------------------
def check_injection_flags(events):
    label = "1a - Injection flag"
    kbd = [e for e in events if e.get("source") == "kbd"]
    mouse = [e for e in events
             if e.get("source") == "mouse" and e.get("eventType") != "move"]
    total = len(kbd) + len(mouse)
    if total == 0:
        return ("skipped", label, "skipped - no input events.", [])

    kbd_flagged = [e for e in kbd if (e.get("flags", 0) & KBD_INJECTED_MASK)]
    mouse_flagged = [e for e in mouse if (e.get("flags", 0) & MOUSE_INJECTED_MASK)]
    flagged_count = len(kbd_flagged) + len(mouse_flagged)
    rate = flagged_count / total

    if flagged_count == 0:
        return ("clean", label,
                f"clean - 0 of {total} input events carried the injected flag.", [])

    details = []
    if kbd:
        details.append(f"Keyboard: {len(kbd_flagged)/len(kbd)*100:.1f}% flagged "
                        f"({len(kbd_flagged)}/{len(kbd)}).")
    if mouse:
        details.append(f"Mouse: {len(mouse_flagged)/len(mouse)*100:.1f}% flagged "
                        f"({len(mouse_flagged)}/{len(mouse)}).")
    if kbd_flagged:
        keys = [_vk_name(e.get("vkCode")) for e in kbd_flagged
                if e.get("eventType") in ("down", "sysdown")]
        if keys:
            top = Counter(keys).most_common(TOP_N)
            details.append("Most-flagged keys: "
                           + ", ".join(f"{k} (x{c})" for k, c in top) + ".")
    if rate >= INJECTED_RATE_HIGH:   # 5%
        details.append("Note: this rate is essentially impossible to produce "
                       "with legitimate input - almost certainly automated. "
                       "The rare innocent explanations (game-streaming, "
                       "remote-play, controller-to-keyboard mappers) do not "
                       "apply to a standard RA1 / CnCNet setup.")
    else:
        details.append("Note: at this low rate an innocent explanation is "
                       "possible (game-streaming / remote-play, controller-"
                       "mappers) - verify with the player before acting.")

    if rate >= INJECTED_RATE_HIGH:
        return ("high", label,
                f"{rate*100:.1f}% of input events ({flagged_count}/{total}) carried "
                f"the Windows injected flag - strong sign of software-generated input.",
                details)
    if rate >= INJECTED_RATE_MEDIUM:
        return ("medium", label,
                f"{rate*100:.2f}% of input events ({flagged_count}/{total}) carried "
                f"the injected flag - anomalous.",
                details)
    return ("low", label,
            f"{flagged_count} of {total} events carried the injected flag - "
            f"low, but not zero.",
            details)


# --- Check 2a: click burst rate (peak cps over a 5s window) -------------------
def check_click_burst_rate(events):
    label = "2a - Click speed (burst)"
    clicks = _mouse_downs(events)
    if len(clicks) < BURST_MIN_CLICKS:
        return ("skipped", label,
                f"skipped - only {len(clicks)} clicks (need {BURST_MIN_CLICKS}).", [])

    times = [c["unixMs"] for c in clicks]
    max_count, best_i = _busiest_window(times, BURST_WINDOW_MS)
    peak_cps = max_count / (BURST_WINDOW_MS / 1000)
    peak_clicks = clicks[best_i:best_i + max_count]
    has_win = _has_window_layer(events)
    inj_n = sum(1 for c in peak_clicks if c.get("_injected"))
    inj_note = (f" ({inj_n} of those {max_count} clicks were injected)"
                if has_win else "")
    details = [
        "Reference: Guinness record for clicks in a minute is ~760 (~12.7/sec).",
    ]
    if peak_cps >= BURST_CPS_HIGH:
        return ("high", label,
                f"Peak click rate {peak_cps:.1f} clicks/sec over 5s{inj_note} - "
                f"above the human world record (~12.7/sec).",
                details)
    if peak_cps >= BURST_CPS_MEDIUM:
        return ("medium", label,
                f"Peak click rate {peak_cps:.1f} clicks/sec over 5s{inj_note} "
                f"- very fast.",
                details)
    return ("clean", label,
            f"clean - peak click rate {peak_cps:.1f} clicks/sec over 5s"
            f"{inj_note}.", [])


# --- Check 2b: click rate over the busiest 60s window -------------------------
def check_click_rate_minute(events):
    label = "2b - Click rate (busiest minute)"
    clicks = _mouse_downs(events)
    duration_ms = _match_duration_ms(events)
    if len(clicks) < MINUTE_MIN_CLICKS or duration_ms < MINUTE_MIN_DURATION_MS:
        return ("skipped", label,
                f"skipped - needs {MINUTE_MIN_CLICKS}+ clicks and a 60s+ match "
                f"(had {len(clicks)} clicks, {duration_ms/1000:.0f}s).", [])

    times = [c["unixMs"] for c in clicks]
    max_count, best_i = _busiest_window(times, MINUTE_WINDOW_MS)
    cpm = max_count
    minute_clicks = clicks[best_i:best_i + max_count]
    has_win = _has_window_layer(events)
    inj_n = sum(1 for c in minute_clicks if c.get("_injected"))
    inj_note = f" ({inj_n} injected)" if has_win else ""

    if cpm > MINUTE_CPM_HIGH:
        return ("high", label,
                f"Busiest minute held {cpm} clicks/min{inj_note} - a "
                f"superhuman sustained rate.",
                ["No human sustains this click rate for a full minute "
                 "while also playing."])
    if cpm >= MINUTE_CPM_MEDIUM:
        return ("medium", label,
                f"Busiest minute held {cpm} clicks/min{inj_note} - faster "
                f"than a human normally sustains.",
                ["This is the match's single busiest minute; a player at "
                 "peak intensity can approach this rate, so it counts as "
                 "suspicious rather than proof."])
    return ("clean", label,
            f"clean - busiest minute held {cpm} clicks/min{inj_note}.", [])


# --- Check 3: fast-click runs (consecutive sub-20ms gaps) ---------------------
def check_fast_click_runs(events):
    label = "3 - Fast clicks (run)"
    clicks = _mouse_downs(events)
    if len(clicks) < FAST_MIN_CLICKS:
        return ("skipped", label, f"skipped - only {len(clicks)} clicks.", [])

    intervals = [clicks[i + 1]["unixMs"] - clicks[i]["unixMs"]
                 for i in range(len(clicks) - 1)]
    longest = 0
    current = 0
    best_end = 0
    for idx, iv in enumerate(intervals):
        if 0 <= iv < FAST_INTERVAL_MS:
            current += 1
            if current > longest:
                longest = current
                best_end = idx
        else:
            current = 0

    if longest < FAST_RUN_MEDIUM:
        return ("clean", label,
                f"clean - longest run of sub-{FAST_INTERVAL_MS}ms gaps is {longest}.",
                [])

    start_click = best_end - longest + 1
    end_click = best_end + 1
    span = clicks[end_click]["unixMs"] - clicks[start_click]["unixMs"]
    run_clicks = clicks[start_click:end_click + 1]
    has_win = _has_window_layer(events)
    inj_n = sum(1 for c in run_clicks if c.get("_injected"))
    inj_note = (f" ({inj_n} of {longest + 1} were injected)"
                if has_win else "")
    details = [
        f"Longest run: {longest + 1} clicks each under {FAST_INTERVAL_MS}ms apart, "
        f"between {_fmt_time(clicks[start_click]['unixMs'])}-"
        f"{_fmt_time(clicks[end_click]['unixMs'])} ({span}ms total).",
        "A double-click or mouse bounce produces isolated short gaps, never a "
        "sustained run - this points to automation.",
    ]
    if longest >= FAST_RUN_HIGH:
        return ("high", label,
                f"Run of {longest} consecutive sub-{FAST_INTERVAL_MS}ms click "
                f"gaps{inj_note} - impossible for a human hand.",
                details)
    return ("medium", label,
            f"Run of {longest} consecutive sub-{FAST_INTERVAL_MS}ms click "
            f"gaps{inj_note} - faster than human.",
            details)


# --- Check 4a/4b: click clustering (busiest 5s window in one grid cell) -------
def _max_clicks_in_cell(clicks, grid, window_ms):
    cells = defaultdict(list)
    for x, y, t, _inj in clicks:
        cells[(x // grid, y // grid)].append(t)
    best = 0
    best_cell = (0, 0)
    best_win = (0, 0)
    for cell, times in cells.items():
        times.sort()
        left = 0
        for right in range(len(times)):
            while times[right] - times[left] > window_ms:
                left += 1
            if right - left + 1 > best:
                best = right - left + 1
                best_cell = cell
                best_win = (times[left], times[right])
    return best, best_cell, best_win


def _cluster_finding(clicks, cell, win, n, grid, box_label, has_window_layer):
    members = [(x, y, t, inj) for x, y, t, inj in clicks
               if (x // grid, y // grid) == cell and win[0] <= t <= win[1]]

    xs = [m[0] for m in members]
    ys = [m[1] for m in members]
    w = max(xs) - min(xs) + 1
    h = max(ys) - min(ys) + 1
    pix_counts = Counter((m[0], m[1]) for m in members)
    distinct = len(pix_counts)
    top_pixel, top_hits = pix_counts.most_common(1)[0]
    inj_in_cluster = sum(1 for m in members if m[3])
    inj_note = (f" ({inj_in_cluster} of those {n} were injected)"
                if has_window_layer else "")

    ts = sorted(m[2] for m in members)
    cv = _cv([ts[i + 1] - ts[i] for i in range(len(ts) - 1)])

    spread_lines = []
    if distinct == 1:
        spread_lines.append(
            f"Actual spread: 1x1 px - all {n} clicks on the exact same "
            f"pixel ({top_pixel[0]},{top_pixel[1]}).")
    else:
        spread_lines.append(
            f"Actual spread: {w}x{h} px across {distinct} distinct pixels.")
        spread_lines.append(
            f"Most-clicked exact pixel: ({top_pixel[0]},{top_pixel[1]}) "
            f"- {top_hits} of {n} cluster clicks.")

    mechanical = cv is not None and cv < CLUSTER_CV_THRESHOLD
    pixel_perfect = distinct <= CLUSTER_MAX_DISTINCT
    cv_txt = f"{cv:.3f}" if cv is not None else "n/a"

    if mechanical:
        sev = "high"
        timing_line = (f"Timing within the cluster: mechanically uniform "
                       f"(CV {cv:.3f}) - automated.")
        reason = (f"{n} clicks packed into one {box_label} spot within "
                  f"{CLUSTER_WINDOW_MS//1000}s{inj_note}, clicked with "
                  f"mechanical timing - autoclicker pattern.")
    elif pixel_perfect and n >= CLUSTER_PIXEL_MIN:
        sev = "medium"
        timing_line = (f"Timing within the cluster: CV {cv_txt} - not "
                       f"conclusive on its own.")
        reason = (f"{n} clicks crammed into a {box_label} spot within "
                  f"{CLUSTER_WINDOW_MS//1000}s{inj_note}, almost all on the "
                  f"exact same pixel - a person spreads their clicks across "
                  f"a button, an autoclicker keeps hitting the same spot.")
    else:
        sev = "clean"
        timing_line = (f"Timing within the cluster: human wobble "
                       f"(CV {cv_txt}) - consistent with a player spamming a button.")
        reason = (f"clean - densest spot was {n} clicks in one {box_label} box "
                  f"within {CLUSTER_WINDOW_MS//1000}s{inj_note}, but the "
                  f"timing wobbles (CV {cv_txt}) like human spam-clicking.")

    details = list(spread_lines)
    details.append(timing_line)
    return (sev, reason, details)


def check_click_clusters(events):
    label = "4a/4b - Click clustering"
    clicks = [(e["x"], e["y"], e["unixMs"], e.get("_injected", False))
              for e in _effective_mouse_events(events)
              if e.get("eventType") == "down"
              and e.get("x") is not None and e.get("y") is not None]
    if not clicks:
        return ("skipped", label, "skipped - no positioned clicks.", [])

    has_win = _has_window_layer(events)

    tight_n, tcell, twin = _max_clicks_in_cell(
        clicks, CLUSTER_TIGHT_GRID, CLUSTER_WINDOW_MS)
    tight = None
    if tight_n >= CLUSTER_TIGHT_THRESHOLD:
        tight = _cluster_finding(clicks, tcell, twin, tight_n,
                                 CLUSTER_TIGHT_GRID, "~6px", has_win)
        if tight[0] == "high":
            return (tight[0], label, tight[1], tight[2])

    wide_n, wcell, wwin = _max_clicks_in_cell(
        clicks, CLUSTER_WIDE_GRID, CLUSTER_WINDOW_MS)
    wide = None
    if wide_n >= CLUSTER_WIDE_THRESHOLD:
        wide = _cluster_finding(clicks, wcell, wwin, wide_n,
                                CLUSTER_WIDE_GRID, "20px", has_win)
        if wide[0] == "high":
            return (wide[0], label, wide[1], wide[2])

    if tight is not None and tight[0] == "medium":
        return (tight[0], label, tight[1], tight[2])
    if wide is not None and wide[0] == "medium":
        return (wide[0], label, wide[1], wide[2])

    if tight is not None:
        return ("clean", label, tight[1], tight[2])
    if wide is not None:
        return ("clean", label, wide[1], wide[2])
    return ("clean", label,
            f"clean - densest spot held {tight_n} clicks in a ~6px box within 5s.",
            [])


# --- Check 5b: keyboard key hold - impossibly short (auto-repeat collapsed) ----
def check_key_hold_short(events):
    label = "5b - Key hold (too short)"
    seq = sorted(
        (e for e in events
         if e.get("source") == "kbd"
         and e.get("eventType") in ("down", "sysdown", "up", "sysup")),
        key=lambda x: x["unixMs"],
    )
    held = {}
    durations = []
    for e in seq:
        vk = e.get("vkCode")
        if e.get("eventType") in ("down", "sysdown"):
            if vk not in held:          # first press; auto-repeat downs ignored
                held[vk] = e["unixMs"]
        else:                            # up / sysup
            down = held.pop(vk, None)
            if down is not None:
                dur = e["unixMs"] - down
                if dur >= 0:
                    durations.append((dur, vk))

    if not durations:
        return ("skipped", label, "skipped - no completed keystrokes.", [])

    total = len(durations)
    short_per_key = Counter(vk for d, vk in durations if d < KBD_SHORT_MS)
    short = sorted(d for d, vk in durations if d < KBD_SHORT_MS)
    # A key only counts as a "short-hold key" if it has many short presses.
    # This filters out single hotkey-trigger taps (X, 5, etc.) from the
    # flagged keys list - those have 1-2 short presses, not dozens like a
    # macro spamming asd.
    min_short_per_key = max(3, int(0.10 * len(short)))
    short_keys = {vk for vk, c in short_per_key.items()
                  if c >= min_short_per_key}

    if len(short) >= KBD_SHORT_COUNT and len(short_keys) >= 2:
        keynames = ", ".join(_vk_name(vk) for vk in sorted(short_keys))
        details = [
            "A human keystroke lasts ~80-150ms while a macro presses and "
            "releases near-instantly; auto-repeat is collapsed, so each key "
            "counts once from its first press to its release.",
        ]
        return ("high", label,
                f"{len(short)} of {total} keystrokes held under "
                f"{KBD_SHORT_MS}ms (range {short[0]}-{short[-1]}ms), spread "
                f"across {len(short_keys)} keys ({keynames}) - physically "
                f"impossible for a finger and a clear keyboard-macro signature.",
                details)

    if len(short) >= KBD_SHORT_COUNT:
        kn = _vk_name(next(iter(short_keys)))
        return ("clean", label,
                f"clean - {len(short)} keystrokes held under {KBD_SHORT_MS}ms "
                f"but all on one key ({kn}) - consistent with a key-remap "
                f"artefact, not a macro.",
                [])

    if short:
        return ("clean", label,
                f"clean - {total} keystrokes; {len(short)} held under "
                f"{KBD_SHORT_MS}ms (under the flag threshold of {KBD_SHORT_COUNT}).",
                [])
    return ("clean", label,
            f"clean - {total} keystrokes, none held under {KBD_SHORT_MS}ms.", [])


# --- Whole-match stat: most-clicked pixel (logged, not scored) ----------------
def most_clicked_pixel(events):
    items = [(e["x"], e["y"], e.get("_injected", False))
             for e in _effective_mouse_events(events)
             if e.get("eventType") == "down"
             and e.get("x") is not None and e.get("y") is not None]
    if not items:
        return None
    coords = [(x, y) for x, y, _ in items]
    (x, y), n = Counter(coords).most_common(1)[0]
    inj_on_top = sum(1 for px, py, inj in items
                     if px == x and py == y and inj)
    return (x, y, n, len(coords), inj_on_top)


# --- Check 6: same-pixel clicks (autoclicker parked on one spot) --------------
def check_same_pixel(events):
    label = "6 - Most-clicked pixel"
    pixel = most_clicked_pixel(events)
    if pixel is None:
        return ("skipped", label, "skipped - no positioned clicks.", [])

    x, y, n, total, inj = pixel
    has_win = _has_window_layer(events)
    inj_note = f" ({inj} of those {n} were injected)" if has_win else ""
    detail = ("In normal play the mouse constantly moves between the build "
              "buttons and the map, so repeat clicks never land on the exact "
              "same pixel.")
    if n >= SAME_PIXEL_HIGH:
        return ("high", label,
                f"{n} of {total} clicks landed on the exact same pixel "
                f"({x},{y}){inj_note} - that points to an autoclicker, "
                f"not a hand.",
                [detail])
    if n >= SAME_PIXEL_MEDIUM:
        return ("medium", label,
                f"{n} of {total} clicks landed on the exact same pixel "
                f"({x},{y}){inj_note} - more repeats on one spot than normal "
                f"play produces.",
                [detail])
    return ("clean", label,
            f"clean - busiest pixel ({x},{y}) took {n} of {total} clicks"
            f"{inj_note}.", [])


# --- Check 1b: injected window input (PostMessage / ControlClick) ------------
def check_window_injection(events):
    label = "1b - Injected window input"

    has_window_layer = any(e.get("source") == "ra1_window_mouse" for e in events)
    if not has_window_layer:
        return ("skipped", label,
                "skipped - window-hook layer not active for this match "
                "(fairplay_hook.dll missing, x86 build issue, or hook "
                "failed to attach).", [])

    win_clicks = sorted(
        (e for e in events
         if e.get("source") == "ra1_window_mouse"
         and e.get("eventType") == "down"
         and e.get("button") in ("left", "right", "middle")),
        key=lambda x: x["unixMs"],
    )
    if len(win_clicks) < WINDOW_INJECTED_MIN_CLICKS:
        return ("skipped", label,
                f"skipped - only {len(win_clicks)} window-clicks "
                f"(need {WINDOW_INJECTED_MIN_CLICKS}).", [])

    phys_by_button = defaultdict(list)
    for e in events:
        if (e.get("source") == "mouse"
                and e.get("eventType") == "down"
                and e.get("button") in ("left", "right", "middle")):
            phys_by_button[e["button"]].append(e["unixMs"])
    for k in phys_by_button:
        phys_by_button[k].sort()
    consumed = {b: [False] * len(phys_by_button[b]) for b in phys_by_button}

    unmatched = 0
    for w in win_clicks:
        button = w["button"]
        t = w["unixMs"]
        candidates = phys_by_button.get(button, [])
        cons = consumed.get(button, [])
        lo = bisect.bisect_left(candidates, t - WINDOW_PAIR_WINDOW_MS)
        hi = bisect.bisect_right(candidates, t + WINDOW_PAIR_WINDOW_MS)
        best = -1
        best_dt = WINDOW_PAIR_WINDOW_MS + 1
        for j in range(lo, hi):
            if cons[j]:
                continue
            d = abs(candidates[j] - t)
            if d < best_dt:
                best_dt = d
                best = j
        if best >= 0:
            cons[best] = True
        else:
            unmatched += 1

    rate = unmatched / len(win_clicks)
    note = ("A real click passes through the OS mouse hook *before* the "
            "game receives it. A click that arrives at the game window "
            "without a matching physical event was injected directly "
            "(PostMessage / SendMessage / ControlClick) - the signature "
            "of a stealth autoclicker.")

    if unmatched >= WINDOW_INJECTED_HIGH:
        return ("high", label,
                f"{unmatched} of {len(win_clicks)} clicks the game "
                f"received ({rate*100:.1f}%) had no matching physical "
                f"click - these were injected straight into the game's "
                f"message queue.",
                [note])
    if unmatched >= WINDOW_INJECTED_MEDIUM:
        return ("medium", label,
                f"{unmatched} of {len(win_clicks)} clicks the game "
                f"received ({rate*100:.1f}%) had no matching physical "
                f"click - more than expected from timing noise alone.",
                [note])
    return ("clean", label,
            f"clean - {unmatched} of {len(win_clicks)} window-clicks "
            f"unmatched ({rate*100:.1f}%) - within timing noise.", [])


def collect_findings(events):
    return [
        check_injection_flags(events),     # 1a - OS-level injected flag
        check_window_injection(events),    # 1b - in-game window pairing
        check_click_burst_rate(events),    # 2a
        check_click_rate_minute(events),   # 2b
        check_fast_click_runs(events),     # 3
        check_click_clusters(events),      # 4a/4b
        check_key_hold_short(events),      # 5b
        check_same_pixel(events),          # 6
    ]


def render_verdict(match_id, events, findings):
    start = _find_meta(events, "match_start")
    end = _find_meta(events, "match_end")
    duration_ms = (end["unixMs"] - start["unixMs"]) if (start and end) else None
    process = (start or {}).get("foregroundProcess", "?")
    pixel = most_clicked_pixel(events)
    if start:
        played_ms = start["unixMs"]
    elif events:
        played_ms = min(e["unixMs"] for e in events)
    else:
        played_ms = None

    high_count = sum(1 for f in findings if f[0] == "high")
    medium_count = sum(1 for f in findings if f[0] == "medium")

    if high_count >= 1:
        verdict = "Likely cheating"
        summary = ("One or more strong indicators of automated input. "
                   "Manual review strongly recommended.")
    elif medium_count >= 2:
        verdict = "Suspicious"
        summary = "Multiple weaker anomalies found - manual review recommended."
    else:
        verdict = "Clean"
        summary = ("No significant anomalies. Any findings below are isolated "
                   "and within normal play.")

    out = []
    out.append(f"# Fairplay verdict: {verdict}")
    out.append("")
    out.append(f"- **Match ID:** `{match_id}`")
    player = (start or {}).get("player")
    map_name = (start or {}).get("map")
    if player:
        out.append(f"- **Player:** `{player}`")
    if map_name:
        out.append(f"- **Map:** {map_name}")
    out.append(f"- **Game process:** `{process}`")
    if played_ms is not None:
        out.append(f"- **Date played:** {_fmt_datetime(played_ms)}")
    if duration_ms is not None:
        out.append(f"- **Duration:** {duration_ms/1000:.1f}s")
    out.append(f"- **Total events:** {len(events)}")
    if pixel:
        x, y, n, tot, inj = pixel
        win_note = (f" ({inj} of those {n} injected)"
                    if _has_window_layer(events) else "")
        out.append(f"- **Most-clicked pixel:** ({x},{y}) - {n} of {tot} clicks"
                   f"{win_note}")
    else:
        out.append("- **Most-clicked pixel:** n/a (no positioned clicks)")
    out.append("")
    out.append(f"**Conclusion:** {summary}")
    out.append("")
    out.append("## Checks")
    out.append("")
    for sev, label, message, details in findings:
        if sev in ("high", "medium"):
            # Flagged check: bare title line, then the finding and the
            # reasoning each as their own bullet underneath.
            out.append(f"- `[{sev}]` **{label}**")
            out.append(f"    - {message}")
        else:
            # Clean / skipped / low: a single line is enough.
            out.append(f"- `[{sev}]` **{label}** - {message}")
        for d in details:
            out.append(f"    - {d}")
    out.append("")
    out.append("---")
    out.append("_Auto-generated by analyze_match.py. Every check is logged, "
               "including clean ones. The final decision rests with an admin._")
    return "\n".join(out) + "\n"


def main(argv):
    if len(argv) < 3:
        print("Usage: analyze_match.py <keylog.jsonl> <matchId>", file=sys.stderr)
        return 2

    jsonl_path = Path(argv[1])
    match_id = argv[2]

    if not jsonl_path.exists():
        print(f"Input not found: {jsonl_path}", file=sys.stderr)
        return 1

    events = load_events(jsonl_path, match_id)
    if not events:
        print(f"No events for match {match_id}", file=sys.stderr)
        return 1

    findings = collect_findings(events)
    verdict_text = render_verdict(match_id, events, findings)

    out_path = jsonl_path.parent / f"verdict-{match_id}.md"
    out_path.write_text(verdict_text, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
