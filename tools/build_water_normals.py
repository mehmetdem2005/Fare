#!/usr/bin/env python3
"""Make a seamless original multi-directional water slope/caustic tile.
No borrowed texture, no copyright issue; generated 256px linear RGBA PNG.
R/G signed XZ slope; B positive Z for diagnostics; A ripple interference mask.
"""
from pathlib import Path
import numpy as np
from PIL import Image

OUT=Path(__file__).resolve().parents[1]/"assets"/"water"/"wave_caustics_rgba.png"
N=256
xx,yy=np.meshgrid(np.arange(N,dtype=np.float32)/N,np.arange(N,dtype=np.float32)/N)
height=np.zeros((N,N),dtype=np.float32)
for kx,ky,amp,phase in [
 (3,5,0.41,0.11),(7,-4,0.32,2.13),(11,2,0.20,1.4),
 (-9,12,0.18,3.19),(2,16,0.13,4.51),(19,7,0.09,0.63),
 (13,-18,0.055,5.72),(22,-9,0.046,2.93)]:
    angle=2.0*np.pi*(kx*xx+ky*yy)+phase
    height+=amp*np.sin(angle)
dx=np.roll(height,-1,axis=1)-np.roll(height,1,axis=1)
dy=np.roll(height,-1,axis=0)-np.roll(height,1,axis=0)
# The encoded xy components express slope rather than tangent normal vector.
nx=np.clip(-dx*0.42,-0.46,0.46)
ny=np.clip(-dy*0.42,-0.46,0.46)
nz=np.sqrt(np.maximum(0.15,1.0-nx*nx-ny*ny))
interference=np.abs(height-0.08*np.roll(height,2,axis=0))
caustic=np.clip((np.sin(interference*5.2)+0.78*np.sin(height*11.1+0.3))*0.33+0.42,0.0,1.0)
rgba=np.empty((N,N,4),dtype=np.uint8)
rgba[:,:,0]=np.round((nx*0.5+0.5)*255).astype(np.uint8)
rgba[:,:,1]=np.round((ny*0.5+0.5)*255).astype(np.uint8)
rgba[:,:,2]=np.round(nz*255).astype(np.uint8)
rgba[:,:,3]=np.round(caustic*255).astype(np.uint8)
OUT.parent.mkdir(parents=True,exist_ok=True)
Image.fromarray(rgba,"RGBA").save(OUT,optimize=True)
print("WAVE_TILE_OK",OUT,OUT.stat().st_size,"bytes",
      "seam_height=",np.max(abs(height[:,0]-height[:,-1])))
