import json, subprocess, numpy as np, soundfile as sf
from PIL import Image
from scipy.signal import butter, sosfilt
W, H, SR, LEAD = 1080, 1920, 48000, 0.25
KIT = "src/glasshouse/video-kit"
SCRIPT = ("Someone is already sitting in your armchair. | You know it before the lights even come on. | "
 "You set your umbrella on the counter, | and let out the sigh you’ve been holding all day. | "
 "An autumn leaf still clings to your coat. | You brush it away. | The lamp flickers on. | And there he is. | "
 "Mr. Fox. | Curled up in your spot. | As usual. | You chuckle, and put the kettle on. | "
 "But here is the thing about Mr. Fox. | You never brought him home. | You never even went looking. | "
 "A year ago, this house stood empty, | and you had never seen him before in your life. | "
 "Now, he waits for you every single night. | So… | Where did he come from?")
words = json.load(open("el/words.json"))
phr = [p.split() for p in SCRIPT.split("|")]
assert sum(len(p) for p in phr) == len(words), (sum(len(p) for p in phr), len(words))
def wt(name, nth=0):
    hits = [w for w in words if w[0].lower().strip(".,?") == name]; return hits[nth][1] + LEAD
VO_END = words[-1][2] + LEAD
T_ON = wt("flickers"); T_OUT = VO_END + 0.65; D = T_OUT + 2.9
# ---------- captions ----------
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def split_lines(ws, maxc=21):
    best = None
    for n in (1, 2, 3):
        # balanced split into n lines
        import itertools
        for cuts in itertools.combinations(range(1, len(ws)), n - 1):
            parts = [" ".join(ws[a:b]) for a, b in zip((0,) + cuts, cuts + (len(ws),))]
            if max(map(len, parts)) <= maxc:
                sc = max(map(len, parts)) - min(map(len, parts))
                if best is None or sc < best[0]: best = (sc, parts)
        if best: return best[1]
    return [" ".join(ws)]
