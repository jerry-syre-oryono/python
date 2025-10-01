from ursina import *
import math

app = Ursina()
window.title = '3D Flight Simulator (Ursina)'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Skybox
sky = Entity(model='sphere', scale=150, texture='sky_default', double_sided=True)

# Terrain
terrain = Entity(model='plane', scale=(100,1,100), texture='grass', texture_scale=(50,50), y=-2, color=color.rgb(100,200,100))


# Reference points (3D grid)
reference_points = []
for x in range(-40, 41, 20):
    for y in range(0, 41, 20):
        for z in range(-40, 41, 20):
            reference_points.append(Entity(model='sphere', color=color.white, scale=0.7, position=(x, y, z), alpha=0.5))

# Plane model (use cube for now, can swap for .obj later)
plane = Entity(model='cube', color=color.orange, scale=(2,0.5,4), position=(0,5,0))

camera.parent = plane
camera.position = (0,2,-10)
camera.rotation = (10,0,0)

speed = 10
pitch = 0
yaw = 0
roll = 0

# Checkpoints
checkpoints = [Entity(model='torus', color=color.red, position=(x*20,5,z*20), scale=3) for x,z in [(2,2),(-2,2),(2,-2),(-2,-2)]]

score = 0

# Flight controls

def update():
    global pitch, yaw, roll, score
    # Mouse look (all axes)
    if held_keys['right mouse']:
        yaw += mouse.velocity[0] * 60 * time.dt
        pitch -= mouse.velocity[1] * 60 * time.dt
        roll += mouse.velocity[2] * 60 * time.dt if hasattr(mouse.velocity, '__getitem__') and len(mouse.velocity) > 2 else 0
    # Keyboard roll
    if held_keys['q']:
        roll += 60 * time.dt
    if held_keys['e']:
        roll -= 60 * time.dt
    # Clamp angles
    pitch = clamp(pitch, -80, 80)
    roll = clamp(roll, -80, 80)
    # Apply rotation
    plane.rotation_x = pitch
    plane.rotation_y = yaw
    plane.rotation_z = roll
    # Move forward
    forward = plane.forward * speed * time.dt
    plane.position += forward
    # Camera follows
    camera.position = (0,2,-10)
    camera.rotation = (10,0,0)
    # Check for checkpoint collision
    for cp in checkpoints:
        if distance(plane.position, cp.position) < 3:
            score += 1
            cp.enabled = False
            print(f'Checkpoint reached! Score: {score}')
    # Prevent going below terrain
    if plane.y < 1:
        plane.y = 1

app.run()
