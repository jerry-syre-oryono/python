from ursina import Ursina, Entity, color, Vec3, window, time, application, camera
from random import randint


app = Ursina()
camera.position = (0, 15, -20)
camera.look_at((0, 0, 0))
camera.fov = 60

window.title = '3D Snake Game (Ursina)'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

CELL_SIZE = 1
GRID_SIZE = 10

snake_texture = 'assets/seamless-green-snake-skin-pattern-free-vector.jpg'  # Actual file name in assets folder
snake = [Entity(model='cube', color=color.green, texture=snake_texture, position=(0,0,0))]
direction = Vec3(1,0,0)
food = Entity(model='cube', color=color.red, position=(randint(-GRID_SIZE//2, GRID_SIZE//2), 0, randint(-GRID_SIZE//2, GRID_SIZE//2)))

score = 0
speed = 4
move_timer = 0

def update():
    global move_timer, direction, score
    move_timer += time.dt
    if move_timer < 1/speed:
        return
    move_timer = 0
    # Move snake
    new_pos = snake[0].position + direction * CELL_SIZE
    # Check collision with self
    for segment in snake:
        if segment.position == new_pos:
            print('Game Over! Score:', score)
            application.quit()
    # Move body
    for i in range(len(snake)-1, 0, -1):
        snake[i].position = snake[i-1].position
    snake[0].position = new_pos
    # Check food collision
    if snake[0].position == food.position:
        score += 1
        snake.append(Entity(model='cube', color=color.green, texture=snake_texture, position=snake[-1].position))
        food.position = (randint(-GRID_SIZE//2, GRID_SIZE//2), 0, randint(-GRID_SIZE//2, GRID_SIZE//2))


def input(key):
    global direction
    if key == 'left arrow' and direction != Vec3(1,0,0):
        direction = Vec3(-1,0,0)
    if key == 'right arrow' and direction != Vec3(-1,0,0):
        direction = Vec3(1,0,0)
    if key == 'up arrow' and direction != Vec3(0,0,1):
        direction = Vec3(0,0,1)
    if key == 'down arrow' and direction != Vec3(0,0,-1):
        direction = Vec3(0,0,-1)

app.run()
