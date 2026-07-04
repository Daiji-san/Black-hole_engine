# Black-hole_engine
A Python + OpenGL black hole simulator with real-time gravitational lensing, built while learning raymarching and relativistic physics

# Relativistic Black Hole Simulator

A real-time, GPU-accelerated black hole renderer built in Python — simulating gravitational lensing, an accretion disk, and orbiting bodies using a raymarched fragment shader.




## Why I built this

I've always been fascinated by black holes — specifically how something with no light of its own can still produce one of the most visually iconic effects in physics: gravitational lensing. The spark for this specific project came from a video I watched on Kavan's YouTube channel, where he simulated a black hole in C++. Watching that made me want to attempt the same idea myself — but in Python, since that's the language I'm more comfortable with and wanted to push further in.

I'm a student, and I'll be upfront: I did not have the physics, math, or graphics programming background to do this entirely from scratch. I used AI (Claude) throughout this project — to understand raymarching, to get the initial GLSL structure working, to debug why my lensing effect wasn't visually showing up, and to understand the actual physics behind photon deflection near a Schwarzschild black hole.

What I *did* bring was the curiosity to keep pushing on it, the persistence to debug it when it didn't look right, and enough understanding by the end to explain what every part of it does and why. This README is my attempt to be transparent about all of that, rather than pretend this was a solo, from-memory build.

---

## What it does

- Renders a black hole with a proper event horizon using GPU raymarching (all per-pixel, done in a fragment shader)
- Simulates gravitational lensing — light rays bend as they pass near the black hole, distorting the background starfield
- Renders an accretion disk with a color gradient based on distance from the center
- Two orbiting bodies with independent orbital paths
- A decorative "spacetime funnel" grid to visualize curvature (this one's for looks, not physical accuracy)
- Free orbit camera (click + drag), zoom (scroll), and auto-rotate toggle (spacebar)

---

## Tech stack

- **Python 3.12**
- **Pygame** — window and input handling
- **ModernGL** — OpenGL context and shader management
- **GLSL 330** — the actual raymarching and lensing math runs entirely on the GPU
- **NumPy** — camera math

---

## The hard part: making the lensing actually visible

This was the biggest struggle of the whole project. I had gravity bending the light rays fairly early on, but visually... nothing happened. It took a while to actually understand *why*:

1. **There was nothing to lens.** The background was a flat color. Bending a ray that points at a solid color does nothing visible — lensing only shows up when there's detail behind the black hole to distort. Adding a procedural starfield sampled by the ray's *final* (bent) direction is what actually made the warping visible.
2. **The bending formula itself was too weak.** My first version used a simple `1/r³` falloff, which does basically nothing until a ray is already about to fall in. Getting a visible photon sphere and lensed ring required switching to a formula that conserves angular momentum (`h = r × v`) — closer to how light actually bends around a Schwarzschild black hole, still an approximation, but a real physics-based one instead of a "looked okay at the time" number.

Debugging this — figuring out *why* something that was technically implemented wasn't visually doing anything — was honestly a bigger learning experience than writing the original shader.

---

## What I still don't fully understand

In the interest of being honest about where my understanding actually is right now:

- The full Schwarzschild geodesic equations — I'm using a physically-motivated approximation (angular-momentum-conserving deflection), not solving the actual general relativity equations of motion.
- Why certain GLSL driver optimizations behave differently across GPUs (I ran into a divide-by-zero edge case that didn't crash on my machine but could behave unpredictably on others — I patched around it, but I don't fully understand the underlying driver behavior).
- Deeper raymarching optimization techniques (adaptive step sizing beyond what's here, distance-estimator functions for more complex geometry).

I'm treating these as things to come back to, not things I'm pretending to have solved.

---

## Timeline

This took about **a month**, working on and off around classes. Roughly:

- **Week 1** — Learning what raymarching even is, getting a basic shader pipeline running in Python (this alone ate several days — GLSL debugging without proper tooling is rough)
- **Week 2** — Understanding the physics enough to know what I was trying to approximate (event horizons, accretion disks, why lensing happens at all)
- **Week 3** — Getting the actual simulation working: camera orbit controls, the disk, the orbiting bodies
- **Week 4** — Debugging why the lensing wasn't visible, understanding the angular-momentum deflection formula, general polish

If you're a student thinking about attempting something similar: budget more time for debugging than for writing the initial code. Almost all of my time went into figuring out *why* something looked wrong, not writing new features.

---

## Controls

| Input | Action |
|---|---|
| Click + Drag | Orbit camera |
| Scroll | Zoom in/out |
| Spacebar | Toggle auto-rotate |

---

## Running it

```bash
pip install pygame moderngl numpy
python blackhole.py
```

Requires a GPU with OpenGL 3.3 support.

---

## Possible future improvements

- Real Schwarzschild geodesic integration instead of the current approximation
- Doppler beaming / redshift on the accretion disk (the classic "brighter on one side" effect from disk rotation)
- Adjustable black hole mass / camera presets via a small UI
- Better starfield (currently a cheap procedural hash, not a real skybox)

---

## Disclosure

This project was built with AI assistance (Claude) for the physics background, GLSL structure, and debugging help. All design decisions, testing, and the final implementation choices were my own. I'm sharing this openly because I think being honest about *how* you learn is more useful — to me and to anyone else looking at this — than pretending otherwise.
