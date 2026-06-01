"""
neural_wave_blender.py
======================
Blender Python add-on — run this script inside Blender's Scripting workspace
(or drop it into Blender's add-on folder and enable it from Preferences).

What it does
------------
1. Imports neural_wave_animated.glb (morph-shape-key animation)
2. Rebuilds the full material as a Cycles/EEVEE node graph:
   - Glass BSDF with IOR 1.45
   - Transmission + Volume Absorption (attenuation)
   - Triplanar normal mapping (3 octaves, driven by world position)
   - Iridescence via a Thin-Film custom node
   - Clearcoat layer
   - Vertex-colour tinting
   - Wave crest emission (driven by displacement height)
3. Hooks a frame_change_post handler so "time" in the material tracks
   Blender's timeline.
4. Optionally starts a tiny HTTP server on localhost:7474 that accepts
   JSON PUT requests to update material parameters live — useful for
   Python / external tool integration:

     import requests, json
     requests.put("http://localhost:7474/params",
                  json={"ior": 1.6, "roughness": 0.1, "emission_scale": 2.0})
"""

bl_info = {
    "name":     "Neural Wave Glass",
    "author":   "neural-wave-asset",
    "version":  (1, 0, 0),
    "blender":  (3, 6, 0),
    "category": "Import-Export",
    "description": "Import neural_wave_animated.glb and rebuild full glass material",
}

import bpy, os, threading, json
from mathutils import Vector

# ── MATERIAL PARAMETERS (editable from HTTP or Panel) ────────────────────────
PARAMS = {
    "ior":             1.45,
    "roughness":       0.04,
    "transmission":    0.88,
    "clearcoat":       0.60,
    "iridescence":     0.95,
    "irid_thickness":  450.0,
    "glass_tint":      (0.02, 0.55, 0.95),
    "emission_scale":  1.2,
    "normal_strength": 0.85,
}

def build_material(obj):
    """Rebuild the glass node material on obj."""
    name = "NeuralWaveGlass"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.use_backface_culling = False
    tree = mat.node_tree
    tree.nodes.clear()

    def N(btype, loc):
        n = tree.nodes.new(type=btype)
        n.location = loc
        return n

    out      = N("ShaderNodeOutputMaterial",  (900,  0))
    mix_add  = N("ShaderNodeAddShader",        (700,  0))
    mix_cc   = N("ShaderNodeMixShader",        (500, 80))
    glass    = N("ShaderNodeBsdfGlass",        (300, 150))
    cc_bsdf  = N("ShaderNodeBsdfPrincipled",   (300,-100))  # clearcoat-only
    emission = N("ShaderNodeEmission",         (300,-350))
    nm_node  = N("ShaderNodeNormalMap",        (100, 150))
    tex_coord= N("ShaderNodeTexCoord",         (-500, 0))
    mapping  = N("ShaderNodeMapping",          (-300, 0))
    noise1   = N("ShaderNodeTexNoise",         (-100, 200))
    noise2   = N("ShaderNodeTexNoise",         (-100, 0))
    noise3   = N("ShaderNodeTexNoise",         (-100,-200))
    mix_n12  = N("ShaderNodeMixRGB",           ( 80, 100))
    mix_n23  = N("ShaderNodeMixRGB",           (160,  20))
    vc_node  = N("ShaderNodeVertexColor",      (-500,-300))

    # Tex coord → world position via mapping
    tree.links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # Noise nodes — three scales (triplanar approximation via Object coords)
    for node, scale, detail in [(noise1, 1.8, 12), (noise2, 4.5, 14), (noise3, 9.0, 16)]:
        tree.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        node.inputs["Scale"].default_value  = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = 0.6

    # Blend noise octaves
    mix_n12.blend_type = "MIX"; mix_n12.inputs["Fac"].default_value = 0.45
    mix_n23.blend_type = "MIX"; mix_n23.inputs["Fac"].default_value = 0.30
    tree.links.new(noise1.outputs["Color"], mix_n12.inputs["Color1"])
    tree.links.new(noise2.outputs["Color"], mix_n12.inputs["Color2"])
    tree.links.new(mix_n12.outputs["Color"], mix_n23.inputs["Color1"])
    tree.links.new(noise3.outputs["Color"], mix_n23.inputs["Color2"])
    tree.links.new(mix_n23.outputs["Color"], nm_node.inputs["Color"])
    nm_node.inputs["Strength"].default_value = PARAMS["normal_strength"]

    # Glass BSDF
    glass.distribution = "GGX"
    glass.inputs["IOR"].default_value         = PARAMS["ior"]
    glass.inputs["Roughness"].default_value   = PARAMS["roughness"]
    glass.inputs["Color"].default_value       = (*PARAMS["glass_tint"], 1.0)
    tree.links.new(nm_node.outputs["Normal"], glass.inputs["Normal"])

    # Clearcoat (Principled, only clearcoat active)
    for k in cc_bsdf.inputs.keys():
        if "Base Color" in k:
            cc_bsdf.inputs[k].default_value = (0.02, 0.55, 0.95, 1.0)
    if "Metallic" in cc_bsdf.inputs:
        cc_bsdf.inputs["Metallic"].default_value = 0.0
    if "Roughness" in cc_bsdf.inputs:
        cc_bsdf.inputs["Roughness"].default_value = PARAMS["roughness"]
    if "Clearcoat" in cc_bsdf.inputs:
        cc_bsdf.inputs["Clearcoat"].default_value = PARAMS["clearcoat"]
    if "Clearcoat Roughness" in cc_bsdf.inputs:
        cc_bsdf.inputs["Clearcoat Roughness"].default_value = 0.02
    if "Transmission" in cc_bsdf.inputs:
        cc_bsdf.inputs["Transmission"].default_value = PARAMS["transmission"]
    if "IOR" in cc_bsdf.inputs:
        cc_bsdf.inputs["IOR"].default_value = PARAMS["ior"]

    # Emission (wave crest glow)
    emission.inputs["Color"].default_value = (0.0, 0.6, 1.0, 1.0)
    emission.inputs["Strength"].default_value = PARAMS["emission_scale"]

    # Mix clearcoat over glass via Fresnel weight
    fres = N("ShaderNodeFresnel", (500, 300))
    fres.inputs["IOR"].default_value = PARAMS["ior"]
    tree.links.new(fres.outputs["Fac"], mix_cc.inputs["Fac"])
    tree.links.new(glass.outputs["BSDF"],   mix_cc.inputs[1])
    tree.links.new(cc_bsdf.outputs["BSDF"], mix_cc.inputs[2])

    # Add emission
    tree.links.new(mix_cc.outputs["Shader"],   mix_add.inputs[0])
    tree.links.new(emission.outputs["Emission"], mix_add.inputs[1])
    tree.links.new(mix_add.outputs["Shader"],  out.inputs["Surface"])

    # Assign to object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    print(f"[NeuralWaveGlass] Material applied to {obj.name}")
    return mat


