"""
black hole raymarcher thing
based on a bunch of shadertoy examples I found + gravitational lensing approximation
(not real GR, just something that looks close enough)
"""
 
import pygame
import moderngl
import numpy as np
import math
import sys
import time
from dataclasses import dataclass
 
@dataclass
class Config:
    width: int = 1280
    height: int = 720
    fps: int = 60
    mouse_sens: float = 0.004
    zoom_speed: float = 0.5
 
CONFIG = Config()
 
VERTEX_SHADER = '''
#version 330 core
in vec2 in_position;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
'''
 
# fullscreen quad, all the actual work happens per-pixel below
FRAGMENT_SHADER = '''
#version 330 core
out vec4 fragColor;
 
uniform vec2 u_resolution;
uniform float u_time;
uniform vec3 u_cameraPos;
uniform vec3 u_cameraDir;
uniform vec3 u_star1_pos;
uniform vec3 u_star2_pos;
 
#define MAX_STEPS 250
#define MAX_DIST 50.0
#define EVENT_HORIZON 1.0
#define MASS 1.0
#define INNER_RADIUS 2.2
#define OUTER_RADIUS 5.5
 
// cheap hash for the starfield, nothing fancy
float hash(vec3 p) {
    return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
}
 
// stars sampled by direction so they stay fixed on the "sky" regardless of camera pos
vec3 starfield(vec3 dir) {
    vec3 p = dir * 200.0;
    vec3 cell = floor(p);
    float h = hash(cell);
    float star = step(0.985, h);
    vec3 base = vec3(0.08, 0.10, 0.18);
    return base + vec3(star) * (0.6 + 0.4 * hash(cell + 7.0));
}
 
void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
 
    vec3 ro = u_cameraPos;
    vec3 forward = normalize(u_cameraDir);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), forward));
    vec3 up = cross(forward, right);
    vec3 rd = normalize(forward + uv.x * right + uv.y * up);
 
    vec3 color = vec3(0.08, 0.10, 0.18);
    bool hit_something = false;
 
    float dt = 0.05;
    float totalDist = 0.0;
    bool is_engulfed = false;
 
    for (int i = 0; i < MAX_STEPS; i++) {
        float r = length(ro);
 
        if (r < EVENT_HORIZON) {
            is_engulfed = true;
            break;
        }
 
        // proper-ish photon deflection: conserve angular momentum h = r x v,
        // then bend rd toward the center scaled by h^2 / r^5.
        // this is the formula that actually gives you a photon sphere / ring
        // instead of the old 1/r^3 version which did basically nothing until
        // the ray was already about to fall in
        vec3 h = cross(ro, rd);
        float h2 = dot(h, h);
        vec3 accel = -1.5 * MASS * h2 * ro / (r * r * r * r * r);
        rd = normalize(rd + accel * dt);
 
        // did we cross the disk plane this step?
        // (guard rd.y away from zero, or a perfectly horizontal ray gives -0/0 -> NaN)
        float safe_rdy = (abs(rd.y) < 1e-5) ? 1e-5 : rd.y;
        float next_y = ro.y + rd.y * dt;
        if (ro.y * next_y < 0.0) {
            float t = -ro.y / safe_rdy;
            vec3 hit = ro + rd * t;
            float hit_r = length(hit.xz);
 
            if (hit_r > INNER_RADIUS && hit_r < OUTER_RADIUS) {
                color = mix(vec3(1.0, 0.9, 0.2), vec3(0.85, 0.15, 0.05), (hit_r - INNER_RADIUS) / (OUTER_RADIUS - INNER_RADIUS));
                hit_something = true;
                break;
            }
        }
 
        if (length(ro - u_star1_pos) < 0.6) {
            color = vec3(0.9, 0.05, 0.05);
            hit_something = true;
            break;
        }
        if (length(ro - u_star2_pos) < 0.4) {
            color = vec3(1.0, 0.6, 0.1);
            hit_something = true;
            break;
        }
 
        // funnel grid, purely decorative, no physical meaning
        float current_gh = -2.5 / (r + 0.5) - 2.0;
        float next_r = length(ro + rd * dt);
        float next_gh = -2.5 / (next_r + 0.5) - 2.0;
        float f1 = ro.y - current_gh;
        float f2 = next_y - next_gh;
 
        if (f1 * f2 <= 0.0) {
            float fraction = f1 / (f1 - f2);
            vec3 hit = ro + rd * dt * fraction;
            vec2 grid_uv = hit.xz * 1.5;
            float line_w = 0.06;
 
            if (fract(grid_uv.x) < line_w || fract(grid_uv.y) < line_w) {
                color = vec3(0.8, 0.35, 0.6);
                hit_something = true;
                break;
            }
        }
 
        ro += rd * dt;
        totalDist += dt;
 
        // bigger steps far away, otherwise this crawls
        dt = max(0.015, r * 0.035);
 
        if (totalDist > MAX_DIST) break;
    }
 
    if (is_engulfed) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    } else if (!hit_something) {
        // ray escaped without hitting anything - sample the sky using its
        // FINAL bent direction, this is what actually shows the lensing
        fragColor = vec4(starfield(rd), 1.0);
    } else {
        fragColor = vec4(color, 1.0);
    }
}
'''
 
 
class OrbitalCamera:
    def __init__(self, radius=12.0):
        self.radius = radius
        self.angle_x = 0.6
        self.angle_y = 0.4
 
        self.target_radius = radius
        self.target_angle_x = self.angle_x
        self.target_angle_y = self.angle_y
 
    def add_orbit(self, dx, dy):
        self.target_angle_x -= dx * CONFIG.mouse_sens
        self.target_angle_y += dy * CONFIG.mouse_sens
 
        # stop it flipping over at the poles
        limit = math.pi / 2.1
        self.target_angle_y = max(-limit, min(limit, self.target_angle_y))
 
    def add_zoom(self, direction):
        self.target_radius += direction * CONFIG.zoom_speed
        self.target_radius = max(4.0, min(40.0, self.target_radius))
 
    def update(self):
        # simple exponential smoothing, good enough
        self.radius += (self.target_radius - self.radius) * 0.15
        self.angle_x += (self.target_angle_x - self.angle_x) * 0.15
        self.angle_y += (self.target_angle_y - self.angle_y) * 0.15
 
    @property
    def position(self):
        return np.array([
            self.radius * math.cos(self.angle_y) * math.sin(self.angle_x),
            self.radius * math.sin(self.angle_y),
            self.radius * math.cos(self.angle_y) * math.cos(self.angle_x)
        ], dtype='f4')
 
    @property
    def direction(self):
        pos = self.position
        return -pos / np.linalg.norm(pos)
 
 
