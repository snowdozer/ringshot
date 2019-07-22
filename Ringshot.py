import sound

import pygame
import math
import random
import copy
import os

import constants
import events
import graphics
import geometry
import debug

import ball
import levels


def screen_update(fps):
    pygame.display.flip()
    final_display.fill(constants.BLACK)
    clock.tick(fps)


os.environ["SDL_VIDEO_CENTERED"] = "1"

# leave some pixels as a border, so it's less likely to click off the window
FULL_WIDTH = constants.FULL_WIDTH
FULL_HEIGHT = constants.FULL_HEIGHT
FULL_SIZE = constants.FULL_SIZE

SCREEN_LEFT = constants.SCREEN_LEFT
SCREEN_TOP = constants.SCREEN_TOP
TOP_LEFT = constants.SCREEN_TOP_LEFT

pygame.init()
final_display = pygame.display.set_mode(FULL_SIZE)
clock = pygame.time.Clock()

mouse_held = False
mouse_click = False
mouse_release = False

sound_transition = sound.load("transition")

LAST_LEVEL = levels.count_levels() - 1

save_data = open("Easily Editable Save Data.txt", 'r')
last_unlocked = int(save_data.read())
save_data.close()

LEVELS_PER_COURSE = 18

LEVEL_FONT = graphics.load_image("level_numbers")
logo_name = graphics.load_image("name", 4)
logo_bird_sprite = graphics.Spritesheet("logo", 10, 10, (11,), 4)
logo_bird = graphics.SpriteInstance(logo_bird_sprite)


def render_level_number(number):
    number_string = str(number)
    surface = graphics.new_surface((len(number_string) * 9, 15))
    for digit_num, digit in enumerate(str(number)):
        x = int(digit) * 9
        surface.blit(LEVEL_FONT, (digit_num * 9, 0), (x, 0, 9, 15))
    return surface


