import json, os, itertools, subprocess, numpy as np, soundfile as sf
from PIL import Image
from scipy.signal import butter, sosfilt
W, H, SR, LEAD = 1080, 1920, 48000, 0.25
KIT = "src/glasshouse/video-kit"
SCRIPT = ("Your grandmother kept one door locked her whole life. | The day you finally got it open, | you found nothing but glass, and rain. | "
 "An old glasshouse. | Cold, leaking, long forgotten. | You sealed every pane. | You saved up for a heater. | And slowly, it became | "
 "the warmest corner of the house. | Every evening, you sit here | with hot tea and a good book. | Then, one autumn afternoon, | "
 "something scratched at the glass. | Two amber eyes. | An auburn coat, shivering in the wind. | You opened the door. | "
 "He walked straight past you, | and curled up in the armchair. | As if he had done it | a hundred times before. | "
 "You cut him a little door of his own. | And then, in her desk, | you found an old photograph. | "
 "Your grandmother, in that same armchair, | fifty years younger. | With a fox asleep in her lap.")
words = json.load(open("el/words3.json"))
phr = [p.split() for p in SCRIPT.split("|")]
assert sum(len(p) for p in phr) == len(words), (sum(len(p) for p in phr), len(words))
def wt(name, nth=0):
    hits = [w for w in words if w[0].lower().strip(".,?") == name]; return hits[nth][1] + LEAD
VO_END = words[-1][2] + LEAD
T_DOOR = VO_END; T_OUT = VO_END + 1.3; D = T_OUT + 2.4
T_WORK, T_WARM, T_ONE = wt("sealed"), wt("warmest") + 0.6, wt("then", 1) - 0.4
T_PH = wt("photograph")
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def split_lines(ws, maxc=21):
    for n in (1, 2, 3):
        best = None
        for cuts in itertools.combinations(range(1, len(ws)), n - 1):
            parts = [" ".join(ws[a:b]) for a, b in zip((0,) + cuts, cuts + (len(ws),))]
            if max(map(len, parts)) <= maxc:
                sc = max(map(len, parts)) - min(map(len, parts))
                if best is None or sc < best[0]: best = (sc, parts)
        if best: return best[1]
    return [" ".join(ws)]
cues, i = [], 0
for p in phr:
    seg = words[i:i + len(p)]; i += len(p); h = len(p) // 2 + 1
    groups = [(p, seg)] if len(" ".join(p)) <= 40 or not cues else [(p[:h], seg[:h]), (p[h:], seg[h:])]
    for g, s in groups: cues.append([g, s[0][1] + LEAD, s[-1][2] + LEAD])
ev = []
for n, (g, a, b) in enumerate(cues):
    last = n == len(cues) - 1
    end = min(b + 0.45, cues[n + 1][1] - 0.09) if not last else T_OUT - 0.05
    tag = "{\\fad(200,300)\\fs96\\c&H7FD0FF&}" if last else "{\\fad(110,90)}"
    ev.append(f"Dialogue: 0,{ts(max(a - 0.05, 0))},{ts(end)},Cap,,0,0,0,,{tag}" + "\\N".join(split_lines(g, 19 if last else 21)))
