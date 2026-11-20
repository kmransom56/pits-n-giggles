"""End-to-end MCP/IPC benchmark using the real Pits n' Giggles IPC + MCPBridge code.

Topology (3 OS processes, mirrors production):
  P1 "core":  IpcPubSubBroker + IpcRouter threads, IpcPublisherAsync publishing
              race-table-update at 5 Hz, fake BACKEND dealer answering driver-info-request.
  P2 "mcp":   McpSubscriber + IpcDealerAsync + MCPBridge(http, port 4770) + loop-lag probe.
  P3 bench:   fastmcp.Client measurements + voice TelemetryAdapter end-to-end.
"""
from pathlib import Path
import asyncio, json, logging, multiprocessing as mp, os, statistics, sys, time, copy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

XSUB, XPUB, ROUTER, MCP_PORT = 55835, 55838, 55836, 4770
OUT = str(Path(__file__).resolve().parent / "results")
os.makedirs(OUT, exist_ok=True)
log = logging.getLogger("bench"); log.addHandler(logging.NullHandler())


def make_row(i, player=False):
    return {
        "driver-info": {"index": i, "name": f"Driver{i}", "position": i + 1, "is-player": player,
                         "dnf-status": "", "team": "Team", "telemetry-setting": "Public",
                         "driver-number": 10 + i},
        "delta-info": {"delta-to-car-in-front": 812 + i, "delta-to-leader": 812 * i},
        "lap-info": {"last-lap": {"lap-time-ms": 92345 + i, "s1": 30111, "s2": 31000, "s3": 31234},
                      "best-lap": {"lap-time-ms": 91999 + i}, "speed-trap-record-kmph": 331.2,
                      "current-lap": 14},
        "tyre-info": {"visual-tyre-compound": "Medium", "actual-tyre-compound": "C3", "tyre-age": 9,
                       "current-wear": {"average": 31.5, "front-left-wear": 33.1, "front-right-wear": 35.2,
                                        "rear-left-wear": 28.0, "rear-right-wear": 29.6},
                       "wear-prediction": {"status": True, "rate": {"front-left": 1.1, "front-right": 1.2, "rear-left": 0.9, "rear-right": 0.95},
                                           "predictions": [{"lap": l, "wear": 30 + l} for l in range(15, 35)]},
                       "tyre-stint-history": [{"start-lap": 1, "end-lap": 5, "compound": "Soft"}]},
        "fuel-info": {"fuel-in-tank": 41.2, "fuel-capacity": 110.0, "fuel-mix": "Standard",
                       "surplus-laps-game": 0.8, "current-fuel-rate": 1.62, "last-lap-fuel-used": 1.6,
                       "target-fuel-rate-average": 1.58, "surplus-laps-png": 0.6},
        "ers-info": {"ers-percent": "54%", "ers-mode": "Medium", "ers-harvested": 3.1},
        "damage-info": {"fl-wing-damage": 0, "fr-wing-damage": 2, "rear-wing-damage": 0},
        "pit-info": {"num-pitstops": 1, "pit-status": "None"},
        "penalties": {"warnings": 0, "time-penalties": 0},
    }


def make_payload(uid=42, n=20):
    return {
        "session-uid": uid, "event-type": "Race", "race-ended": False, "is-spectating": False,
        "session-duration-so-far": 1500.0, "session-time-left": 3000.0, "circuit": "Silverstone",
        "current-lap": 14, "total-laps": 52, "track-temperature": 34, "air-temperature": 22,
        "weather-forecast-samples": [{"time-offset": t, "weather": "Light Cloud", "rain-percentage": 5}
                                      for t in (0, 5, 10, 15, 30)],
        "safety-car-status": "NO_SAFETY_CAR", "table-entries": [make_row(i, i == 3) for i in range(n)],
    }


