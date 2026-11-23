# Generic builder for parts 4-6. Usage: python3 build_part.py <n>
import json, re, sys, difflib, itertools, subprocess, numpy as np, soundfile as sf
from PIL import Image
from scipy.signal import butter, sosfilt
W, H, SR, LEAD = 1080, 1920, 48000, 0.25
KIT = "src/glasshouse/video-kit"
P = int(sys.argv[1])
SCRIPTS = {
4: ("Foxes do not live for fifty years. | You know that. | You looked it up twice. | But the fox in your grandmother’s photograph | "
    "has the same white tip on his tail. | The same way of sleeping, | with his nose tucked under. | So you spend the evening on the floor, | "
    "going through her desk. | Receipts. | Seed catalogues. | The birthday cards you sent, | and the gaps where you forgot. | And more photographs. | "
    "Nineteen seventy-four. | Nineteen eighty-nine. | Two thousand and six. | Her hair goes grey. | The armchair changes colour. | "
    "The fox never changes at all. | On the back of every one, | in her handwriting, | the same four words. | He came back again. | "
    "Mr. Fox hasn’t moved. | But you are fairly sure | he is listening. | And at the very bottom of the drawer, | there is an envelope | with your name on it."),
5: ("Your grandmother’s last letter | begins with an apology. | “I’m sorry about the roof,” she wrote. | “And about your cousins.” | "
    "You laugh, and then you don’t. | She knew exactly what they would say. | She left it to you anyway. | “They would have sold it by spring. | "
    "You were the only one who ever stayed | for a second cup of tea.” | You think of the visits you cancelled. | The calls you kept short. | "
    "She doesn’t mention those. | “I was your age when I came here. | No money, no plan, | and a winter coming. | He was on the doorstep the first night. | "
    "He is not a pet. | He comes with the house, | to whoever needs it | as much as it needs them. | Leave his door unlatched. | "
    "And when the first frost comes, | follow him.” | You fold the letter. | Outside, the rain has stopped. | The glass is turning white."),
6: ("On the night of the first frost, | the armchair was empty. | His little door was still swinging. | You pulled a coat over your pyjamas | "
    "and followed the paw prints, | down the garden, past the birch, | to a shed you had never managed to open. | Tonight, the door stood ajar. | "
    "Inside, shelves of paper envelopes, | in her handwriting. | Seeds. | Bulbs. | Fifty autumns, saved and labelled. | And one envelope set apart. | "
    "“For whoever comes next. | Plant these when you are ready to stay.” | Your cousins called in the spring. | The market had changed, they said. | "
    "They had an offer for you. | A generous one. | You looked out at the garden, | coming up green | in rows you had planted yourself. | "
    "“It’s not for sale.” | That evening, you came in from the rain, | and set your umbrella on the counter. | "
    "Someone was already sitting in your armchair. | You wouldn’t have it any other way."),
}
words = json.load(open(f"el/words{P}.json"))
phr = [p.split() for p in SCRIPTS[P].split("|")]
# ---- align script words to the transcript (numbers and spelling may differ) ----
NUM = {"1974": "nineteen seventyfour", "1989": "nineteen eightynine", "2006": "two thousand and six", "50": "fifty"}
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower().replace("colour", "color").replace("grey", "gray").replace("catalogues", "catalogs").replace("jewellery", "jewelry").replace("pyjamas", "pajamas"))
wt_tok, wt_time = [], []
for w, a, b in words:
    toks = NUM.get(norm(w), norm(w)).split() or [""]
    for k, t in enumerate(toks):
        wt_tok.append(t); wt_time.append((a + (b - a) * k / len(toks), a + (b - a) * (k + 1) / len(toks)))
sc_tok = [norm(w).replace("seventyfour", "seventyfour") for p in phr for w in p]
sc_tok = [t.replace("everyone", "every") for t in sc_tok]
times = [None] * len(sc_tok)
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sc_tok, wt_tok, autojunk=False).get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1): times[i1 + k] = wt_time[j1 + k]
    elif j2 > j1:
        a, b = wt_time[j1][0], wt_time[j2 - 1][1]
        for k in range(i2 - i1): times[i1 + k] = (a + (b - a) * k / (i2 - i1), a + (b - a) * (k + 1) / (i2 - i1))
