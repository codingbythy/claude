import json, subprocess, sys
import numpy as np
from PIL import Image
from story import PARTS
W, H = 1080, 1920
KIT = "src/glasshouse/video-kit"
# tilt-shift mask (white = blurred) and a vignette / centre-dim overlay
y = np.linspace(0, 1, H)[:, None]
ts = np.clip((np.abs(y - 0.56) - 0.27) / 0.2, 0, 1) ** 1.3
Image.fromarray((np.repeat(ts, W, 1) * 255).astype(np.uint8)).save("ts.png")
x = np.linspace(-1, 1, W)[None, :]; yy = np.linspace(-1, 1, H)[:, None]
vig = np.clip((np.sqrt((x*0.9)**2 + (yy*0.95)**2) - 0.55) / 0.75, 0, 1) ** 1.6 * 0.62
band = np.exp(-((yy + 0.0) / 0.26) ** 2) * 0.30 * np.ones_like(x)
a = np.clip(np.maximum(vig, band), 0, 1)
ov = np.zeros((H, W, 4), np.uint8); ov[..., 0] = 8; ov[..., 1] = 10; ov[..., 2] = 22; ov[..., 3] = (a * 255).astype(np.uint8)
Image.fromarray(ov).save("ov.png")

def ts_fmt(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
def chunks(text, maxc=40):
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > maxc: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    out.append(cur)
    if len(out) > 1 and len(out[-1]) < 12: out[-2:] = [out[-2] + " " + out[-1]]
    return out
def wrap(c, maxc=21):
    if len(c) <= maxc: return c
    ws = c.split(); best = None
    for i in range(1, len(ws)):
        a, b = " ".join(ws[:i]), " ".join(ws[i:])
        sc = abs(len(a) - len(b))
        if best is None or sc < best[0]: best = (sc, a + r"\N" + b)
    return best[1]
PANS = [(2080, 2215), (140, 1320), (1480, 2215)]
STARTS = [4, 62, 118]
for pi, (label, title, lines) in enumerate(PARTS, 1):
    if len(sys.argv) > 1 and str(pi) not in sys.argv[1:]: continue
    meta = json.load(open(f"cues{pi}.json")); D = meta["dur"]
    ev = [f"Dialogue: 0,{ts_fmt(0.15)},{ts_fmt(1.5)},Title,,0,0,0,,{{\\fad(250,250)}}{{\\fs44\\c&H9CCBF2&}}{label.upper()}\\N{{\\fs92\\c&HFFFFFF&}}{title}"]
    for c in meta["cues"]:
        ch = chunks(c["text"]); tot = sum(len(k) for k in ch); t = c["start"]
        for k in ch:
            d = (c["end"] - c["start"]) * len(k) / tot
            ev.append(f"Dialogue: 0,{ts_fmt(t)},{ts_fmt(t + d + 0.12)},Cap,,0,0,0,,{{\\fad(120,100)}}{wrap(k)}"); t += d
    tail = "to be continued…" if pi < 3 else "the end"
    ev.append(f"Dialogue: 0,{ts_fmt(D - 2.2)},{ts_fmt(D - 0.2)},Title,,0,0,0,,{{\\fad(300,300)}}{{\\fs56\\c&H9CCBF2&}}{tail}")
    open(f"p{pi}.ass", "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Pixelify Sans SemiBold,90,&H00F4FAFF,&H00FFFFFF,&H00160C0A,&H96000000,0,0,0,0,100,100,1,0,1,7,5,5,70,70,0,1
Style: Title,Pixelify Sans SemiBold,92,&H00FFFFFF,&H00FFFFFF,&H00160C0A,&H96000000,0,0,0,0,100,100,2,0,1,7,5,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
    x0, x1 = PANS[pi - 1]; ss = STARTS[pi - 1]
    pan = f"{x0}+({x1}-{x0})*(1-cos(PI*min(t/{D:.2f},1)))/2"
    fc = (f"[0:v]fps=30,scale=1138:640:flags=area,eq=saturation=1.2:contrast=1.06,scale=3414:1920:flags=neighbor,"
          f"crop=1080:1920:x='{pan}':y=0,format=gbrp,split=3[s][b0][g0];"
          f"[b0]gblur=sigma=7[bl];[1:v]format=gray,scale=1080:1920[m];[s][bl][m]maskedmerge[tsd];"
          f"[g0]curves=all='0/0 0.55/0 1/1',gblur=sigma=22[glow];[tsd][glow]blend=all_mode=screen:all_opacity=0.5[lit];"
          f"[lit][2:v]overlay=format=auto,format=yuv420p,ass=p{pi}.ass:fontsdir=fonts,fade=in:st=0:d=0.6,fade=out:st={D-0.7:.2f}:d=0.7[v];"
          f"[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.6[amb];[4:a]aresample=48000,volume=0.8[mu];"
          f"[5:a]aresample=48000,highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160,volume=2.4,pan=stereo|c0=c0|c1=c0[vo];"
          f"[amb][mu][vo]amix=inputs=3:normalize=0,alimiter=limit=0.89:level=disabled,afade=in:st=0:d=0.8,afade=out:st={D-1.6:.2f}:d=1.6[a]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(ss), "-i", f"{KIT}/loop.mp4", "-loop", "1", "-i", "ts.png", "-loop", "1", "-i", "ov.png",
           "-ss", str(ss), "-i", f"{KIT}/ambience.flac", "-ss", str(8 + 0 * pi), "-i", f"{KIT}/music.flac", "-i", f"vo{pi}.wav",
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{D:.2f}", "-r", "30",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           f"out/autumn-rain-part-{pi}.mp4"]
    subprocess.run(cmd, check=True); print("built", pi, round(D, 1))
