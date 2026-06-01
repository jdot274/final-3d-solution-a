"""
build_textures.py — regenerate the missing material-layer textures from the math.
Outputs to assets/textures/: wave_heightmap.png, wave_normalmap.png, wave_flipbook.png (8x8).
Run: blender --background --python build_textures.py
"""
import bpy, os, math
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "assets", "textures"); os.makedirs(OUT, exist_ok=True)
R = 512

def save(name, rgba):
    img = bpy.data.images.new(name, rgba.shape[1], rgba.shape[0], alpha=True)
    img.pixels = rgba.reshape(-1).tolist()
    img.filepath_raw = os.path.join(OUT, name + ".png"); img.file_format = 'PNG'
    img.save(); print("[TEX]", name, rgba.shape)

def height_field():
    y, x = np.mgrid[0:R, 0:R] / R
    h = (np.sin(x*12 + 1.7) * np.cos(y*9 - 0.6)
         + 0.5*np.sin((x+y)*16) + 0.3*np.sin(np.hypot(x-0.5, y-0.5)*30))
    h = (h - h.min()) / (h.max() - h.min())
    return h

# heightmap
h = height_field()
rgba = np.zeros((R, R, 4), np.float32); rgba[...,0]=rgba[...,1]=rgba[...,2]=h; rgba[...,3]=1
save("wave_heightmap", rgba)

# normalmap (sobel of height)
gx = np.gradient(h, axis=1) * R/64.0
gy = np.gradient(h, axis=0) * R/64.0
nz = np.ones_like(h)
ln = np.sqrt(gx*gx + gy*gy + nz*nz)
nm = np.zeros((R, R, 4), np.float32)
nm[...,0] = (-gx/ln)*0.5+0.5; nm[...,1] = (-gy/ln)*0.5+0.5; nm[...,2] = (nz/ln)*0.5+0.5; nm[...,3]=1
save("wave_normalmap", nm)

# 8x8 LED flipbook (64 animated frames of a moving emissive grid)
G = 8; cell = R // G
fb = np.zeros((R, R, 4), np.float32); fb[...,3] = 1
yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32)
for f in range(G*G):
    cy, cx = (f // G) * cell, (f % G) * cell
    t = f / (G*G) * 6.2831853
    led = 16
    sub = np.zeros((cell, cell, 3), np.float32)
    lc = cell / led
    for j in range(led):
        for i in range(led):
            d = np.hypot(xx-(i+0.5)*lc, yy-(j+0.5)*lc) / (lc*0.5)
            dot = np.clip(1-d, 0, 1)**2
            amp = 0.5+0.5*math.sin(t + (i+j)*0.5)
            sub[...,0] += dot*amp*(0.2)
            sub[...,1] += dot*amp*(0.4)
            sub[...,2] += dot*amp
    fb[cy:cy+cell, cx:cx+cell, :3] = np.clip(sub, 0, 1)
save("wave_flipbook", fb)
print("[DONE]", OUT)