for k in range(len(times)):  # fill gaps by interpolation
    if times[k] is None:
        prev = times[k - 1][1] if k else 0.0
        nxt = next((times[j][0] for j in range(k + 1, len(times)) if times[j]), prev + 0.3)
        times[k] = (prev, max(prev, nxt))
print("matched", sum(1 for t in times if t), "/", len(times))
def wt(name, nth=0):
    hits = [k for k, t in enumerate(sc_tok) if t == name]; return times[hits[nth]][0] + LEAD
VO_END = words[-1][2] + LEAD
T_OUT = VO_END + (1.3 if P < 6 else 1.6); D = T_OUT + (2.4 if P < 6 else 2.8)
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
    seg = times[i:i + len(p)]; i += len(p); h = len(p) // 2 + 1
    groups = [(p, seg)] if len(" ".join(p)) <= 40 or not cues else [(p[:h], seg[:h]), (p[h:], seg[h:])]
    for g, s in groups: cues.append([g, s[0][0] + LEAD, s[-1][1] + LEAD])
ev = []
for n, (g, a, b) in enumerate(cues):
    last = n == len(cues) - 1
    end = min(max(b + 0.45, a + 0.9), cues[n + 1][1] - 0.09) if not last else T_OUT - 0.05
    tag = "{\\fad(200,300)\\fs96\\c&H7FD0FF&}" if last else "{\\fad(110,90)}"
    ev.append(f"Dialogue: 0,{ts(max(a - 0.05, 0))},{ts(end)},Cap,,0,0,0,,{tag}" + "\\N".join(split_lines(g, 19 if last else 21)))
