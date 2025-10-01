from ursina import *
from random import randint, choice
import math

app = Ursina()
mouse_sensitivity = 100
rotation_x = 20
rotation_y = 0
rotation_z = 0
window.title = '3D Maze Car Game (Ursina)'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

camera.position = (0, 20, -30)
camera.look_at((0, 0, 0))
camera.fov = 60

MAZE_SIZE = 10
CELL_SIZE = 2

# Simple maze generation (random walls)
maze = [[choice([0, 1]) for _ in range(MAZE_SIZE)] for _ in range(MAZE_SIZE)]
maze[0][0] = 0  # Start
maze[MAZE_SIZE-1][MAZE_SIZE-1] = 0  # End

# Draw maze
for x in range(MAZE_SIZE):
    for z in range(MAZE_SIZE):
        if maze[x][z] == 1:
            Entity(model='cube', color=color.gray, position=(x*CELL_SIZE, 1, z*CELL_SIZE), scale=(CELL_SIZE, 2, CELL_SIZE))

# Car character
car = Entity(model='cube', color=color.azure, position=(0, 1, 0), scale=(1.5, 1, 2), texture='white_cube')

speed = 5

def update():
    global rotation_x, rotation_y, rotation_z
    move = Vec3(0,0,0)
    if held_keys['w']:
        move += car.forward * speed * time.dt
    if held_keys['s']:
        move -= car.forward * speed * time.dt
    if held_keys['a']:
        car.rotation_y += 90 * time.dt
    if held_keys['d']:
        car.rotation_y -= 90 * time.dt
    # Mouse look
    if held_keys['right mouse']:
        rotation_y += mouse.velocity[0] * mouse_sensitivity
        rotation_x -= mouse.velocity[1] * mouse_sensitivity
        rotation_z += mouse.velocity[2] * mouse_sensitivity if hasattr(mouse.velocity, '__getitem__') and len(mouse.velocity) > 2 else 0
        rotation_x = clamp(rotation_x, -80, 80)
        rotation_z = clamp(rotation_z, -80, 80)
    camera.rotation_x = rotation_x
    camera.rotation_y = rotation_y
    camera.rotation_z = rotation_z
    offset = Vec3(0, 20, -30)
    # Apply yaw (Y), pitch (X), and roll (Z) rotations
    rad_y = math.radians(rotation_y)
    rad_x = math.radians(rotation_x)
    rad_z = math.radians(rotation_z)
    # Yaw
    rotated_offset = Vec3(
        offset.z * math.sin(rad_y) + offset.x * math.cos(rad_y),
        offset.y,
        offset.z * math.cos(rad_y) - offset.x * math.sin(rad_y)
    )
    # Pitch
    rotated_offset = Vec3(
        rotated_offset.x,
        rotated_offset.y * math.cos(rad_x) - rotated_offset.z * math.sin(rad_x),
        rotated_offset.y * math.sin(rad_x) + rotated_offset.z * math.cos(rad_x)
    )
    # Roll
    rotated_offset = Vec3(
        rotated_offset.x * math.cos(rad_z) - rotated_offset.y * math.sin(rad_z),
        rotated_offset.x * math.sin(rad_z) + rotated_offset.y * math.cos(rad_z),
        rotated_offset.z
    )
    camera.position = car.position + rotated_offset
    camera.look_at(car.position)
    # Collision check
    new_pos = car.position + move
    grid_x = int(round(new_pos.x / CELL_SIZE))
    grid_z = int(round(new_pos.z / CELL_SIZE))
    if 0 <= grid_x < MAZE_SIZE and 0 <= grid_z < MAZE_SIZE and maze[grid_x][grid_z] == 0:
        car.position = new_pos
    # Win condition
    if grid_x == MAZE_SIZE-1 and grid_z == MAZE_SIZE-1:
        print('You win!')
        application.quit()

app.run()
