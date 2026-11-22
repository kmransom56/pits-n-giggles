"""Local voice-stack benchmark: Piper TTS, faster-whisper STT (closed loop), Ollama selector."""
import json, os, statistics, sys, time, wave, io
import numpy as np, requests

from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
W = os.environ.get("PNG_BENCH_HOME", str(ROOT))  # expects W/models/{piper,whisper}
OUT = str(Path(__file__).resolve().parent / "results")
res = {"cpu": os.cpu_count()}

def summ(xs):
    xs = sorted(xs); n = len(xs)
    return {"n": n, "p50": round(xs[n // 2], 3), "min": round(xs[0], 3), "max": round(xs[-1], 3),
            "mean": round(statistics.mean(xs), 3)}

# ---------------- Piper
from piper import PiperVoice
t = time.perf_counter(); voice = PiperVoice.load(f"{W}/models/piper/en_GB-alan-medium.onnx")
res["piper_load_s"] = round(time.perf_counter() - t, 3)
phrases = {
    "ack": "Go ahead.",
    "short": "Fronts at thirty three percent, rears at twenty nine.",
    "medium": "Box this lap for mediums. Gap behind is plus one point two seconds, you will rejoin ahead of Norris.",
    "long": ("Copy. Fuel is plus zero point six laps, tyre wear is thirty one percent average, "
             "rain is five percent in the next fifteen minutes, so stay out and manage the rears through sector two. "
             "We will review the pit window in three laps."),
}
piper = {}
audio_for_stt = {}
for k, text in phrases.items():
    ttfa, tot, durs = [], [], []
    for i in range(5):
        t0 = time.perf_counter(); first = None; pcm = b""; rate = 22050
        for ch in voice.synthesize(text):
            if first is None: first = time.perf_counter() - t0; rate = ch.sample_rate
            pcm += ch.audio_int16_bytes
        tot.append(time.perf_counter() - t0); ttfa.append(first); durs.append(len(pcm) / 2 / rate)
    piper[k] = {"chars": len(text), "time_to_first_chunk_s": summ(ttfa), "synth_total_s": summ(tot),
                "audio_s": round(durs[0], 2), "rtf": round(statistics.median(tot) / durs[0], 3)}
    audio_for_stt[k] = (np.frombuffer(pcm, dtype=np.int16), rate)
res["piper"] = piper

# questions the driver might ask -> synth with Piper -> resample 16k -> whisper (closed loop)
questions = ["Radio, what is my tyre wear?", "Engineer, how much fuel do I have?",
             "Radio, what's the gap to the car behind?", "Radio, should I box for inters?"]
q_audio = []
for q in questions:
    pcm = b""; rate = 22050
    for ch in voice.synthesize(q): rate = ch.sample_rate; pcm += ch.audio_int16_bytes
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    n16 = int(len(x) * 16000 / rate)
    x16 = np.interp(np.linspace(0, len(x) - 1, n16), np.arange(len(x)), x).astype(np.float32)
    q_audio.append((q, x16))

# ---------------- faster-whisper
sys.path.insert(0, str(ROOT))
from faster_whisper import WhisperModel
F1_PROMPT = ("Radio, engineer. Box box. Tyres, softs, mediums, hards, inters, wets. "
             "Fuel, ERS, DRS, gap, undercut, overcut, pit window, safety car, VSC, lap time, sector.")
stt = {}
for m in ("tiny.en", "base.en", "small.en"):
    for threads in (2,):
        t = time.perf_counter()
        model = WhisperModel(m, device="cpu", compute_type="int8", cpu_threads=threads, download_root=f"{W}/models/whisper")
        load = time.perf_counter() - t
        lat, out = [], []
        for q, x in q_audio:
            model.transcribe(x[:16000], language="en", beam_size=1)  # warm
            for _ in range(3):
                t0 = time.perf_counter()
                segs, _ = model.transcribe(x, language="en", beam_size=1, vad_filter=True,
                                           initial_prompt=F1_PROMPT, condition_on_previous_text=False)
                text = " ".join(s.text.strip() for s in segs).strip()
                lat.append(time.perf_counter() - t0)
            out.append({"ref": q, "hyp": text, "audio_s": round(len(x) / 16000, 2)})
        stt[f"{m}@{threads}t"] = {"load_s": round(load, 2), "latency_s": summ(lat), "transcripts": out}
        del model
res["whisper"] = stt

# ---------------- Ollama selector (mirrors LocalEngineer._select_card payload)
from apps.voice.knowledge import build_context, retrieve_cards
from apps.voice.contracts import Intent, Evidence
ev = Evidence("complex", 42, 1, 3, time.monotonic() + 5, time.monotonic() + 5, None,
              {"tyres": {"compound": "Medium", "age_laps": 9, "wear_avg_pct": 31.5},
               "fuel": {"surplus_laps_live": 0.6}, "weather": {"rain_pct_next_15m": 5}}, (), ())
q = "should I pit now for inters or stay out"
cards = retrieve_cards(Intent("complex"), q, game_season=None)
ctx = build_context(q, ev, cards) or q
res["selector_prompt_chars"] = len(ctx)
llm = {}
for model in ("qwen2.5:1.5b", "llama3.2:3b", "llama3.1:8b"):
    runs = []
    for i in range(4):
        payload = {"model": model, "prompt": ctx, "stream": False, "keep_alive": "2h",
                   "options": {"temperature": 0, "num_predict": 8, "num_ctx": 4096}}
        t0 = time.perf_counter(); r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=600).json()
        wall = time.perf_counter() - t0
        runs.append({"wall_s": round(wall, 2), "load_s": round(r.get("load_duration", 0) / 1e9, 2),
                     "prompt_tokens": r.get("prompt_eval_count"), "prompt_eval_s": round(r.get("prompt_eval_duration", 0) / 1e9, 2),
                     "gen_tokens": r.get("eval_count"), "gen_tok_per_s": round(r.get("eval_count", 0) / max(1e-9, r.get("eval_duration", 1) / 1e9), 2),
                     "response": r.get("response", "")[:40]})
    # free-form 1-2 sentence answer (what a streaming engineer would need)
    t0 = time.perf_counter()
    r = requests.post("http://127.0.0.1:11434/api/generate", json={"model": model, "stream": False, "keep_alive": "2h",
        "prompt": "You are an F1 race engineer. In one short sentence: tyres medium 9 laps 31% wear, rain 5%, fuel +0.6 laps. Should the driver pit for inters?",
        "options": {"temperature": 0, "num_predict": 40, "num_ctx": 2048}}, timeout=600).json()
    llm[model] = {"selector_runs": runs, "freeform_40tok": {"wall_s": round(time.perf_counter() - t0, 2),
                  "gen_tok_per_s": round(r.get("eval_count", 0) / max(1e-9, r.get("eval_duration", 1) / 1e9), 2),
                  "text": r.get("response", "")[:160]}}
    requests.post("http://127.0.0.1:11434/api/generate", json={"model": model, "keep_alive": 0})  # unload
res["ollama"] = llm
json.dump(res, open(f"{OUT}/voice.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:8000])
