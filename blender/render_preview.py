"""
render_preview.py — render the neural wave as an animated GIF + MP4
using matplotlib (no GPU / no Blender needed).  Gives an inline preview
of exactly the mesh that was baked into the GLB / Alembic.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter

GRID, FRAMES, DECAY = 80, 60, 0.25
lin = np.linspace(-5, 5, GRID)
X, Y = np.meshgrid(lin, lin)
R = np.sqrt(X**2 + Y**2)

def wave_z(t):
    z  = np.sin(2*np.pi*R - t*2.0) * np.exp(-DECAY*R)
    z += np.sin(4*np.pi*R - t*3.5 + 1.2) * np.exp(-0.4*R) * 0.30
    z += np.sin(8*np.pi*R - t*5.0 + 2.4) * np.exp(-0.7*R) * 0.08
    return z

# Cyan→purple glassy colormap
from matplotlib.colors import LinearSegmentedColormap
glass = LinearSegmentedColormap.from_list(
    "glass", ["#02030f", "#003a6b", "#0a8bd6", "#39e6ff", "#aef0ff",
              "#7a3cff", "#bf6cff"])

fig = plt.figure(figsize=(8, 8), facecolor="#000008")
ax  = fig.add_subplot(111, projection="3d")
ax.set_facecolor("#000008")
ax.set_axis_off()

def draw(frame):
    ax.clear(); ax.set_axis_off()
    t = (frame / FRAMES) * 2 * np.pi
    Z = wave_z(t)
    ax.plot_surface(X, Y, Z, cmap=glass, vmin=-1.1, vmax=1.1,
                    rcount=GRID, ccount=GRID, antialiased=True,
                    linewidth=0, edgecolor="none", shade=True)
    ax.set_zlim(-2.2, 2.2)
    ax.view_init(elev=38, azim=frame * 6)  # slow orbit
    ax.set_box_aspect((1, 1, 0.45))
    return []

print("Rendering 60-frame animated preview …")
anim = FuncAnimation(fig, draw, frames=FRAMES, blit=False)
anim.save("neural_wave_preview.gif", writer=PillowWriter(fps=24), dpi=70)
print("✓ neural_wave_preview.gif")

# Also a hero still (frame 15)
draw(15)
fig.savefig("neural_wave_hero.png", dpi=120, facecolor="#000008",
            bbox_inches="tight")
print("✓ neural_wave_hero.png")
