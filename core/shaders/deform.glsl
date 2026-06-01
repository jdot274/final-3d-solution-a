// deform.glsl — shared height-field deformation (web three.js + reference for UE/MaterialX).
// Drivers: 0 softbody · 1 waves · 2 heightmap · 3 video. Edge-pinned so instances tile cleanly.
// Per-instance variation via aPhase (added to time) so an instanced volume shimmers, not marches in lockstep.

uniform float uTime, uAmp, uFreq, uSpeed, uSoft, uNoise, uSizeX, uSizeY;
uniform int   uDriver;
attribute float aPhase;   // per-instance time offset

float hsh(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
float n2(vec2 p){
  vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hsh(i),hsh(i+vec2(1,0)),f.x), mix(hsh(i+vec2(0,1)),hsh(i+vec2(1,1)),f.x), f.y);
}
float field(vec2 uv, float t){
  float edge = sin(3.14159*uv.x) * sin(3.14159*uv.y);        // pinned edges
  if (uDriver==1) return uAmp*( sin(uv.x*uFreq*2.0+t*2.0)*0.5 + sin((uv.x+uv.y)*uFreq-t*2.4)*0.5 );
  if (uDriver==2){ vec2 c=uv-0.5; float r=length(c)*8.0; return uAmp*edge*sin(r-t*4.0)*exp(-r*0.12); }
  if (uDriver==3) return uAmp*edge*0.25*( sin(uv.x*10.0+t)+sin(uv.y*10.0-t)+sin((uv.x+uv.y)*8.0+t) );
  // softbody (default): low-freq jelly + value noise
  float w1 = sin(uv.x*uFreq + t*2.0) * cos(uv.y*(uFreq*0.8) - t*1.3);
  float w2 = sin((uv.x+uv.y)*(uFreq*1.6) - t*2.4);
  float nz = (n2(uv*8.0 + t*0.6) - 0.5) * uNoise;
  return uAmp*(1.0+uSoft)*edge*( 0.6*w1 + 0.3*w2 + nz );
}