tail = "to be continued…" if P < 6 else "the end"
ev.append(f"Dialogue: 0,{ts(T_OUT + 0.5)},{ts(D - 0.15)},Cap,,0,0,0,,{{\\fad(300,300)\\fs52\\c&H9CCBF2&}}{tail}")
open(f"p{P}.ass", "w").write(f"""[Script Info]
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
# ---------- per-part looks ----------
def ramp(a, b, lo=0.0, hi=1.0):  # 0 before a, rises to hi at b
    return f"({lo}+({hi}-{lo})*min(1,max(0,(T-{a:.2f})/{max(b - a, 0.05):.2f})))"
# GRADE: weight of an alternate grade "B" blended over the normal picture. DIM: fraction of darkness before the cut.
if P == 4:
    a, b, c = wt("photographs"), wt("never"), wt("back")
    GRADE = f"if(lt(T,{a:.2f}),0,if(lt(T,{c:.2f}),0.85*min(1,(T-{a:.2f})/1.5),max(0,0.85-(T-{c:.2f})/2)))"
    ALT = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0,eq=contrast=0.92:brightness=-0.04"
    T_DIM = wt("and", 3) if len([t for t in sc_tok if t == "and"]) > 3 else VO_END - 4
    x0, x1, ss, ms = 1700, 2150, 30, 400
elif P == 5:
    a = wt("glass") - 0.6
    GRADE = f"if(lt(T,{a:.2f}),0,min(0.9,(T-{a:.2f})/2.6*0.9))"
    ALT = "gblur=sigma=2.5,colorchannelmixer=.55:.25:.25:0:.25:.6:.25:0:.3:.3:.75:0,eq=brightness=0.22:saturation=0.35"
    T_DIM = VO_END + 0.2
    x0, x1, ss, ms = 160, 1250, 90, 520
else:
    a = wt("spring")
    GRADE = f"if(lt(T,{a - 0.5:.2f}),0.8,max(0,0.8-(T-{a - 0.5:.2f})/1.6))"
    ALT = "colorchannelmixer=.6:.2:.3:0:.2:.65:.3:0:.25:.3:.9:0,eq=brightness=0.06:saturation=0.45"
    T_DIM = VO_END + 0.4
    x0, x1, ss, ms = 160, 1250, 20, 30
T_CUT = wt("someone") - 0.15 if P == 6 else None
if T_CUT:
    pan = f"if(lt(t,{T_CUT:.2f}),{x0}+({x1}-{x0})*(1-cos(PI*min(t/{T_CUT:.2f},1)))/2,2150)"
else:
    pan = f"{x0}+({x1}-{x0})*(1-cos(PI*min(t/{T_OUT:.2f},1)))/2"
# ---------- subtle sound effects ----------
rng = np.random.default_rng(20 + P); N = int(D * SR); sfx = np.zeros(N, np.float32)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x).astype(np.float32)
def put(x, t, gain=1.0):
    a = int(t * SR); b = min(N, a + len(x)); sfx[a:b] += gain * x[:b - a]
def tt(d): return np.arange(int(d * SR)) / SR
def swipe(d, lo=1400, hi=5200):
    t = tt(d); return bp(rng.standard_normal(len(t)), lo, hi) * np.hanning(len(t)) ** 1.5
def paper(t0):
    for k, d in enumerate((0.4, 0.3)): put(swipe(d, 2200, 8000), t0 + 0.45 * k, 0.05)
if P == 4:
    paper(wt("photographs") + 0.4); paper(wt("drawer") + 0.5)
elif P == 5:
    paper(max(0.3, wt("letter") - 0.2)); paper(wt("fold") + 0.1)
else:
    for k in range(6): put(swipe(0.12, 1800, 7000), wt("followed") + 0.35 * k, 0.06)   # steps on frost
    t = tt(1.4); put((swipe(1.4, 300, 1400) * 0.6).astype(np.float32), wt("ajar") - 0.6, 0.06)  # the shed door
t = tt(2.4); boom = np.sin(2*np.pi*np.cumsum(38 + 40*np.exp(-t/0.12))/SR) * np.exp(-t/0.55) + 0.4*lp(rng.standard_normal(len(t)), 160) * np.exp(-t/0.25)
if P < 6: put(boom.astype(np.float32), T_OUT, 0.3)
sf.write(f"sfx{P}.wav", np.clip(sfx, -0.95, 0.95), SR)
# ---------- render ----------
end_fade = f"fade=t=out:st={T_OUT:.2f}:d=0.04" if P < 6 else f"fade=t=out:st={T_OUT:.2f}:d=1.2"
rain = f"if(lt(t,{wt('rain') if P == 5 else 1e9:.2f}),1.6,max(0.5,1.6-(t-{wt('rain') if P == 5 else 1e9:.2f})*0.6))"
duck = f"if(lt(t,{T_OUT - 4:.2f}),0.8,if(lt(t,{T_OUT:.2f}),0.8-(t-{T_OUT - 4:.2f})*0.1,{'0' if P < 6 else '0.4'}))"
fc = (f"[0:v]fps=30,scale=1138:640:flags=area,eq=saturation=1.2:contrast=1.06,format=gbrp,split[n0][c0];"
      f"[c0]{ALT},format=gbrp[alt];[n0][alt]blend=all_expr='A*(1-({GRADE}))+B*({GRADE})',{end_fade},format=gbrp,"
      f"scale=3414:1920:flags=neighbor,crop=1080:1920:x='{pan}':y=0,format=gbrp,split=3[s][b0][g0];"
      f"[b0]gblur=sigma=7[bl];[1:v]format=gray,scale=1080:1920[m];[s][bl][m]maskedmerge[tsd];"
      f"[g0]curves=all='0/0 0.55/0 1/1',gblur=sigma=22[glow];[tsd][glow]blend=all_mode=screen:all_opacity=0.5[lit];"
      f"[lit][2:v]overlay=format=auto,format=yuv420p,ass=p{P}.ass:fontsdir=fonts,fade=in:st=0:d=0.2,fade=out:st={D-0.5:.2f}:d=0.5[v];"
      f"[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume='{rain}':eval=frame[amb];[4:a]aresample=48000,volume='{duck}':eval=frame[mu];"
      f"[5:a]aresample=48000,highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160,volume=3.1,adelay={int(LEAD*1000)}:all=1,pan=stereo|c0=c0|c1=c0[vo];"
      f"[6:a]volume=0.3,pan=stereo|c0=c0|c1=c0[fx];"
      f"[amb][mu][vo][fx]amix=inputs=4:normalize=0,alimiter=limit=0.89:level=disabled,afade=in:st=0:d=0.25,afade=out:st={D-1.2:.2f}:d=1.2[a]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(ss), "-i", f"{KIT}/loop.mp4", "-loop", "1", "-i", "ts.png", "-loop", "1", "-i", "ov.png",
    "-ss", str(ss), "-i", f"{KIT}/ambience.flac", "-ss", str(ms), "-i", f"{KIT}/music.flac", "-i", f"el/vo{P}.mp3", "-i", f"sfx{P}.wav",
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{D:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", f"out/autumn-rain-part-{P}.mp4"], check=True)
print("built", P, round(D, 2))