def driver_info_reply(idx):
    return {"ok": True, "data": {
        "index": idx, "curr-lap-num": 14,
        "lap-time-history": {"best-lap-time-lap-num": 9, "best-sector-1-lap-num": 9,
                             "best-sector-2-lap-num": 11, "best-sector-3-lap-num": 7,
                             "lap-history-data": [{"lap-time-in-ms": 92000 + l * 7, "sector-1-time-in-ms": 30000,
                                                   "sector-2-time-in-ms": 31000, "sector-3-time-in-ms": 31000,
                                                   "top-speed-kmph": 330, "lap-valid-bit-flags": 15}
                                                  for l in range(14)]},
        "race-ctrl": [{"lap": l, "type": "OVERTAKE", "message": f"msg {l}"} for l in range(30)],
        "car-damage": {"tyres-wear": [33.1, 35.2, 28.0, 29.6], "tyres-damage": [0, 0, 0, 0],
                       "brakes-damage": [0, 0, 0, 0], "front-left-wing-damage": 0, "front-right-wing-damage": 2,
                       "rear-wing-damage": 0, "floor-damage": 0, "diffuser-damage": 0, "sidepod-damage": 0,
                       "drs-fault": False, "ers-fault": False, "gear-box-damage": 1, "engine-damage": 3,
                       "engine-mguh-wear": 10, "engine-es-wear": 10, "engine-ce-wear": 10, "engine-ice-wear": 10,
                       "engine-mguk-wear": 10, "engine-tc-wear": 10, "engine-blown": False, "engine-seized": False},
    }}


# ------------------------------------------------------------------ P1 core
def core_proc(rate_hz, ready):
    from lib.ipc import IpcPubSubBroker, IpcRouter, IpcPublisherAsync, IpcDealerAsync, PngAppId
    broker = IpcPubSubBroker(xsub_port=XSUB, xpub_port=XPUB, logger=log); broker.run_in_thread()
    router = IpcRouter(port=ROUTER, logger=log); router.run_in_thread()

    async def main():
        pub = IpcPublisherAsync(port=XSUB, logger=log); pub.get_task()
        dealer = IpcDealerAsync(port=ROUTER, identity=str(PngAppId.BACKEND), logger=log)

        @dealer.route("driver-info-request")
        async def _h(data, sender):
            return driver_info_reply(data.get("index"))
        asyncio.create_task(dealer.start())
        base = make_payload()
        ready.set()
        period = 1.0 / rate_hz
        t_start = time.monotonic()
        while True:
            t = time.monotonic()
            base["session-duration-so-far"] = 1500.0 + (t - t_start)
            base["session-time-left"] = 3000.0 - (t - t_start)
            await pub.publish("race-table-update", base)
            await asyncio.sleep(max(0, period - (time.monotonic() - t)))
    asyncio.run(main())


# ------------------------------------------------------------------ P2 mcp
def mcp_proc(ready, lag_file):
    from lib.ipc import IpcDealerAsync, PngAppId
    from apps.mcp_server.subscriber import init_subscriber_task
    from apps.mcp_server.mcp_server import MCPBridge

    async def lag_probe():
        lags = []
        while True:
            t = time.perf_counter(); await asyncio.sleep(0.01)
            lags.append((time.perf_counter() - t - 0.01) * 1000)
            if len(lags) % 200 == 0:
                with open(lag_file, "w") as f: json.dump(lags[-6000:], f)

    async def main():
        tasks = []
        init_subscriber_task(port=XPUB, logger=log, tasks=tasks)
        dealer = IpcDealerAsync(port=ROUTER, identity=str(PngAppId.MCP), logger=log)
        tasks.append(asyncio.create_task(dealer.start()))
        bridge = MCPBridge(dealer=dealer, logger=log, version="bench", transport="http", port=MCP_PORT)
        tasks.append(asyncio.create_task(bridge.run()))
        tasks.append(asyncio.create_task(lag_probe()))
        await asyncio.sleep(1.5); ready.set()
        await asyncio.gather(*tasks)
    asyncio.run(main())


# ------------------------------------------------------------------ helpers
def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summ(xs):
    return {"n": len(xs), "p50_ms": round(pct(xs, 50), 2), "p95_ms": round(pct(xs, 95), 2),
            "p99_ms": round(pct(xs, 99), 2), "mean_ms": round(statistics.mean(xs), 2),
            "max_ms": round(max(xs), 2)}


