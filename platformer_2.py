### Pymunk Platformer ###
# A platforming game featuring a grappling hook and moving camera

### THINGS TO DO ###
#   -   Add grappling hook
#   -   Custom level, sprites
#   -   Clean up


import os, math

import pygame, pytmx

import pymunk, pymunk.pygame_util

from player import Player

if pymunk.version != '5.7.0':
    error = ImportError()
    error.message = "Pymunk must be at version 5.7.0, due to a gamebreaking incompatibility with pymunk 6.0.0 and pygame"
    raise error

SPEED_LIMIT = 40
    

#   INITIALISATION
#-------------------------------

pygame.init()

clock = pygame.time.Clock()
dt = 0

screen = pygame.display.set_mode((800, 600))

debug_layer = pygame.Surface((12000, 600))  # Debug layer

space = pymunk.Space()
space.gravity = 0, -20

camera = pygame.Vector2((0,0))      #The "camera" is a vector by which we offset every element before drawing it.

draw_options = pymunk.pygame_util.DrawOptions(debug_layer) # Debug Utility
debug = False

grounded = False

#--------------------------------

def load_map(path_to_level):
    """ 
    Load Tiled Map using PyTMX 

    Keyword arguments:
    
    path_to_level -- a path to a .tmx file of the level.

    """

    map = pytmx.load_pygame(path_to_level) #loads each tile in the level with a pygame style (x,y) coordinate 

    rects = []

    for x, y, gid in map.get_layer_by_name("Platforms"):

        if map.get_tile_image_by_gid(gid) != None:      # Every tile without an image is assigned to the first layer, for some reason. This will crash if we try to draw a nonexistant image, so we check.

            #space.static_body.position = (              # A pymunk space contains only one static body. The position of this body does not matter. This is a performance saver, however we have to move the static body every time we make a new box.
            #    x * map.tilewidth + map.tilewidth/2,    # Pytmx loads the (x,y) coordinates based on the tile position, i.e 2 tiles to the left and 3 tiles up. We multiply this by the tile width to get the actual coordinate
            #    -(y * map.height + map.tileheight/2) + 109)  # I don't know why 109 is the correct amount. 

            #box = pymunk.Poly.create_box(space.static_body, (map.tilewidth, map.tileheight))
            #box.friction = 0.5

            #space.add(box)

            rect = pygame.Rect(x * map.tilewidth, y * map.tileheight, map.tilewidth, map.tileheight)
            rects.append(rect)

    for i in range(2):
        for rect in rects:
            for rect_2 in rects:
                if rect.y == rect_2.y and rect != rect_2:
                    rect.width += rect_2.width
                    if rect_2.x < rect.x:
                        rect.x = rect_2.x

                    rects.remove(rect_2)

    for rect in rects:
        space.static_body.position = (              # A pymunk space contains only one static body. The position of this body does not matter. This is a performance saver, however we have to move the static body every time we make a new box.
                rect.x + rect.width/2,    # Pytmx loads the (x,y) coordinates based on the tile position, i.e 2 tiles to the left and 3 tiles up. We multiply this by the tile width to get the actual coordinate
                -(rect.y + rect.height/2) + 600)  # I don't know why 109 is the correct amount. 

        box = pymunk.Poly.create_box(space.static_body, (rect.width, rect.height))
        box.friction = 0.8
        
        space.add(box)


    return map

map = load_map('maps/test_level.tmx')

player = Player(100, 50, space)

def convert_pygame(pos):
    """ Convert between pymunk coordinates, which dictate the center of an object, to pygame coordinates, which dictate the top left corner."""
    return (pos[0], -pos[1] + 600)

def draw():
    """ Draw every object, including the level"""

    screen.fill((255,255,255))

    if debug: 
        debug_layer.fill((255,255,255))
        space.debug_draw(draw_options)
        screen.blit(debug_layer, camera)    #   Draw the layer containing all hitboxes and debug utilities to the screen, offset by the camera

    for layer in map.visible_layers:

        for x, y, gid in layer:
            img = map.get_tile_image_by_gid(gid)

            if img != None:
                rect = pygame.Rect(x * map.tilewidth, y * map.tileheight, map.tilewidth, map.tileheight)
                screen.blit(img, rect.move(*camera))

    screen.blit(player.image, player.rect.move(*camera))


    pygame.display.flip()

done = False
while not done:

    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            
            done = True

            break

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and keys[pygame.K_LCTRL]:
                debug = not debug   # Toggle drawing hitboxes

            if event.key == pygame.K_SPACE and grounded:
                player.body.apply_impulse_at_local_point((0, 100)) # Jump

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d and grounded:
                player.body._set_velocity((player.body.velocity.x * 0.25, player.body.velocity.y))

    if done: break # Quit Game

    grounded = False
    for x, y, gid in map.get_layer_by_name("Platforms"):
        if map.get_tile_image_by_gid(gid) != None:
            rect = pygame.Rect(x * map.tilewidth, y * map.tileheight - 10, map.tilewidth, map.tileheight)
            if rect.colliderect(player.rect):
                grounded = True

    space.step(1/60)

    player.update(pygame.event.get(), grounded)

    player.rect.center = convert_pygame(player.body.position)
    player.body.angle = 0 # Prevent flipping

    if grounded:
        if player.body.velocity.x > SPEED_LIMIT:
            player.body._set_velocity((SPEED_LIMIT, player.body.velocity.y))
        elif player.body.velocity.x < -SPEED_LIMIT:
            player.body._set_velocity((-SPEED_LIMIT, player.body.velocity.y))

    camera = pygame.Vector2((-player.body.position[0] + 250, player.body.position[1] - 100)) # center camera on player

    draw()

    pygame.display.update()
    #clock.tick(120)