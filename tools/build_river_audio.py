#!/usr/bin/env python3
"""Create original looping river water sounds; deterministic, copyright-free.
Godot 4.7 Mobile: 22050 Hz mono PCM WAV (no network, no runtime synthesis).
"""
from pathlib import Path
import wave
import numpy as np

OUT=Path(__file__).resolve().parents[1]/"assets"/"audio"
RATE=22050
SECONDS=7
N=RATE*SECONDS
RNG=np.random.default_rng(49825)
OUT.mkdir(parents=True,exist_ok=True)

def smooth(x,width):
    width=int(width)
    cs=np.cumsum(np.r_[0.0,x])
    return np.pad((cs[width:]-cs[:-width])/width,(width//2,width-width//2-1),mode="wrap")[:len(x)]

def write(name,x):
    # Crossfade endpoints to make a seam-free loop.
    fade=RATE//4
    x=np.asarray(x,dtype=np.float64)
    a=np.linspace(0,1,fade)
    mix=x[:fade]*(1-a)+x[-fade:]*a
    x[:fade]=mix
    x[-fade:]=mix
    x=np.tanh(x*1.1)
    x/=max(1.0,np.max(np.abs(x))*1.08)
    samples=np.asarray(x*25000,dtype="<i2")
    path=OUT/name
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(samples.tobytes())
    print("RIVER_AUDIO_OK",name,path.stat().st_size)

t=np.arange(N,dtype=np.float64)/RATE
noise=RNG.normal(0,1,N)
noise2=RNG.normal(0,1,N)
base=0.82*smooth(noise,22)+0.24*smooth(noise2,3)
soft=np.sin(t*2*np.pi*0.45+1.3)*0.11
write("river_calm.wav",base*1.7+soft)
bubbles=smooth(RNG.normal(0,1,N),7)
bursts=0.64+0.22*np.sin(t*2*np.pi*1.9)+0.13*np.sin(t*2*np.pi*0.91)
write("river_rapids.wav",bursts*(0.50*noise+0.86*bubbles+0.20*base))
drops=np.zeros(N,dtype=np.float64)
for i in range(85):
    offset=int(RNG.integers(0,N-320))
    n=np.arange(320)
    hz=float(RNG.uniform(280,850))
    drops[offset:offset+320]+=(0.05*np.exp(-n/58.0)*np.sin(2*np.pi*hz*n/RATE))
write("river_drops.wav",drops+0.055*smooth(noise,40))
print("RIVER_AUDIO_ALL_OK")