async def voice_only(url):
    from fastmcp import Client
    from apps.voice.session_tracker import SessionProgressTracker
    from apps.voice.telemetry import TelemetryAdapter
    from apps.voice.direct_answers import answer_direct, classify
    res = {}
    async with Client(url) as c:
        ad = TelemetryAdapter(c, SessionProgressTracker(), epoch_clock=time.time, mono_clock=time.monotonic)
        await ad.collect(classify("what is my tyre wear"), time.monotonic() + 2.0)
        await asyncio.sleep(0.6)
        for q in ("what is my tyre wear", "how much fuel do I have", "what's the gap behind", "when should I pit"):
            intent = classify(q)
            lat, ok_lat, reasons, texts = [], [], {}, None
            for i in range(80):
                await asyncio.sleep(0.037 * (i % 7))
                t = time.perf_counter()
                ev = await ad.collect(intent, time.monotonic() + 2.0)
                ans = answer_direct(intent, ev) if ev.reason is None else None
                dt = (time.perf_counter() - t) * 1000
                lat.append(dt)
                if ans: ok_lat.append(dt); texts = ans.text
                reasons[str(ev.reason)] = reasons.get(str(ev.reason), 0) + 1
            res[f"voice_direct:{intent.topic}"] = {**summ(lat), "success_rate": round(len(ok_lat) / len(lat), 3),
                "ok_p50_ms": round(pct(ok_lat, 50), 1) if ok_lat else None, "reasons": reasons, "sample_answer": texts}
    return res


