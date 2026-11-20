import json, re, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
from story import PARTS
k = Kokoro("tts/kokoro.onnx", "tts/voices.bin")
VOICE, SPEED, SR = "af_heart", 0.86, 24000
def trim(x, th=0.004):
    idx = np.where(np.abs(x) > th)[0]
    return x[max(0, idx[0]-600): idx[-1]+2400] if len(idx) else x
for pi, (_, _, lines) in enumerate(PARTS, 1):
    # group lines into sentences so prosody is natural, keep line boundaries for captions
    out, cues, t = [np.zeros(int(SR*1.6), np.float32)], [], 1.6
    group = []
    for li, line in enumerate(lines):
        group.append(line)
        if re.search(r"[.!?”]$", line):
            text = " ".join(group).replace("“", '"').replace("”", '"').replace("’", "'")
            a, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us"); assert sr == SR
            a = trim(a.astype(np.float32)); d = len(a)/SR
            tot = sum(len(g) for g in group); c = t
            for g in group:
                gd = d*len(g)/tot; cues.append({"text": g, "start": round(c, 3), "end": round(c+gd, 3)}); c += gd
            gap = 0.55 if len(text) > 14 else 0.75
            out += [a, np.zeros(int(SR*gap), np.float32)]; t += d + gap; group = []
    out.append(np.zeros(int(SR*2.5), np.float32))
    y = np.concatenate(out); sf.write(f"vo{pi}.wav", y, SR)
    json.dump({"dur": len(y)/SR, "cues": cues}, open(f"cues{pi}.json", "w"), indent=1)
    print(pi, round(len(y)/SR, 1))
