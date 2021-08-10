### Pymunk Platformer ###
# A platforming game featuring a grappling hook and moving camera

### THINGS TO DO ###
#   -   Background
#   -   Fix Debug Draw
#   -   More Level Design
#   -   Clean up


import os, sys, math
from typing import Type

import pygame, pytmx

import pymunk, pymunk.pygame_util

from player import Player

if sys.version_info[0] != 3:
    print('This game requires at least Python version 3.0.0')

if pymunk.version != '5.7.0':
    print("Pymunk must be at version 5.7.0, due to a gamebreaking incompatibility with pymunk 6.0.0 and pygame")
    raise ImportError()

WIDTH = 800
HEIGHT = 600
SPEED_LIMIT = 120
GRAVITY = 800
    
#   INITIALISATION
#-------------------------------

pygame.init()

clock = pygame.time.Clock()
dt = 0

screen = pygame.display.set_mode((WIDTH, HEIGHT))

debug_layer = pygame.Surface((5120, 5120))  # When debug_draw is active we draw every hit box to this layer and then offset the layer so it moves with the camera.

space = pymunk.Space()
space.gravity = 0, -GRAVITY

camera = pygame.Vector2((0,0))      #The "camera" is a vector by which we offset every element before drawing it.

draw_options = pymunk.pygame_util.DrawOptions(debug_layer) # Debug Utility
debug = False

grounded = False

grapple = None
grapple_increment = 0

step = 1/60

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
    global objects, anchors, ladders

    map = pytmx.load_pygame(path_to_level) #loads each tile in the level with a pygame style (x,y) coordinate 

    anchors = []
    objects = []
    ladders = []

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
                -(rect.y + rect.height/2) + HEIGHT) 

        box = pymunk.Poly.create_box(space.static_body, (rect.width, rect.height))
        box.friction = 0.8
        
        space.add(box)

    #loading grapple anchors
    for x, y, gid in map.get_layer_by_name("Anchors"):
        if map.get_tile_image_by_gid(gid) != None:
            body = pymunk.Body(0, 0, body_type=pymunk.Body.KINEMATIC)
            body.position = (x * map.tilewidth + map.tilewidth/2, -(y * map.tileheight + map.tileheight/2) + HEIGHT)

            space.add(body)
            anchors.append(body)

    for object in map.objects:
        if object.type == 'Crate':  # Loading dynamic crate objects
            body = pymunk.Body(object.mass, pymunk.moment_for_box(object.mass,(object.width,object.height)))
            body.position = (object.x + object.width/2, -(object.y + object.height/2) + HEIGHT)

            hitbox = pymunk.Poly.create_box(body, (object.width,object.height))
            hitbox.friction = 0.5

            space.add(body, hitbox)
            objects.append((hitbox, object.image, (object.width, object.height)))
        elif object.type == 'Platform': # Loading small platforms
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            body.position = (object.x + object.width/2, -(object.y + object.height/2) + HEIGHT)

            hitbox = pymunk.Poly.create_box(body, (object.width,object.height))
            hitbox.friction = 0.5

            space.add(body, hitbox)
    
    for x, y, gid in map.get_layer_by_name("Ladders"):
        if map.get_tile_image_by_gid(gid) != None:
            rect = pygame.Rect(x * map.tilewidth, y * map.tileheight + 10, map.tilewidth, map.tileheight - 10)
            ladders.append(rect)


    return map

map = load_map('maps/test_level_2.tmx')

player = Player(100, 1200, space)