cues, i = [], 0
for p in phr:
    seg = words[i:i + len(p)]; i += len(p)
    # break long phrases in two caption cards
    groups = [(p, seg)] if len(" ".join(p)) <= 40 else [(p[:len(p)//2 + 1], seg[:len(p)//2 + 1]), (p[len(p)//2 + 1:], seg[len(p)//2 + 1:])]
    for g, s in groups: cues.append([" ".join(g), g, s[0][1] + LEAD, s[-1][2] + LEAD])
ev = []
for n, (text, g, a, b) in enumerate(cues):
    end = min(b + 0.45, cues[n + 1][2] - 0.02) if n + 1 < len(cues) else b + 0.9
    last = n == len(cues) - 1
    tag = "{\\fad(200,400)\\fs96\\c&H7FD0FF&}" if last else "{\\fad(110,90)}"
    ev.append(f"Dialogue: 0,{ts(max(a - 0.05, 0))},{ts(end)},Cap,,0,0,0,,{tag}" + "\\N".join(split_lines(g, 19 if last else 21)))
ev.append(f"Dialogue: 0,{ts(T_OUT + 0.5)},{ts(D - 0.15)},Cap,,0,0,0,,{{\\fad(300,300)\\fs52\\c&H9CCBF2&}}to be continued…")
open("p1.ass", "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Pixelify Sans SemiBold,84,&H00F4FAFF,&H00FFFFFF,&H00160C0A,&H96000000,0,0,0,0,100,100,1,0,1,7,5,5,70,200,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
# ---------- lamp-off overlay (in the 1138x640 pixel-art space) ----------
yy, xx = np.mgrid[0:640, 0:1138].astype(np.float32)
g = lambda cx, cy, s: np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
al = np.clip(0.50 + 0.43 * g(769, 262, 62) + 0.16 * g(800, 400, 210), 0, 0.94)
dk = np.zeros((640, 1138, 4), np.uint8); dk[..., 0] = 5; dk[..., 1] = 9; dk[..., 2] = 26; dk[..., 3] = (al * 255).astype(np.uint8)
Image.fromarray(dk).save("dark.png")
# darkness K(T): 1 = lamp off, 0 = lamp on
on = [(0.00, 0.07, 0.25), (0.07, 0.22, 1), (0.22, 0.28, 0.4), (0.28, 0.50, 0.95), (0.50, 0.60, 0.15), (0.60, 0.72, 0.8), (0.72, 0.85, 0.1), (0.85, 0.95, 0.45)]
out = [(0.00, 0.07, 0.6), (0.07, 0.15, 0.1), (0.15, 0.25, 0.8), (0.25, 0.31, 0.2)]
K = "1"
for a, b, v in reversed(out): K = f"if(lt(T,{T_OUT + b:.3f}),{v},{K})"
K = f"if(lt(T,{T_OUT:.3f}),0,{K})"
K = f"if(lt(T,{T_ON + 1.25:.3f}),0.45*({T_ON + 1.25:.3f}-T)/0.3,{K})"
for a, b, v in reversed(on): K = f"if(lt(T,{T_ON + b:.3f}),{v},{K})"
K = f"if(lt(T,{T_ON:.3f}),1,{K})"
# ---------- sound effects ----------
rng = np.random.default_rng(7); N = int(D * SR); sfx = np.zeros(N, np.float32)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x).astype(np.float32)
def put(x, t, gain=1.0):
    a = int(t * SR); b = min(N, a + len(x)); sfx[a:b] += gain * x[:b - a]
def tt(d): return np.arange(int(d * SR)) / SR
def knock(f1, f2, d=0.16):
    t = tt(d); return (np.sin(2*np.pi*f1*t) * np.exp(-t/0.035) + 0.5*np.sin(2*np.pi*f2*t) * np.exp(-t/0.018) + 0.35*lp(rng.standard_normal(len(t)), 900) * np.exp(-t/0.012)).astype(np.float32)
def swipe(d, lo=1400, hi=5200):
    t = tt(d); return bp(rng.standard_normal(len(t)), lo, hi) * np.hanning(len(t)) ** 1.5
def click():
    t = tt(0.03); return (np.sin(2*np.pi*2300*t) * np.exp(-t/0.004) + 0.6*bp(rng.standard_normal(len(t)), 2500, 9000) * np.exp(-t/0.003)).astype(np.float32)
def buzz(d):
    t = tt(d); x = sum(np.sin(2*np.pi*100*k*t + k) / k for k in range(1, 14)); x = bp(x.astype(np.float32), 180, 4200)
    cr = (rng.random(len(t)) > 0.9985) * rng.standard_normal(len(t)); x = x / np.abs(x).max() + 2.5 * bp(cr.astype(np.float32), 1500, 8000)
    e = np.minimum(1, np.minimum(t, d - t) / 0.004); return (x * e).astype(np.float32)
tc = wt("counter")
put(knock(170, 410), tc + 0.05, 0.20); put(knock(230, 560, 0.1), tc + 0.19, 0.09); put(swipe(0.45, 900, 3800), tc - 0.12, 0.05)   # umbrella on the counter
tb = wt("brush"); put(swipe(0.22), tb + 0.02, 0.10); put(swipe(0.26), tb + 0.33, 0.12)                                           # brushing the leaf off
put(click(), T_ON - 0.03, 0.22)                                                                                                # lamp switch
for a, b, v in on:
    if v < 0.6: put(buzz(b - a), T_ON + a, 0.10 * (1 - v))
t = tt(1.6); put(buzz(1.6) * np.exp(-t / 0.4), T_ON + 0.95, 0.035)
kt = sf.read("el/kettle.wav", dtype="float32")[0]; kt = kt / max(np.abs(kt).max(), 1e-6)
put(kt, wt("kettle") + 0.12, 0.16)                                                                                             # kettle (ElevenLabs)
# tension drone under the reveal, swelling to the last line
t0 = wt("but"); t = tt(T_OUT + 0.3 - t0); u = t / t[-1]
dr = sum(a * np.sin(2*np.pi*f*t + 2*np.pi*0.3*np.sin(2*np.pi*r*t)) for f, a, r in ((55, 1, .07), (82.5, .55, .11), (110.6, .4, .05), (165.4, .22, .09), (58.3, .35, .13)))
dr = dr + 0.5 * bp(rng.standard_normal(len(t)), 600, 2400) * (0.5 + 0.5*np.sin(2*np.pi*0.21*t)) * u**2
put((dr * (0.08 + 0.92 * u**2.2) * np.minimum(1, (t[-1] - t) / 0.08)).astype(np.float32), t0, 0.03)
for a, b, v in out:
    if v < 0.6: put(buzz(b - a), T_OUT + a, 0.11)
put(click(), T_OUT + 0.31, 0.2)                                                                                                # lamp dies
t = tt(2.4); boom = np.sin(2*np.pi*np.cumsum(38 + 40*np.exp(-t/0.12))/SR) * np.exp(-t/0.55) + 0.4*lp(rng.standard_normal(len(t)), 160) * np.exp(-t/0.25)
put(boom.astype(np.float32), T_OUT + 0.31, 0.32)
print("sfx peak", float(np.abs(sfx).max())); sf.write("sfx1.wav", np.clip(sfx, -0.95, 0.95), SR)
# ---------- render ----------
x0, x1 = 2110, 2185
pan = f"{x0}+({x1}-{x0})*(1-cos(PI*min(t/{D:.2f},1)))/2"
duck = f"if(lt(t,{t0:.2f}),0.8,if(lt(t,{T_OUT:.2f}),max(0.34,0.8-(t-{t0:.2f})*0.035),max(0.0,0.34-(t-{T_OUT:.2f})*1.2)))"
fc = (f"[0:v]fps=30,scale=1138:640:flags=area,eq=saturation=1.2:contrast=1.06,format=gbrp,split[lit0][d0];"
      f"[d0][6:v]overlay=format=auto,format=gbrp[dark];[lit0][dark]blend=all_expr='A*(1-({K}))+B*({K})',"
      f"scale=3414:1920:flags=neighbor,crop=1080:1920:x='{pan}':y=0,format=gbrp,split=3[s][b0][g0];"
      f"[b0]gblur=sigma=7[bl];[1:v]format=gray,scale=1080:1920[m];[s][bl][m]maskedmerge[tsd];"
      f"[g0]curves=all='0/0 0.55/0 1/1',gblur=sigma=22[glow];[tsd][glow]blend=all_mode=screen:all_opacity=0.5[lit];"
      f"[lit][2:v]overlay=format=auto,format=yuv420p,ass=p1.ass:fontsdir=fonts,fade=in:st=0:d=0.2,fade=out:st={D-0.5:.2f}:d=0.5[v];"
      f"[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.6[amb];[4:a]aresample=48000,volume='{duck}':eval=frame[mu];"
      f"[5:a]aresample=48000,highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160,volume=3.1,adelay={int(LEAD*1000)}:all=1,pan=stereo|c0=c0|c1=c0[vo];"
      f"[7:a]volume=0.3,pan=stereo|c0=c0|c1=c0[fx];"
      f"[amb][mu][vo][fx]amix=inputs=4:normalize=0,alimiter=limit=0.89:level=disabled,afade=in:st=0:d=0.25,afade=out:st={D-1.2:.2f}:d=1.2[a]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4", "-i", f"{KIT}/loop.mp4", "-loop", "1", "-i", "ts.png", "-loop", "1", "-i", "ov.png",
    "-ss", "4", "-i", f"{KIT}/ambience.flac", "-ss", "8", "-i", f"{KIT}/music.flac", "-i", "el/vo.mp3", "-loop", "1", "-i", "dark.png", "-i", "sfx1.wav",
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{D:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "out/autumn-rain-part-1.mp4"], check=True)
print("built", round(D, 2), "lamp on", round(T_ON, 2), "lamp out", round(T_OUT, 2))
