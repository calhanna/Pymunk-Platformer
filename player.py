import pygame, pymunk

class Player():
    """ Controllable player simulated using pymunk. Defines all hitboxes """

    def __init__(self, x, y, space):

        self.image = pygame.image.load('images/player/idle.png')

        self.rect = self.image.get_rect()

        self.rect.x, self.rect.y = x, y

        self.body = pymunk.Body(2, pymunk.moment_for_box(2, (16, 24)))
        self.body.position = (x, -y + 600)

        self.hitbox = pymunk.Poly.create_box(self.body, (16,24))
        self.hitbox.friction = 0.5

        space.add(self.body, self.hitbox)
        
    def update(self, events, gnd):
        pressed = pygame.key.get_pressed()

        move = pygame.Vector2((0, 0))
        self.hitbox.friction = 0.5

        if pressed[pygame.K_a]: move += (-1, 0)

        if pressed[pygame.K_d]: move += (1, 0)

        if move.length() > 0: move.normalize_ip()
        else: 
            self.hitbox.friction = 0.8

        if gnd:
            self.body.apply_impulse_at_local_point(move*0.5)
        else:
            self.body.apply_impulse_at_local_point(move*0.25)