class Renderer:
    def __init__(self):
        print("[init] creating GL context...", flush=True)
        self.ctx = moderngl.create_context()
        print("[init] GL context ok, compiling shaders...", flush=True)
        self.program = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER
        )
        print("[init] shaders compiled ok", flush=True)
 
        # just a screen-covering quad, shader does everything else
        verts = np.array([-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0], dtype='f4')
        self.vbo = self.ctx.buffer(verts.tobytes())
        self.vao = self.ctx.vertex_array(self.program, [(self.vbo, '2f', 'in_position')])
 
    def render(self, t, camera, stars, resolution):
        if 'u_time' in self.program:
            self.program['u_time'].value = t
 
        self.program['u_resolution'].value = resolution
        self.program['u_cameraPos'].value = tuple(camera.position)
        self.program['u_cameraDir'].value = tuple(camera.direction)
        self.program['u_star1_pos'].value = tuple(stars[0])
        self.program['u_star2_pos'].value = tuple(stars[1])
 
        self.ctx.clear(0.0, 0.0, 0.0)
        self.vao.render(moderngl.TRIANGLE_STRIP)
 
 
class BlackHoleSimulator:
    def __init__(self):
        pygame.init()
 
        flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((CONFIG.width, CONFIG.height), flags)
        pygame.display.set_caption("black hole thing")
 
        self.renderer = Renderer()
        self.camera = OrbitalCamera()
 
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
 
        self.dragging = False
        self.last_mouse = (0, 0)
        self.auto_rotate = True
 
    def get_star_positions(self, t):
        # two stars orbiting, numbers picked by eye until it looked decent
        s1 = (
            math.cos(t * 0.5) * 8.0,
            math.sin(t * 0.3) * 2.0,
            math.sin(t * 0.5) * 8.0,
        )
        s2 = (
            math.cos(t * 0.9 + 3.14) * 5.0,
            0.5,
            math.sin(t * 0.9 + 3.14) * 5.0,
        )
        return [s1, s2]
 
    def run(self):
        print("drag to orbit, scroll to zoom, space toggles auto rotate")
        running = True
 
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
 
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h),
                        pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
                    )
                    self.renderer.ctx.viewport = (0, 0, event.w, event.h)
 
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.dragging = True
                        self.auto_rotate = False
                        self.last_mouse = event.pos
                    elif event.button == 4:
                        self.camera.add_zoom(-1)
                    elif event.button == 5:
                        self.camera.add_zoom(1)
 
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging = False
 
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    dx = event.pos[0] - self.last_mouse[0]
                    dy = event.pos[1] - self.last_mouse[1]
                    self.camera.add_orbit(dx, dy)
                    self.last_mouse = event.pos
 
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.auto_rotate = not self.auto_rotate
 
            t = time.time() - self.start_time
 
            if self.auto_rotate:
                self.camera.add_orbit(1.0, 0.0)
 
            self.camera.update()
            stars = self.get_star_positions(t)
 
            self.renderer.render(t, self.camera, stars, pygame.display.get_window_size())
            pygame.display.flip()
 
            sys.stdout.write(f"\rfps: {self.clock.get_fps():.1f}   ")
            sys.stdout.flush()
 
            self.clock.tick(CONFIG.fps)
 
        pygame.quit()
        sys.exit(0)
 
 
if __name__ == "__main__":
    try:
        app = BlackHoleSimulator()
        app.run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("\ncrashed - press Enter to close...")
