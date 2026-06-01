"""Render the deep-blue LED-volume voxel wave as an animated GIF."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

TILES, FRAMES, DECAY = 40, 60, 0.22
BASE_H, AMP_H = 0.1, 1.0
lin = np.linspace(-5, 5, TILES)
CX, CY = np.meshgrid(lin, lin)
R = np.sqrt(CX**2 + CY**2)

def heights(t):
    w  = np.sin(2*np.pi*R - t*2.0) * np.exp(-DECAY*R)
    w += np.sin(4*np.pi*R - t*3.5 + 1.2) * np.exp(-0.40*R) * 0.30
    w += np.sin(8*np.pi*R - t*5.0 + 2.4) * np.exp(-0.70*R) * 0.08
    return BASE_H + AMP_H * (w * 0.5 + 0.5)

xpos = CX.ravel(); ypos = CY.ravel()
dx = dy = (10.0 / TILES) * 0.82

fig = plt.figure(figsize=(8, 8), facecolor="#000308")
ax = fig.add_subplot(111, projection="3d")
ax.set_facecolor("#000308")

def draw(frame):
    ax.clear(); ax.set_axis_off()
    t = (frame / FRAMES) * 2 * np.pi
    h = heights(t).ravel()
    hn = (h - h.min()) / (np.ptp(h) + 1e-9)
    # deep blue → bright cyan LED by height
    colors = np.zeros((len(h), 4))
    colors[:, 0] = 0.0 + 0.2 * hn
    colors[:, 1] = 0.15 + 0.7 * hn
    colors[:, 2] = 0.55 + 0.45 * hn
    colors[:, 3] = 0.85
    ax.bar3d(xpos - dx/2, ypos - dy/2, np.zeros_like(h),
             dx, dy, h, color=colors, shade=True, edgecolor="none")
    ax.set_zlim(0, 1.3); ax.set_box_aspect((1, 1, 0.5))
    ax.view_init(elev=42, azim=frame * 6)
    return []

print("Rendering LED voxel wave preview …")
anim = FuncAnimation(fig, draw, frames=FRAMES, blit=False)
anim.save("voxel_wave_preview.gif", writer=PillowWriter(fps=24), dpi=68)
print("✓ voxel_wave_preview.gif")
draw(12)
fig.savefig("voxel_wave_hero.png", dpi=120, facecolor="#000308", bbox_inches="tight")
print("✓ voxel_wave_hero.png")