ev.append(f"Dialogue: 0,{ts(T_OUT + 0.5)},{ts(D - 0.15)},Cap,,0,0,0,,{{\\fad(300,300)\\fs52\\c&H9CCBF2&}}to be continued…")
open("p3.ass", "w").write(f"""[Script Info]
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
Image.new("RGBA", (1138, 640), (40, 62, 96, 70)).save("cold.png")
Image.new("RGB", (1138, 640), (3, 5, 14)).save("black.png")
# K1: cold, faded "memory" grade that warms up as the house is restored. K2: darkness closing in on the last line.
K1 = f"if(lt(T,{T_WORK:.2f}),1,if(lt(T,{T_WARM:.2f}),1-(T-{T_WORK:.2f})/{T_WARM - T_WORK:.2f},0))"
K2 = f"if(lt(T,{T_ONE:.2f}),0,if(lt(T,{T_OUT:.2f}),0.62*(T-{T_ONE:.2f})/{T_OUT - T_ONE:.2f},1))"
KS = f"if(lt(T,{T_PH - 0.6:.2f}),0,min(0.9,(T-{T_PH - 0.6:.2f})/2.2*0.9))"
# ---------- sound effects ----------
rng = np.random.default_rng(11); N = int(D * SR); sfx = np.zeros(N, np.float32)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x).astype(np.float32)
def put(x, t, gain=1.0):
    a = int(t * SR); b = min(N, a + len(x)); sfx[a:b] += gain * x[:b - a]
def tt(d): return np.arange(int(d * SR)) / SR
def knock(f1, f2, d=0.2):
    t = tt(d); return (np.sin(2*np.pi*f1*t) * np.exp(-t/0.045) + 0.5*np.sin(2*np.pi*f2*t) * np.exp(-t/0.02) + 0.35*lp(rng.standard_normal(len(t)), 700) * np.exp(-t/0.015)).astype(np.float32)
def swipe(d, lo=1400, hi=5200):
    t = tt(d); return bp(rng.standard_normal(len(t)), lo, hi) * np.hanning(len(t)) ** 1.5
def clip(name, fade=0.15):
    p = f"el/{name}.wav"
    if not os.path.exists(p): return None
    x = sf.read(p, dtype="float32")[0]; x = x / max(np.abs(x).max(), 1e-6); n = int(fade * SR); x[-n:] *= np.linspace(1, 0, n); return x
used = []
def fx(name, t, gain):
    x = clip(name)
    if x is not None: put(x, t, gain); used.append(name)
    return x is not None
fx("creak", wt("open") - 1.3, 0.13)                                        # the door finally opens
put(knock(140, 380, 0.2), wt("heater") + 0.45, 0.10)                         # heater set down
if not fx("scratch", wt("scratched") + 0.45, 0.22):                          # scratching at the glass
    for k in (0.5, 0.78, 1.1): put(swipe(0.16, 2600, 9000), wt("scratched") + k, 0.09)
t = tt(3.2); put((lp(rng.standard_normal(len(t)), 420) * np.hanning(len(t)) ** 1.2 * (1 + 0.3*np.sin(2*np.pi*0.9*t))).astype(np.float32), wt("shivering") - 0.9, 0.5)   # a gust of wind
for k, d in enumerate((0.4, 0.3)): put(swipe(d, 2200, 8000), T_PH + 0.5 + 0.5 * k, 0.05)                                   # the photograph
t0 = T_ONE; t = tt(T_OUT - t0); u = t / t[-1]
dr = sum(a * np.sin(2*np.pi*f*t + 2*np.pi*0.3*np.sin(2*np.pi*r*t)) for f, a, r in ((55, 1, .07), (82.5, .55, .11), (110.6, .4, .05), (165.4, .22, .09), (58.3, .35, .13)))
dr = dr + 0.5 * bp(rng.standard_normal(len(t)), 600, 2400) * (0.5 + 0.5*np.sin(2*np.pi*0.21*t)) * u**2
put((dr * (0.1 + 0.9 * u**2) * np.minimum(1, (t[-1] - t) / 0.05)).astype(np.float32), t0, 0.075)
t = tt(2.4); boom = np.sin(2*np.pi*np.cumsum(38 + 40*np.exp(-t/0.12))/SR) * np.exp(-t/0.55) + 0.4*lp(rng.standard_normal(len(t)), 160) * np.exp(-t/0.25)
put(boom.astype(np.float32), T_OUT, 0.34)
print("sfx peak", float(np.abs(sfx).max()), "clips", used); sf.write("sfx3.wav", np.clip(sfx, -0.95, 0.95), SR)
# ---------- render ----------
x0, x1 = 1480, 2185
pan = f"{x0}+({x1}-{x0})*(1-cos(PI*min(t/{T_OUT:.2f},1)))/2"
duck = f"if(lt(t,{t0:.2f}),0.8,if(lt(t,{T_OUT:.2f}),max(0.3,0.8-(t-{t0:.2f})*0.05),0))"
fc = (f"[0:v]fps=30,scale=1138:640:flags=area,eq=saturation=1.2:contrast=1.06,format=gbrp,split[n0][c0];"
      f"[c0]hue=s=0.3,eq=brightness=-0.05[c1];[c1][6:v]overlay=format=auto,format=gbrp[cold];"
      f"[n0][cold]blend=all_expr='A*(1-({K1}))+B*({K1})'"
      f",split[w0][w1];[w1]colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0,eq=contrast=0.92:brightness=-0.04,format=gbrp[sep];"
      f"[w0][sep]blend=all_expr='A*(1-({KS}))+B*({KS})',fade=t=out:st={T_OUT:.2f}:d=0.04,format=gbrp,"
      f"scale=3414:1920:flags=neighbor,crop=1080:1920:x='{pan}':y=0,format=gbrp,split=3[s][b0][g0];"
      f"[b0]gblur=sigma=7[bl];[1:v]format=gray,scale=1080:1920[m];[s][bl][m]maskedmerge[tsd];"
      f"[g0]curves=all='0/0 0.55/0 1/1',gblur=sigma=22[glow];[tsd][glow]blend=all_mode=screen:all_opacity=0.5[lit];"
      f"[lit][2:v]overlay=format=auto,format=yuv420p,ass=p3.ass:fontsdir=fonts,fade=in:st=0:d=0.2,fade=out:st={D-0.5:.2f}:d=0.5[v];"
      f"[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.6[amb];[4:a]aresample=48000,volume='{duck}':eval=frame[mu];"
      f"[5:a]aresample=48000,highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160,volume=3.1,adelay={int(LEAD*1000)}:all=1,pan=stereo|c0=c0|c1=c0[vo];"
      f"[7:a]pan=stereo|c0=c0|c1=c0[fx];"
      f"[amb][mu][vo][fx]amix=inputs=4:normalize=0,alimiter=limit=0.89:level=disabled,afade=in:st=0:d=0.25,afade=out:st={D-1.2:.2f}:d=1.2[a]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "118", "-i", f"{KIT}/loop.mp4", "-loop", "1", "-i", "ts.png", "-loop", "1", "-i", "ov.png",
    "-ss", "118", "-i", f"{KIT}/ambience.flac", "-ss", "250", "-i", f"{KIT}/music.flac", "-i", "el/vo3.mp3", "-loop", "1", "-i", "cold.png", "-i", "sfx3.wav", "-loop", "1", "-i", "black.png",
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{D:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "out/autumn-rain-part-3.mp4"], check=True)
print("built", round(D, 2), "photo", round(T_PH, 2), "black", round(T_OUT, 2))