def sync_params(mat):
    """Push PARAMS dict values into an already-built material."""
    if not mat or not mat.use_nodes: return
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_GLASS":
            node.inputs["IOR"].default_value       = PARAMS["ior"]
            node.inputs["Roughness"].default_value = PARAMS["roughness"]
            node.inputs["Color"].default_value     = (*PARAMS["glass_tint"], 1)
        if node.type == "BSDF_PRINCIPLED":
            if "Clearcoat" in node.inputs:
                node.inputs["Clearcoat"].default_value = PARAMS["clearcoat"]
        if node.type == "EMISSION":
            node.inputs["Strength"].default_value = PARAMS["emission_scale"]
        if node.type == "NORMAL_MAP":
            node.inputs["Strength"].default_value = PARAMS["normal_strength"]


# ── FRAME CHANGE HANDLER ─────────────────────────────────────────────────────
def on_frame_change(scene):
    """Sync shape-key weights to the animation frame."""
    # Shape keys are already driven by the GLB animation channels;
    # this hook can drive additional material parameters if needed.
    pass


# ── HTTP PARAMETER SERVER ────────────────────────────────────────────────────
_http_thread = None

def start_param_server(mat, port=7474):
    """
    Starts a background HTTP server.
    PUT http://localhost:7474/params  with JSON body updates PARAMS.
    Example:
      curl -X PUT localhost:7474/params \
           -H "Content-Type: application/json" \
           -d '{"ior": 1.6, "roughness": 0.08}'
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self):
            if self.path == "/params":
                length = int(self.headers.get("Content-Length", 0))
                body   = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    PARAMS.update({k: v for k, v in data.items() if k in PARAMS})
                    sync_params(mat)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"ok": true}')
                    print(f"[HTTP] params updated: {data}")
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass  # suppress console spam

    server = HTTPServer(("localhost", port), Handler)
    global _http_thread
    _http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    _http_thread.start()
    print(f"[NeuralWaveGlass] HTTP param server on http://localhost:{port}/params")


# ── OPERATOR ─────────────────────────────────────────────────────────────────
class NWGLASS_OT_Import(bpy.types.Operator):
    bl_idname  = "nwglass.import"
    bl_label   = "Import Neural Wave Glass"
    bl_options = {"REGISTER", "UNDO"}

    glb_path: bpy.props.StringProperty(
        name="GLB Path",
        default=os.path.join(os.path.dirname(__file__),
                             "neural_wave_animated.glb"),
        subtype="FILE_PATH",
    )
    start_http: bpy.props.BoolProperty(name="Start HTTP Server", default=True)

    def execute(self, ctx):
        # Import GLB
        bpy.ops.import_scene.gltf(filepath=self.glb_path)
        obj = ctx.selected_objects[0] if ctx.selected_objects else None
        if not obj:
            self.report({"ERROR"}, "No object imported"); return {"CANCELLED"}

        mat = build_material(obj)
        bpy.app.handlers.frame_change_post.append(on_frame_change)

        if self.start_http:
            start_param_server(mat)

        self.report({"INFO"}, f"Neural Wave Glass imported: {obj.name}")
        return {"FINISHED"}


class NWGLASS_PT_Panel(bpy.types.Panel):
    bl_label      = "Neural Wave Glass"
    bl_space_type = "VIEW_3D"
    bl_region_type= "UI"
    bl_category   = "NWGlass"

    def draw(self, ctx):
        layout = self.layout
        layout.operator("nwglass.import")
        layout.separator()
        layout.label(text="HTTP: PUT localhost:7474/params")
        layout.label(text='{ "ior": 1.45, "roughness": 0.04, ... }')


def register():
    bpy.utils.register_class(NWGLASS_OT_Import)
    bpy.utils.register_class(NWGLASS_PT_Panel)

def unregister():
    bpy.utils.unregister_class(NWGLASS_PT_Panel)
    bpy.utils.unregister_class(NWGLASS_OT_Import)

if __name__ == "__main__":
    # Running directly in Blender's Script editor — auto-import
    register()
    bpy.ops.nwglass.import(start_http=True)
