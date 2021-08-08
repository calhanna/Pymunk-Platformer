### Pymunk Platformer ###
# A platforming game featuring a grappling hook and moving camera

### THINGS TO DO ###
#   -   Background
#   -   Fix Debug Draw
#   -   More Level Design
#   -   Clean up


import os, math

import pygame, pytmx

import pymunk, pymunk.pygame_util

from player import Player

if pymunk.version != '5.7.0':
    print("Pymunk must be at version 5.7.0, due to a gamebreaking incompatibility with pymunk 6.0.0 and pygame")
    raise ImportError()

SPEED_LIMIT = 120
GRAVITY = 600
    
#   INITIALISATION
#-------------------------------

pygame.init()

clock = pygame.time.Clock()
dt = 0

screen = pygame.display.set_mode((800, 600))

debug_layer = pygame.Surface((5120, 5120))  # When debug_draw is active we draw every hit box to this layer and then offset the layer so it moves with the camera.

space = pymunk.Space()
space.gravity = 0, -GRAVITY

camera = pygame.Vector2((0,0))      #The "camera" is a vector by which we offset every element before drawing it.

draw_options = pymunk.pygame_util.DrawOptions(debug_layer) # Debug Utility
debug = False

grounded = False

grapple = None
grapple_increment = 0

anchors = []
objects = []

#--------------------------------

def load_image(filename, colorkey_pixel = None):
    """ Loads an image and converts the transparent pixels """
    try:
        image = pygame.image.load(filename)    
    except pygame.error:
        print('Cannot load image ' + filename)
        raise SystemExit

    image = image.convert()
    if colorkey_pixel is not None:  # select transparent colour
        colorkey = image.get_at(colorkey_pixel)
        image.set_colorkey(colorkey, pygame.RLEACCEL)

    return image, image.get_rect()

chain = load_image("images/items/chain.png", (1,0))[0]


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
            rect = pygame.Rect(x * map.tilewidth, y * map.tileheight, map.tilewidth, map.tileheight)
            rects.append(rect)

    for i in range(2):                                  # This merges the platforms before making collision bodies. This is supposed to prevent the player from jumping a little whenever they go over the border of two tiles.
        for rect in rects:                              # However, it is kinda broken right now, and you may notice a bump between the 4th and 5th tiles of the first platform.
            for rect_2 in rects:
                if rect.y == rect_2.y and rect != rect_2:
                    if rect.x - rect_2.x < rect.width + 128 and rect.x - rect_2.x >= -128:
                        rect.width += rect_2.width
                        if rect_2.x < rect.x:
                            rect.x = rect_2.x

                        rects.remove(rect_2)

    for rect in rects:
        space.static_body.position = (              # A pymunk space contains only one static body. The position of this body does not matter. This is a performance saver, however we have to move the static body every time we make a new box.
                rect.x + rect.width/2,    # Pytmx loads the (x,y) coordinates based on the tile position, i.e 2 tiles to the left and 3 tiles up. We multiply this by the tile width to get the actual coordinate
                -(rect.y + rect.height/2) + 600) 

        box = pymunk.Poly.create_box(space.static_body, (rect.width, rect.height))
        box.friction = 0.8
        
        space.add(box)

    #loading grapple anchors
    for x, y, gid in map.get_layer_by_name("Anchors"):
        if map.get_tile_image_by_gid(gid) != None:
            body = pymunk.Body(0, 0, body_type=pymunk.Body.KINEMATIC)
            body.position = (x * map.tilewidth + map.tilewidth/2, -(y * map.tileheight + map.tileheight/2) + 600)

            space.add(body)
            anchors.append(body)

    #loading dynamic objects
    for object in map.objects:
        body = pymunk.Body(object.mass, pymunk.moment_for_box(object.mass,(32,32)))
        body.position = (object.x + 16, -(object.y + 16) + 600)

        hitbox = pymunk.Poly.create_box(body, (32,32))
        hitbox.friction = 0.5

        space.add(body, hitbox)
        objects.append((hitbox, object.image))


    return map

map = load_map('maps/test_level_2.tmx')

player = Player(100, 800, space)

def convert_pygame(pos):
    """ Convert between pymunk coordinates, which dictate the center of an object, to pygame coordinates, which dictate the top left corner."""
    return (pos[0], -pos[1] + 600)

def distance(pos, obj):
    """ Returns the distance between two points"""

    dx = pos[0] - obj[0]
    dy = pos[1] - obj[1]
    return math.sqrt((dx*dx) + (dy*dy))

def find_angle(pos, obj):
    """ Returns the angle from point pos to point obj """
    dx = pos[0] - obj[0]
    dy = pos[1] - obj[1]

    try:
        return math.atan(dy/dx)
    except:
        return(math.radians(90))

