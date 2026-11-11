import numpy as np, wave
SR=24000; DUR=720; N=SR*DUR; rng=np.random.default_rng(7)
L=np.zeros(N); Rr=np.zeros(N)
def hz(m): return 440*2**((m-69)/12)
def add(sig,start,pan):
    idx=(start+np.arange(len(sig)))%N
    np.add.at(L,idx,sig*np.cos(pan*np.pi/2)); np.add.at(Rr,idx,sig*np.sin(pan*np.pi/2))
def piano(m,vel,dur=7.0):
    f=hz(m); t=np.arange(int(dur*SR))/SR; s=np.zeros_like(t)
    for n in range(1,7):
        fn=n*f*np.sqrt(1+0.0004*n*n)
        if fn>SR*0.45: break
        tau=(2.6/n**0.8)*(261.6/f)**0.35
        s+=np.sin(2*np.pi*fn*t+rng.uniform(0,6.28))*np.exp(-t/tau)/n**1.9
    a=int(0.018*SR); s[:a]*=0.5-0.5*np.cos(np.pi*np.arange(a)/a)
    r=int(0.5*SR); s[-r:]*=np.linspace(1,0,r)
    return s*vel
def pad(m,dur,amp):
    f=hz(m); t=np.arange(int(dur*SR))/SR
    s=np.sin(2*np.pi*f*1.0016*t)+np.sin(2*np.pi*f*0.9984*t+1.3)+0.22*np.sin(2*np.pi*2*f*t+0.5)
    e=np.sin(np.pi*t/dur)**1.5
    return s*e*amp*(1+0.12*np.sin(2*np.pi*0.11*t+rng.uniform(0,6.28)))
CH=12.0
prog=[[50,57,62,66],[47,54,57,62],[43,50,59,66],[45,52,57,61],
      [50,57,62,66],[42,49,57,64],[43,50,59,62],[45,52,59,64]]
penta=[62,64,66,69,71,74,76,78,81]
nch=int(DUR/CH)
for c in range(nch):
    for i,m in enumerate(prog[c%len(prog)]):
        add(pad(m,CH*1.55,0.05), int((c*CH-CH*0.275)*SR)%N, 0.3+0.4*(i/3))
t=1.0; pos=4
while t<DUR-0.5:
    chord=set(x%12 for x in prog[int(t/CH)%len(prog)])
    for _ in range(6):
        cand=int(np.clip(pos+rng.integers(-2,3),0,len(penta)-1))
        if penta[cand]%12 in chord or rng.random()<0.3: pos=cand; break
    add(piano(penta[pos],rng.uniform(0.35,0.75)), int(t*SR), rng.uniform(0.25,0.75))
    if rng.random()<0.3:
        add(piano(prog[int(t/CH)%len(prog)][0]-0 ,rng.uniform(0.3,0.5)), int(t*SR), 0.5)
    if rng.random()<0.28:
        p2=int(np.clip(pos+rng.choice([-2,-1,1,2]),0,len(penta)-1)); add(piano(penta[p2],rng.uniform(0.25,0.5)), int((t+0.75)*SR), rng.uniform(0.25,0.75))
    t+=rng.choice([1.5,3,3,3,4.5,4.5,6])
# circular reverb
def rev(x,seed):
    r=np.random.default_rng(seed); n=int(3.8*SR); t=np.arange(n)/SR
    ir=r.standard_normal(n)*np.exp(-t/0.9); ir=np.convolve(ir,np.ones(6)/6,'same'); ir[:int(0.012*SR)]=0
    ir/=np.sqrt((ir**2).sum())
    pad_ir=np.zeros(N); pad_ir[:n]=ir
    return np.fft.irfft(np.fft.rfft(x)*np.fft.rfft(pad_ir),N)
L=L+0.9*rev(L,1); Rr=Rr+0.9*rev(Rr,2)
st=np.stack([L,Rr],1); st*=0.04/np.sqrt((st**2).mean())
print('peak',abs(st).max(),'rms',np.sqrt((st**2).mean()))
st=np.clip(st,-0.98,0.98)
w=wave.open('music.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype('<i2').tobytes()); w.close()
# rotate ambience by 10 s
a=wave.open('../vid/loop.wav'); d=np.frombuffer(a.readframes(a.getnframes()),'<i2').reshape(-1,2); d=np.roll(d,-10*48000,axis=0)
w=wave.open('amb_rot.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(d.tobytes()); w.close()