class MenuScreen:
    PAUSE_LENGTH = 60
    GROW_LENGTH = 120
    FADE_LENGTH = 60

    PAUSE_LAST = PAUSE_LENGTH
    GROW_LAST = PAUSE_LAST + GROW_LENGTH
    FADE_LAST = GROW_LAST + GROW_LENGTH

    CREDITS = 0
    LEVEL_SELECT = 1
    LEVEL_EDITOR = 2

    ARROW_WIDTH = 20
    ARROW_HEIGHT = 60
    LEFT_ARROW_X = 20
    RIGHT_ARROW_X = constants.FULL_WIDTH - 20 - ARROW_WIDTH
    ARROW_Y = constants.FULL_MIDDLE_INT[1] - ARROW_HEIGHT // 2

    PAGE_CHANGE_LENGTH = 30
    PAGE_CHANGE_A = -constants.FULL_WIDTH / (PAGE_CHANGE_LENGTH ** 2)

    LEFT = 1
    RIGHT = 2

    LOGO_WIDTH = 284
    LOGO_HEIGHT = 52
    LOGO_BIRD_X = (FULL_WIDTH - LOGO_WIDTH) // 2
    LOGO_BIRD_Y = FULL_HEIGHT - 100
    LOGO_NAME_X = LOGO_BIRD_X + 64
    LOGO_NAME_Y = LOGO_BIRD_Y - 12

    def __init__(self):
        self.arrow_y_offset = 0.0
        self.arrow_frame = 0

        self.page = self.LEVEL_SELECT
        self.next_page = 0
        self.changing_page = False
        self.page_frame = 0
        self.page_direction = 0
        self.x_offset = 0.0

        self.switch_to_level = False
        self.selected_level = 0
        self.transition_ball = None

        self.CIRCLE_RADII = (100, 140, 180, 220, 260)
        self.BUTTON_RING_RADII = (120, 160, 200, 240)
        self.angle_offsets = [0.6, 0.4, 0.2, 0.0]
        self.ROTATE_SPEED = 0.0005
        self.SHELL_COLORS = ball.SHELL_DEBUG_COLORS

        self.BUTTON_RADIUS = 16

        self.mouse_level = -1
        self.mouse_arrow = 0
        self.block_layers = levels.load_all_block_layers()

        self.grow_frame = 0
        self.grow_course = False
        self.grow_radius = 0.0
        self.target_radius = 0.0
        self.grow_a = 0.0
        self.level_alpha = 0

    def update(self):
        for angle_num in range(len(self.angle_offsets)):
            self.angle_offsets[angle_num] += self.ROTATE_SPEED
            self.angle_offsets[angle_num] %= math.pi * 2

        if self.grow_course:
            if self.grow_frame <= self.PAUSE_LAST:
                pass
            elif self.grow_frame <= self.GROW_LAST:
                a = self.grow_a
                x = self.grow_frame
                d = self.GROW_LAST
                c = self.target_radius
                self.grow_radius = a * (x - d) ** 2 + c
            elif self.level_alpha < 255:
                self.level_alpha += 10
                if self.level_alpha > 255:
                    self.level_alpha = 255
            else:
                self.grow_course = False
            self.grow_frame += 1

            return

        if not self.changing_page and self.page == self.LEVEL_SELECT:
            self.mouse_level = self.touching_level(events.mouse.position)
        else:
            self.mouse_level = -1
        self.update_menu_buttons()

        if events.mouse.released:
            if self.mouse_level != -1 and self.mouse_level < last_unlocked:
                self.selected_level = self.mouse_level
                self.switch_to_level = True

            elif self.mouse_arrow != 0:
                self.changing_page = True
                self.page_frame = 0

                if self.mouse_arrow == self.LEFT:
                    self.next_page = self.page - 1
                    self.page_direction = self.LEFT

                elif self.mouse_arrow == self.RIGHT:
                    self.next_page = self.page + 1
                    self.page_direction = self.RIGHT

        if self.changing_page:
            if self.page_frame < self.PAGE_CHANGE_LENGTH:
                self.x_offset = (self.page_frame - self.PAGE_CHANGE_LENGTH) ** 2
                self.x_offset = self.PAGE_CHANGE_A * self.x_offset
                if self.page_direction == self.RIGHT:
                    self.x_offset = -self.x_offset

                self.page_frame += 1
            else:
                self.changing_page = False
                self.page = self.next_page

        logo_bird.delay_next(10)

    def draw(self, surface):
        """Set level_hover to false if you don't want to draw the level
        being hovered over.
        """
        # Arrows
        if not self.changing_page:
            y = self.ARROW_Y + self.arrow_y_offset
            w = self.ARROW_WIDTH
            h = self.ARROW_HEIGHT
            color = constants.WHITE
            if self.page != 0:
                x = self.LEFT_ARROW_X
                direction = graphics.LEFT

                graphics.draw_arrow(surface, color, (x, y, w, h), direction)

            if self.page != 2:
                x = self.RIGHT_ARROW_X
                direction = graphics.RIGHT

                graphics.draw_arrow(surface, color, (x, y, w, h), direction)

        if self.PAUSE_LAST < self.grow_frame <= self.GROW_LAST:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)
            self.draw_level_select(surface, shake_x, shake_y)

        elif self.changing_page:

            # Level select page
            if self.page == self.LEVEL_SELECT:
                if self.page_direction == self.LEFT:
                    x = self.x_offset + FULL_WIDTH
                else:
                    x = self.x_offset - FULL_WIDTH
                self.draw_level_select(surface, int(x))

            elif self.next_page == self.LEVEL_SELECT:
                self.draw_level_select(surface, int(self.x_offset))

            # Credits page
            if self.page == self.CREDITS:
                x = self.x_offset - FULL_WIDTH
                self.draw_credits_options(surface, int(x))

            elif self.next_page == self.CREDITS:
                x = self.x_offset
                self.draw_credits_options(surface, int(x))

        elif self.page == self.LEVEL_SELECT:
            self.draw_level_select(surface)
        elif self.page == self.CREDITS:
            self.draw_credits_options(surface)

    def draw_level_select(self, surface, x_offset=0, y_offset=0):
        last_level = last_unlocked
        if self.grow_course:
            last_level -= 1
            color = self.SHELL_COLORS[last_level // 18 + 1]
            position = constants.FULL_MIDDLE_INT
            position = (position[0] + x_offset, position[1] + y_offset)
            pygame.draw.circle(surface, color, position, int(self.grow_radius))

            level_center = self.level_center(last_level)

            text = render_level_number(last_level + 1)
            text_x = level_center[0] - (text.get_width() / 2) + x_offset
            text_y = level_center[1] - (text.get_height() / 2) + y_offset
            text.set_alpha(self.level_alpha)

            surface.blit(text, (text_x, text_y))

        last_unlocked_course = (last_level - 1) // LEVELS_PER_COURSE

        position = (constants.FULL_WIDTH // 2, constants.FULL_HEIGHT // 2)
        position = (position[0] + x_offset, position[1] + y_offset)
        circle_index = last_unlocked_course + 2
        for color in reversed(self.SHELL_COLORS[:last_unlocked_course + 2]):
            circle_index -= 1
            radius = self.CIRCLE_RADII[circle_index]
            pygame.draw.circle(surface, color, position, radius)

        course_num = -1
        for level in range(last_level):
            if level % LEVELS_PER_COURSE == 0:
                course_num += 1

            level_center = self.level_center(level)

            text = render_level_number(level + 1)
            text_x = level_center[0] - (text.get_width() / 2) + x_offset
            text_y = level_center[1] - (text.get_height() / 2) + y_offset

            if not self.grow_course and level == self.mouse_level:
                text_y += 3

                # Draws a circle around the selected level
                # color = constants.WHITE
                # position = self.level_center(self.mouse_level)
                # pygame.draw.circle(surface, color, position, self.BUTTON_RADIUS, 2)

                if level < len(self.block_layers):
                    # position = constants.FULL_MIDDLE_INT
                    # pygame.draw.circle(surface, constants.BLACK, position, 60)

                    layer = self.block_layers[self.mouse_level]
                    x = constants.FULL_MIDDLE[0]
                    y = constants.FULL_MIDDLE[1]
                    x -= levels.WIDTH * 3 / 2
                    y -= levels.HEIGHT * 3 / 2
                    layer.draw_thumbnail(surface, (x, y), constants.BLACK, 3)

            surface.blit(text, (text_x, text_y))

    def draw_credits_options(self, surface, x_offset=0, y_offset=0):
        x = self.LOGO_BIRD_X + x_offset
        y = self.LOGO_BIRD_Y + y_offset
        surface.blit(logo_bird.get_now_frame(), (x, y))

        x = self.LOGO_NAME_X + x_offset
        y = self.LOGO_NAME_Y + y_offset
        surface.blit(logo_name, (x, y))

    def level_center(self, level_num):
        course_num = level_num // LEVELS_PER_COURSE
        level_in_course = level_num % LEVELS_PER_COURSE

        angle = math.pi * 2 * (level_in_course / LEVELS_PER_COURSE)
        angle -= math.pi / 2
        angle += self.angle_offsets[course_num]

        x = self.BUTTON_RING_RADII[course_num] * math.cos(angle)
        y = self.BUTTON_RING_RADII[course_num] * math.sin(angle)
        x += constants.FULL_MIDDLE[0]
        y += constants.FULL_MIDDLE[1]

        return int(x), int(y)

    def touching_level(self, point):
        distance = geometry.distance(constants.FULL_MIDDLE, point)

        if distance < 100.0:
            return -1

        for course_num, radius in enumerate(self.CIRCLE_RADII[1:]):
            if distance < radius:
                course = course_num
                break
        else:
            return -1

        course_angle = (math.pi * 2.0 / LEVELS_PER_COURSE)

        angle = geometry.angle_between(constants.FULL_MIDDLE, point)
        angle += math.pi / 2
        angle -= self.angle_offsets[course_num]
        angle += course_angle / 2
        if angle < 0.0:
            angle += math.pi * 2
        level_in_course = int(angle / course_angle)
        level = level_in_course + course * LEVELS_PER_COURSE

        point_distance = geometry.distance(point, self.level_center(level))
        if point_distance < self.BUTTON_RADIUS:
            return level
        return -1

    def init_grow_course(self):
        previous_course = (last_unlocked - 2) // 18
        self.grow_course = True
        self.grow_frame = 0
        self.level_alpha = 0
        self.grow_radius = self.CIRCLE_RADII[previous_course + 1]
        self.target_radius = self.CIRCLE_RADII[previous_course + 2]

        self.grow_a = float(self.grow_radius - self.target_radius)
        self.grow_a /= (self.PAUSE_LAST - self.GROW_LAST) ** 2

    def update_menu_buttons(self):
        mouse_x, mouse_y = events.mouse.position
        top = self.ARROW_Y + self.arrow_y_offset
        bottom = self.ARROW_Y + self.ARROW_HEIGHT + self.arrow_y_offset

        if top < mouse_y < bottom:
            left_left = self.LEFT_ARROW_X
            left_right = self.LEFT_ARROW_X + self.ARROW_WIDTH

            right_left = self.RIGHT_ARROW_X
            right_right = self.RIGHT_ARROW_X + self.ARROW_WIDTH

            if self.page != 0 and left_left < mouse_x < left_right:
                self.mouse_arrow = self.LEFT
            elif self.page != 2 and right_left < mouse_x < right_right:
                self.mouse_arrow = self.RIGHT
            else:
                self.mouse_arrow = 0

        else:
            self.mouse_arrow = 0

        self.arrow_y_offset = 3 * math.sin(3 * math.pi / 180 * self.arrow_frame)
        if self.arrow_frame >= 120:
            self.arrow_frame = 0
        else:
            self.arrow_frame += 1


class PlayScreen:
    SLOWMO_MAX = 8.0  # the largest factor of slowmo possible
    SPEEDUP_FACTOR = 0.05  # how much the slowmo effect "wears off" each frame

    AIMER_LAYERS = 4

    def __init__(self):
        self.level = None
        self.slowmo_factor = 1.0  # the coefficient of time-slow.
        self.balls = []
        self.players = []
        self.start_ball = None
        self.level_num = 0

        # make sure you DONT DRAW THE RED BUTTONS ON BLOCK_SURFACE
        self.block_surface = graphics.new_surface(constants.SCREEN_SIZE)

        self.start_position = constants.SCREEN_MIDDLE
        self.end_open = False

        self.transition = False
        self.end_ball = None

        self.unlocked = True

    def update(self):
        mouse = events.mouse
        new_x = mouse.position[0] - SCREEN_LEFT
        new_y = mouse.position[1] - SCREEN_TOP
        mouse.position = (new_x, new_y)
        keys = events.keys

        if mouse.held and self.players[0].containing_shells:
            if mouse.clicked:
                self.slowmo_factor = self.SLOWMO_MAX

            if self.slowmo_factor > 1.0:
                self.slowmo_factor -= self.SPEEDUP_FACTOR

                if self.slowmo_factor < 1.0:
                    self.slowmo_factor = 1.0

            for player in self.players:
                player.rotate_towards(mouse.position, self.slowmo_factor)

        if mouse.released and self.players[0].containing_shells:
            self.shoot_ball(mouse.position)
            self.slowmo_factor = 1.0

        if keys.pressed_key == pygame.K_r:
            if mouse.held:
                self.reset_level(True)
            else:
                self.reset_level(False)

        ball_index = len(self.balls)
        for ball_ in reversed(self.balls):
            ball_index -= 1
            if ball_.out_of_bounds():
                del self.balls[ball_index]
            else:
                ball_.check_collision(self.level, self.slowmo_factor)

                if self.level.pressed_buttons == self.level.total_buttons:
                    if ball_.touching_end:
                        self.transition = True
                        self.end_ball = ball_

                ball_.update_body(self.slowmo_factor)

        if not self.unlocked:
            if self.level.pressed_buttons == self.level.total_buttons:
                self.unlocked = True
                self.level.draw_debug_start_end(self.block_surface, (0, 0))

        graphics.update_ripples(self.slowmo_factor)

    def shoot_ball(self, position):
        """Shoots a ball towards a specified position."""
        add_balls = []
        remove_balls = []
        for player in self.players:
            old_ball = player

            new_radius = player.radius - ball.SHELL_WIDTH
            new_shell = old_ball.containing_shells[0]
            new_ball = ball.Ball(player.position, new_radius, new_shell)

            new_ball.is_player = True

            new_ball.angle = old_ball.angle
            new_ball.containing_shells = old_ball.containing_shells[1:]

            if old_ball.shell_type == ball.CLONE:
                old_ball.shell_type = old_ball.containing_shells[0]
                old_ball.containing_shells = old_ball.containing_shells[1:]
                old_ball.radius = new_radius

            else:
                old_ball.is_player = False
                old_ball.containing_shells = []
                remove_balls.append(old_ball)

            add_balls.append(new_ball)

            new_ball.launch_towards(position)
            old_ball.x_velocity = -new_ball.x_velocity
            old_ball.y_velocity = -new_ball.y_velocity

        for player in remove_balls:
            self.players.remove(player)

        for player in add_balls:
            self.players.append(player)
            self.balls.append(player)

    def draw(self, surface):
        surface.blit(self.block_surface, TOP_LEFT)
        self.level.draw_debug_layer(surface, levels.LAYER_BUTTONS, TOP_LEFT)

        graphics.draw_ripples(surface)

        if events.mouse.held and self.players[0].containing_shells:
            self.draw_aimers(surface)

        for ball_ in self.balls:
            ball_.draw_debug(surface, TOP_LEFT)

    def draw_aimers(self, surface):
        mouse_position = events.mouse.position
        for player in self.players:
            angle1 = geometry.angle_between(mouse_position, player.position)
            angle2 = angle1 + math.pi

            width = 2
            color = ball.SHELL_DEBUG_COLORS[player.shell_type]
            for layer in range(self.AIMER_LAYERS, 0, -1):
                magnitude = player.radius + layer ** 2

                diff1 = geometry.vector_to_difference(angle1, magnitude)
                diff2 = geometry.vector_to_difference(angle2, magnitude)
                point1 = (diff1[0] + player.x, diff1[1] + player.y)
                point2 = (diff2[0] + player.x, diff2[1] + player.y)
                point1 = graphics.screen_position(point1)
                point2 = graphics.screen_position(point2)
                pygame.draw.line(surface, color, point1, point2, width)

                width += 2

    def reset_level(self, slowmo=False):
        self.balls = [copy.deepcopy(self.start_ball)]
        self.players = [self.balls[0]]
        self.players[0].point_towards_end(self.level)
        columns = levels.WIDTH
        rows = levels.HEIGHT
        self.level.pressed_grid = [[False] * rows for _ in range(columns)]
        self.level.pressed_buttons = 0
        self.unlocked = False
        self.level.draw_debug_start_end(self.block_surface, (0, 0))
        if slowmo:
            self.slowmo_factor = self.SLOWMO_MAX

    def load_level(self, level_num):
        self.block_surface.fill(constants.TRANSPARENT)
        self.slowmo_factor = 1.0

        self.level_num = level_num
        self.level = levels.load_level(level_num)

        block_layer = levels.LAYER_BLOCKS
        self.level.draw_debug_layer(self.block_surface, block_layer, (0, 0))
        self.level.draw_debug_start_end(self.block_surface, (0, 0))

        start_tile = self.level.start_tile
        position = levels.middle_pixel(start_tile)
        radius = ball.first_ball_radius(self.level)
        containing_shells = self.level.start_shells
        shell = containing_shells.pop(0)

        self.start_ball = ball.Ball(position, radius, shell)
        self.start_ball.is_player = True
        self.start_ball.containing_shells = containing_shells

        self.reset_level()


class LevelTransition:
    PAUSE_LENGTH = 30
    OUT_LENGTH = 60
    IN_LENGTH = 60
    SHELL_LENGTH = 13

    PAUSE_LAST = PAUSE_LENGTH
    OUT_LAST = PAUSE_LAST + OUT_LENGTH
    IN_LAST = OUT_LAST + IN_LENGTH

    LAST_RADIUS = 700
    LAST_WIDTH = 150

    GENERAL = 1
    POINT_TO_LEVEL = 2
    LEVEL_TO_MENU = 3

    def __init__(self):
        self.previous_surface = graphics.new_surface(constants.FULL_SIZE)
        self.new_surface = graphics.new_surface(constants.FULL_SIZE)

        self.from_point = (0.0, 0.0)
        self.to_point = (0.0, 0.0)
        self.center = (0.0, 0.0)

        self.x_change = 0.0
        self.y_change = 0.0

        # finds the value a in y = a(x - r)(x - s) form
        # x and y are based off of the vertex, at maximum radius/width
        denominator = (self.OUT_LAST - self.PAUSE_LAST)
        denominator *= (self.OUT_LAST - self.IN_LAST)

        self.radius_a = self.LAST_RADIUS / denominator
        self.width_a = self.LAST_WIDTH / denominator

        self.frame = 0
        self.radius = 0.0
        self.width = 0.0

        self.transparency_temp = graphics.new_surface(FULL_SIZE)

        self.end_ball = None
        self.new_ball = None
        self.shell_count = 0
        self.color = constants.WHITE

        self.done = False

        self.sound_grow_shell = sound.load_numbers("grow_shell%i", 10)
        self.sound_grow_shell.set_volumes(0.3)

        self.sound_whoosh = sound.load("transition")
        self.sound_whoosh.set_volume(0.7)

        self.type = 0

    def update(self):
        if self.frame <= self.PAUSE_LAST:
            pass
        elif self.frame <= self.IN_LAST:
            center_x = self.center[0] + self.x_change
            center_y = self.center[1] + self.y_change
            self.center = (center_x, center_y)

            # equation is the (x - r)(x - s) part.
            equation = self.frame - self.PAUSE_LAST
            equation *= self.frame - self.IN_LAST
            self.radius = self.radius_a * equation
            self.width = self.width_a * equation

        elif self.type == self.POINT_TO_LEVEL:
            if (self.frame - self.IN_LAST) % self.SHELL_LENGTH == 0:
                self.shell_count += 1

                if self.shell_count > len(self.new_ball.containing_shells) + 1:
                    self.done = True
                elif self.shell_count < 12:
                    self.sound_grow_shell.play(self.shell_count - 2)

        else:
            self.done = True

        if self.frame == self.PAUSE_LAST:
            self.sound_whoosh.play()

        self.frame += 1

    def draw(self, surface):
        if self.frame <= self.PAUSE_LAST:
            surface.blit(self.previous_surface, (0, 0))

        elif self.frame <= self.OUT_LAST:
            shake_position = (random.randint(-3, 3), random.randint(-3, 3))
            surface.blit(self.previous_surface, shake_position)

            center = (int(self.center[0]), int(self.center[1]))
            radius = int(self.radius)
            width = int(self.width)
            pygame.draw.circle(surface, self.color, center, radius, width)

        elif self.frame <= self.IN_LAST:
            shake_position = (random.randint(-3, 3), random.randint(-3, 3))
            surface.blit(self.previous_surface, shake_position)

            center = (int(self.center[0]), int(self.center[1]))
            radius = int(self.radius)
            width = int(self.width)

            self.transparency_temp.fill(constants.BLACK)
            self.transparency_temp.blit(self.new_surface, (0, 0))
            color = constants.TRANSPARENT
            pygame.draw.circle(self.transparency_temp, color, center, radius)

            surface.blit(self.transparency_temp, shake_position)

            pygame.draw.circle(surface, self.color, center, radius, width)

        elif self.type == self.POINT_TO_LEVEL:
            surface.blit(self.new_surface, (0, 0))
            self.new_ball.draw_debug(surface, TOP_LEFT, self.shell_count)

        else:  # level-menu transition carries on for one more frame
            surface.blit(self.new_surface, (0, 0))

    def set_from_point(self, position):
        self.from_point = (position[0] + SCREEN_LEFT, position[1] + SCREEN_TOP)

    def set_to_point(self, position):
        self.to_point = (position[0] + SCREEN_LEFT, position[1] + SCREEN_TOP)

    def init_general(self, from_point, to_point, color):
        self.type = self.GENERAL

        self.frame = 0
        self.previous_surface.fill(constants.TRANSPARENT)
        self.previous_surface.blit(final_display, (0, 0))

        self.new_surface.fill(constants.TRANSPARENT)

        length = (self.OUT_LENGTH + self.IN_LENGTH)
        self.x_change = (to_point[0] - from_point[0]) / length
        self.y_change = (to_point[1] - from_point[1]) / length
        self.center = from_point

        self.color = color

    def init_point_to_level(self, from_point, level, new_ball, color):
        """
        Initializes the circle, starting from a given point to the ball in
        the given level, including building up the shells of the new ball.

        from_point is the first point.
        to_point is the
        Rearranging a quadratic in vertex form:
        (y - c) / ((x - d) ** 2) = a
        y is the first value
        c is the final value
        x is the first frame (0)
        d is the last frame
        """
        self.new_ball = new_ball
        self.new_ball.point_towards_end(level)

        to_point = graphics.screen_position(self.new_ball.position)

        self.init_general(from_point, to_point, color)
        self.type = self.POINT_TO_LEVEL
        level.draw_debug(transition.new_surface, TOP_LEFT)

        self.shell_count = 1

    def init_point_to_point(self, point1, point2):
        pass


def next_level_transition():
    old_position = graphics.screen_position(play_screen.end_ball.position)

    color = ball.SHELL_DEBUG_COLORS[play_screen.end_ball.shell_type]

    play_screen.load_level(play_screen.level_num + 1)
    level = play_screen.level
    new_ball = play_screen.players[0]

    transition.init_point_to_level(old_position, level, new_ball, color)


def menu_level_transition():
    level_num = main_menu.selected_level
    old_position = main_menu.level_center(level_num)
    color = ball.SHELL_DEBUG_COLORS[level_num // LEVELS_PER_COURSE + 1]

    play_screen.load_level(level_num)
    level = play_screen.level
    new_ball = play_screen.players[0]

    transition.init_point_to_level(old_position, level, new_ball, color)


def level_menu_transition():
    color = ball.SHELL_DEBUG_COLORS[play_screen.end_ball.shell_type]
    from_point = graphics.screen_position(play_screen.end_ball.position)
    to_point = constants.FULL_MIDDLE

    transition.init_general(from_point, to_point, color)
    transition.type = transition.LEVEL_TO_MENU
    main_menu.draw(transition.new_surface)

    play_screen.level_num += 1


def check_level_menu_transition():
    if play_screen.level_num + 1 == last_unlocked:
        if last_unlocked % LEVELS_PER_COURSE == 0:
            return True

    if play_screen.level_num == LAST_LEVEL:
        return True

    return False


main_menu = MenuScreen()

play_screen = PlayScreen()
file = open("Starting Level.txt", 'r')
play_screen.load_level(int(file.readline()))
file.close()

transition = LevelTransition()

MENU = 0
PLAY = 1
TRANSITION = 2
current_screen = MENU

while True:
    events.update()
    sound.update()

    if current_screen == PLAY:
        play_screen.update()
        play_screen.draw(final_display)

        if play_screen.transition:
            play_screen.transition = False
            current_screen = TRANSITION

            if check_level_menu_transition():
                if play_screen.level_num == LAST_LEVEL:
                    main_menu.page = main_menu.CREDITS
                    level_menu_transition()

                else:
                    main_menu.page = main_menu.LEVEL_SELECT
                    level_menu_transition()
                    main_menu.init_grow_course()
            else:
                next_level_transition()

            sound.play(ball.end_note, 0.6)

            if last_unlocked < play_screen.level_num + 1:
                last_unlocked = play_screen.level_num + 1
                save_data = open("Easily Editable Save Data.txt", 'w')
                save_data.write(str(last_unlocked) + "\n")
                save_data.close()

    elif current_screen == MENU:
        main_menu.update()
        main_menu.draw(final_display)
        if main_menu.switch_to_level:
            main_menu.switch_to_level = False
            main_menu.mouse_level = -1
            current_screen = TRANSITION

            menu_level_transition()

    elif current_screen == TRANSITION:
        transition.update()

        transition.draw(final_display)

        if transition.done:
            transition.done = False

            if transition.type == transition.POINT_TO_LEVEL:
                current_screen = PLAY
                if events.mouse.held:
                    play_screen.slowmo_factor = play_screen.SLOWMO_MAX
            elif transition.type == transition.LEVEL_TO_MENU:
                current_screen = MENU
            graphics.clear_ripples()

    debug.debug(clock.get_fps())
    debug.debug(current_screen)
    debug.debug(main_menu.grow_frame)
    debug.debug(main_menu.mouse_arrow)
    debug.draw(final_display)

    # if events.mouse.held:
    #     screen_update(2)
    # else:
    screen_update(60)