def draw():
    """ Draw every object, including the level"""

    screen.fill((50,50,50))

    if debug: 
        debug_layer.fill((255,255,255))
        space.debug_draw(draw_options)
        screen.blit(debug_layer, camera)    #   Draw the layer containing all hitboxes and debug utilities to the screen, offset by the camera

    for layer in map.visible_layers:
        if layer != map.get_layer_by_name("Dynamic Objects"):
            for x, y, gid in layer:
                img = map.get_tile_image_by_gid(gid)

                if img != None:
                    rect = pygame.Rect(x * map.tilewidth, y * map.tileheight, map.tilewidth, map.tileheight)
                    screen.blit(img, rect.move(*camera))
        else:
            for object in objects:  #   Each object is a tuple containing the hitbox and the tile image
                rect = pygame.Rect(object[0].body.position[0] - 16, -object[0].body.position[1] + 600 - 16, 32, 32)
                screen.blit(object[1], rect.move(*camera))


    if grapple != None:
        #pygame.draw.line(screen, (0,255,0), (player.rect.center[0] + camera[0], player.rect.center[1] + camera[1]), (grapple.b.position[0] + camera[0], -grapple.b.position[1] + 600 + camera[1]))
        gl = int(distance(player.rect.center, (grapple.b.position[0], -grapple.b.position[1] + 600)))
        angle = find_angle(player.rect.center, (grapple.b.position[0], -grapple.b.position[1] + 600))

        if math.degrees(angle) >= 0: angle += math.radians(180)

        if player.rect.center[1] <= -grapple.b.position[1] + 600:
            angle += math.radians(180)

        limit = int(gl/7)
        for i in range(limit):              # Draws chain links in increments along the grappling hook to create the illusion of a chain 
            rect = chain.get_rect()
            rect.x = int(player.rect.center[0] - 5 + i * math.cos(angle) * 7)
            rect.y = int(player.rect.center[1] - 5 + i * math.sin(angle) * 7)

            # Finds the angle between the current link and the next. Do not look at it. Do not acknowlege it.
            sub_angle = math.degrees(find_angle(rect.center, (player.rect.center[0] - 2 + (i+1) * math.cos(angle) * 7, (player.rect.center[1] - 1.5 + (i+1) * math.sin(angle) * 7))))

            screen.blit(pygame.transform.rotate(chain, -sub_angle+95), rect.move(*camera))  # I do not know why you have to make sub_angle negative. I do not know why you have to add exactly 95 degrees. Do not ask me as I will probably scream.


    screen.blit(player.image, player.rect.move(*camera))

    pygame.display.flip()

done = False
while not done:
    keys = pygame.key.get_pressed()
    mouse = (pygame.mouse.get_pos()[0] - camera[0], pygame.mouse.get_pos()[1] - camera[1])  # Pygame's mouse works with *screen coordinates*, not *world coordinates*.

    if grapple != None:
        if keys[pygame.K_LSHIFT]:
            grapple_increment += 1
            if grapple.max > 80:
                grapple.max -= grapple_increment
        else:
            grapple_increment = 0
        
        if keys[pygame.K_LCTRL]:
            grapple.max += 5

        if pygame.mouse.get_pressed()[0] == False:
            space.remove(grapple)
            grapple = None


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            
            done = True

            break

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and keys[pygame.K_LCTRL]:
                debug = not debug   # Toggle drawing hitboxes
                space.gravity = 0,0

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d and grounded:
                player.body._set_velocity((player.body.velocity.x * 0.25, player.body.velocity.y))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == pygame.BUTTON_LEFT:
                for anchor in anchors:  
                    if distance(mouse, (anchor.position[0], -anchor.position[1] + 600)) < 60:
                        max = distance(player.rect.center, (anchor.position[0], -anchor.position[1] + 600))
                        grapple: pymunk.Constraint() = pymunk.SlideJoint(player.body, anchor, (0,0), (0,0), 0, max)    #   We set the grapple to a pymunk SlideJoint constraint which allows the player to move so long as it is not outside of the min and max distances
                        space.add(grapple)                                                                              #   Good for modelling chains.

    if done: break # Quit Game

    # Check if player is on a platform
    grounded = False
    for x, y, gid in map.get_layer_by_name("Platforms"):
        if map.get_tile_image_by_gid(gid) != None:
            rect = pygame.Rect(x * map.tilewidth, y * map.tileheight - 10, map.tilewidth, map.tileheight)
            if rect.colliderect(player.rect):
                grounded = True

    space.step(1/60)

    #Player movement function
    player.update(pygame.event.get(), grounded)

    # Update the position at which we draw the player
    player.rect.center = convert_pygame(player.body.position)
    player.body.angle = 0 # Prevent flipping

    #if grounded:                                    # Velocity Limiting. We take the player's current horizontal velocity and check it against the speed limit. 
    #    if player.body.velocity.x > SPEED_LIMIT:    # If it is above, we set the velocity to the speed limit, but do not change the vertical velocity.
    #        player.body._set_velocity((SPEED_LIMIT, player.body.velocity.y))
    #    elif player.body.velocity.x < -SPEED_LIMIT:
    #        player.body._set_velocity((-SPEED_LIMIT, player.body.velocity.y))

    if keys[pygame.K_SPACE] and grounded:
            player.body.apply_impulse_at_local_point((0, 200)) # Jump
            grounded = False

    camera = pygame.Vector2((-player.body.position[0] + 400, player.body.position[1] - 300)) # center camera on player
  
    draw()

    pygame.display.update()
    clock.tick(120)