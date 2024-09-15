from d import Camera, Model, load
import pygame
pygame.init()

screen = pygame.display.set_mode([500, 500])
pygame.display.set_caption("Untitled Game")

# pygame.mouse.set_relative_mode(True)
clock = pygame.time.Clock()

camera = Camera()

size = 20
model = Model(load('cube.obj'), size)
model.texture = pygame.image.load('texture.jpg')
model.position.z = 400
model.rotation.x = 180

dt = 0

running = True
while running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        camera.position += camera.forward * dt
    if keys[pygame.K_s]:
        camera.position -= camera.forward * dt     
  
    screen.fill((255, 255, 255)) # Background Color

    # Your game
    camera.render([model], screen)
    model.rotation.y += 1.5

    pygame.display.flip()
    dt = clock.tick(60) # Change this to FPS
    pygame.display.set_caption(f"Untitled Game | FPS: {clock.get_fps():.2f}")

pygame.quit()