def convert_pygame(pos):
    """ Convert between pymunk coordinates, which dictate the center of an object, to pygame coordinates, which dictate the top left corner."""
    return (pos[0], -pos[1] + HEIGHT)

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

    # You may notice a lot of try, except TypeError statements in this function. For some reason it raises a typerror after the player comes off a ladder. I do not know why.

    screen.fill((50,50,50))

    if debug: 
        debug_layer.fill((255,255,255))
        space.debug_draw(draw_options)
        screen.blit(debug_layer, camera)    #   Draw the layer containing all hitboxes and debug utilities to the screen, offset by the camera

    for layer in map.visible_layers:
        if layer != map.get_layer_by_name("Dynamic Objects") and layer != map.get_layer_by_name('Small Platforms'):
            for x, y, gid in layer:
                img = map.get_tile_image_by_gid(gid)

                if img != None:
                    rect = pygame.Rect(x * map.tilewidth, y * map.tileheight, map.tilewidth, map.tileheight)
                    screen.blit(img, rect.move(*camera))
        else:
            for object in objects:  #   Each object is a tuple containing the hitbox, the tile image and the dimensions of the object
                rect = pygame.Rect(object[0].body.position[0] - object[2][0]/2, -object[0].body.position[1] + HEIGHT - object[2][1]/2, object[2][0], object[2][1])
                screen.blit(object[1], rect.move(*camera))


    if grapple != None:
        #pygame.draw.line(screen, (0,255,0), (player.rect.center[0] + camera[0], player.rect.center[1] + camera[1]), (grapple.b.position[0] + camera[0], -grapple.b.position[1] + HEIGHT + camera[1]))
        gl = int(distance(player.rect.center, (grapple.b.position[0], -grapple.b.position[1] + HEIGHT)))
        angle = find_angle(player.rect.center, (grapple.b.position[0], -grapple.b.position[1] + HEIGHT))

        if math.degrees(angle) >= 0: angle += math.radians(180)

        if player.rect.center[1] <= -grapple.b.position[1] + HEIGHT:
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

        if grapple.b != pymunk.Body.KINEMATIC:
            max = distance(player.rect.center, (grapple.b.position[0], -grapple.b.position[1] + HEIGHT))

        if pygame.mouse.get_pressed()[0] == False:
            space.remove(grapple)
            grapple = None

    if keys[pygame.K_q]:
        if step == 1/60:    #Slow motion. This step variable is used as the time difference for the physics engine update. By decreasing the value, we slow down "time" by slowing down the physics engine
            step = 1/360
    elif step != 1/60:
        step = 1/60

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
                    if distance(mouse, (anchor.position[0], -anchor.position[1] + HEIGHT)) < 60:
                        max = distance(player.rect.center, (anchor.position[0], -anchor.position[1] + HEIGHT))
                        grapple: pymunk.Constraint() = pymunk.SlideJoint(player.body, anchor, (0,0), (0,0), 0, max)    #   We set the grapple to a pymunk SlideJoint constraint which allows the player to move so long as it is not outside of the min and max distances
                        space.add(grapple)                                                                              #   Good for modelling chains.

                for obj in objects:
                    if distance(mouse, (obj[0].body.position[0], -obj[0].body.position[1] + HEIGHT)) < 60 and grapple == None:
                        max = distance(player.rect.center, (obj[0].body.position[0], -obj[0].body.position[1] + HEIGHT))
                        grapple: pymunk.Constraint() = pymunk.SlideJoint(player.body, obj[0].body, (0,0), (0,0), 0, max)    #   We set the grapple to a pymunk SlideJoint constraint which allows the player to move so long as it is not outside of the min and max distances
                        space.add(grapple)  

    if done: break # Quit Game

    if keys[pygame.K_SPACE] and grounded:
        player.body.apply_impulse_at_local_point((0, 800)) # Jump
        grounded = False

    # Check if player is on a platform
    grounded = False
    if not keys[pygame.K_SPACE]:
        for x, y, gid in map.get_layer_by_name("Platforms"):
            if map.get_tile_image_by_gid(gid) != None:
                rect = pygame.Rect(x * map.tilewidth + 2, y * map.tileheight - 8, map.tilewidth - 2, map.tileheight)
                if rect.colliderect(player.rect):
                    grounded = True
        for obj in objects:
            rect = pygame.Rect(obj[0].body.position[0] - 16, -obj[0].body.position[1] + HEIGHT - 20, 30, 32)
            if rect.colliderect(player.rect):
                grounded = True
        for ladder in ladders:
            if ladder.move(0,-10).colliderect(player.rect):
                grounded = True

    # Ladder Movement
    on_ladder = False
    if keys[pygame.K_w]:
        for ladder in ladders:
            if ladder.colliderect(player.rect):
                player.body.body_type = pymunk.Body.KINEMATIC     # Kinematic bodies are unaffected by gravity, so we temporarily convert the player body to kinematic while on a ladder
                player.body.position = (player.body.position[0], player.body.position[1] + 10)
                on_ladder = True
    
    if not on_ladder and player.body.body_type == pymunk.Body.KINEMATIC:
        player.body.body_type = pymunk.Body.DYNAMIC     # When we convert back to dynamic, we need to reset the mass and moment as a kinematic body does not have these
        player.body.mass = 2
        player.body.moment = pymunk.moment_for_box(2, (32,48))
        player.body.apply_impulse_at_local_point((0,900))   # little jump at the end of a ladder

    #Player movement function
    player.update(pygame.event.get(), grounded)

    # Update the position at which we draw the player
    safe_to_update = True
    nan = str(player.body.position[0])
    if nan == 'nan':
        safe_to_update = False
    
    if safe_to_update:
        player.rect.center = convert_pygame(player.body.position)
        player.body.angle = 0 # Prevent flipping

    #if grounded:                                    # Velocity Limiting. We take the player's current horizontal velocity and check it against the speed limit. 
    #    if player.body.velocity.x > SPEED_LIMIT:    # If it is above, we set the velocity to the speed limit, but do not change the vertical velocity.
    #        player.body._set_velocity((SPEED_LIMIT, player.body.velocity.y))
    #    elif player.body.velocity.x < -SPEED_LIMIT:
    #        player.body._set_velocity((-SPEED_LIMIT, player.body.velocity.y))

        camera = pygame.Vector2((-player.body.position[0] + 400, player.body.position[1] - 300)) # center camera on player
  
    draw()

    # check if out of bounds
    if player.rect.x < -128 or player.rect.x > 5320 or player.rect.y > 3000 or player.rect.y < 0:
        space = pymunk.Space()
        space.gravity = 0, -GRAVITY
        player = Player(100, 1200, space)
        grapple = None
        map = load_map('maps/test_level_2.tmx')

    pygame.display.update()
    clock.tick(120)
    space.step(step)