async def bench_client():
    from fastmcp import Client
    url = f"http://127.0.0.1:{MCP_PORT}/mcp"
    res = {}
    if os.environ.get("VOICE_ONLY"):
        return await voice_only(url)
    # session setup cost
    setups = []
    for _ in range(20):
        t = time.perf_counter()
        async with Client(url) as c:
            await c.list_tools()
        setups.append((time.perf_counter() - t) * 1000)
    res["client_session_open+list_tools"] = summ(setups)

    async with Client(url) as c:
        tools = await c.list_tools(); res["tool_count"] = len(tools)
        sizes = {}
        calls = [("get_session_info", {}), ("get_race_table", {}), ("get_drivers_list", {}),
                 ("get_player_driver_info", {}), ("get_player_tyre_wear", {}), ("get_player_fuel_info", {}),
                 ("get_tyre_wear", {"driver_index": 3}), ("get_fuel_info", {"driver_index": 3}),
                 ("get_driver_lap_times", {"driver_index": 3}), ("get_session_events_for_driver", {"driver_index": 3}),
                 ("get_car_damage", {"driver_index": 3})]
        for name, args in calls:
            for _ in range(10): await c.call_tool(name, args, raise_on_error=False)
            lat = []
            for _ in range(200):
                t = time.perf_counter(); r = await c.call_tool(name, args, raise_on_error=False)
                lat.append((time.perf_counter() - t) * 1000)
            sizes[name] = len(json.dumps(r.structured_content or {}, default=str))
            res[f"tool:{name}"] = {**summ(lat), "resp_bytes": sizes[name]}

        # voice snapshot pattern: 4 tools in parallel on one session
        lat = []
        for _ in range(100):
            t = time.perf_counter()
            await asyncio.gather(*[c.call_tool(n, {}, raise_on_error=False) for n in
                                   ("get_session_info", "get_player_tyre_wear", "get_player_fuel_info", "get_race_table")])
            lat.append((time.perf_counter() - t) * 1000)
        res["voice_snapshot_4_parallel"] = summ(lat)
        lat = []
        for _ in range(100):
            t = time.perf_counter()
            for n in ("get_session_info", "get_race_table", "get_player_tyre_wear"):
                await c.call_tool(n, {}, raise_on_error=False)
            lat.append((time.perf_counter() - t) * 1000)
        res["voice_adapter_3_sequential"] = summ(lat)

    # concurrency sweep on get_race_table (separate sessions)
    for conc in (1, 4, 16):
        lat = []
        async def worker():
            async with Client(url) as c:
                for _ in range(60):
                    t = time.perf_counter(); await c.call_tool("get_race_table", {}, raise_on_error=False)
                    lat.append((time.perf_counter() - t) * 1000)
        t0 = time.perf_counter()
        await asyncio.gather(*[worker() for _ in range(conc)])
        wall = time.perf_counter() - t0
        res[f"concurrency:{conc}:get_race_table"] = {**summ(lat), "throughput_rps": round(len(lat) / wall, 1)}

    # dealer-path concurrency (MCP -> router -> backend)
    for conc in (1, 8):
        lat = []
        async def worker2():
            async with Client(url) as c:
                for _ in range(50):
                    t = time.perf_counter(); await c.call_tool("get_car_damage", {"driver_index": 3}, raise_on_error=False)
                    lat.append((time.perf_counter() - t) * 1000)
        t0 = time.perf_counter()
        await asyncio.gather(*[worker2() for _ in range(conc)])
        wall = time.perf_counter() - t0
        res[f"concurrency:{conc}:get_car_damage(dealer)"] = {**summ(lat), "throughput_rps": round(len(lat) / wall, 1)}

    # voice adapter end-to-end (real TelemetryAdapter + direct answer)
    from apps.voice.session_tracker import SessionProgressTracker
    from apps.voice.telemetry import TelemetryAdapter
    from apps.voice.contracts import Intent
    from apps.voice.direct_answers import answer_direct, classify
    async with Client(url) as c:
        ad = TelemetryAdapter(c, SessionProgressTracker(), epoch_clock=time.time, mono_clock=time.monotonic)
        for q in ("what is my tyre wear", "how much fuel do I have", "what's the gap behind"):
            intent = classify(q)
            lat, reasons, texts = [], {}, None
            for _ in range(60):
                t = time.perf_counter()
                ev = await ad.collect(intent, time.monotonic() + 2.0)
                ans = answer_direct(intent, ev) if ev.reason is None else None
                lat.append((time.perf_counter() - t) * 1000)
                reasons[str(ev.reason)] = reasons.get(str(ev.reason), 0) + 1
                texts = ans.text if ans else None
            res[f"voice_direct:{intent.topic}"] = {**summ(lat), "reasons": reasons, "sample_answer": texts}

    # IPC pub/sub latency observed by a separate subscriber
    from lib.ipc import IpcSubscriberAsync
    sub = IpcSubscriberAsync(port=XPUB, logger=log)
    got = []
    @sub.route("race-table-update")
    async def _r(msg): got.append(time.perf_counter())
    task = asyncio.create_task(sub.run())
    await asyncio.sleep(6)
    sub.close() if hasattr(sub, "close") else None
    task.cancel()
    st = sub.get_stats()
    res["ipc_subscriber_stats_6s"] = st
    if len(got) > 2:
        gaps = [(b - a) * 1000 for a, b in zip(got, got[1:])]
        res["ipc_interarrival_ms"] = summ(gaps)
    return res


def main():
    rate = float(os.environ.get("RATE_HZ", "5"))
    ctx = mp.get_context("spawn")
    r1, r2 = ctx.Event(), ctx.Event()
    lag_file = f"{OUT}/loop_lag_{int(rate)}hz.json"
    p1 = ctx.Process(target=core_proc, args=(rate, r1), daemon=True); p1.start(); r1.wait(10)
    p2 = ctx.Process(target=mcp_proc, args=(r2, lag_file), daemon=True); p2.start(); r2.wait(15)
    time.sleep(1.0)
    res = asyncio.run(bench_client())
    res["publish_rate_hz"] = rate
    res["payload_bytes"] = len(json.dumps(make_payload()))
    time.sleep(2.5)
    try:
        lags = json.load(open(lag_file)); res["mcp_loop_lag"] = summ(lags)
    except Exception as e:
        res["mcp_loop_lag"] = str(e)
    with open(f"{OUT}/mcp_{int(rate)}hz.json", "w") as f: json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:6000])
    p2.terminate(); p1.terminate()


if __name__ == "__main__":
    main()
