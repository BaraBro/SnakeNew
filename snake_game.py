#!/usr/bin/env python3
"""
Terminal Snake Game
A classic Snake game implemented using Python's curses library.

Controls:
- Arrow keys or WASD to move
- Q to quit
- R to restart after game over

Author: AI Assistant
"""

import curses
import random
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


@dataclass
class Point:
    y: int
    x: int
    
    def __add__(self, direction: Direction):
        dy, dx = direction.value
        return Point(self.y + dy, self.x + dx)
    
    def __eq__(self, other):
        return self.y == other.y and self.x == other.x


class SnakeGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Game boundaries (leave space for borders and UI)
        self.game_height = self.height - 4
        self.game_width = self.width - 2
        self.start_y = 2
        self.start_x = 1
        
        # Initialize game state
        self.reset_game()
        
        # Set up curses
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(150)  # Game speed (milliseconds)
        
        # Initialize colors if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Snake
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Food
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Score
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Border
        
    def reset_game(self):
        """Reset the game to initial state"""
        # Snake starts in the middle
        start_y = self.game_height // 2
        start_x = self.game_width // 2
        self.snake = [
            Point(start_y, start_x),
            Point(start_y, start_x - 1),
            Point(start_y, start_x - 2)
        ]
        self.direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.place_food()
    
    def place_food(self):
        """Place food at a random location not occupied by snake"""
        while True:
            food_y = random.randint(0, self.game_height - 1)
            food_x = random.randint(0, self.game_width - 1)
            self.food = Point(food_y, food_x)
            
            # Make sure food is not on snake
            if self.food not in self.snake:
                break
    
    def draw_border(self):
        """Draw game border"""
        # Top and bottom borders
        for x in range(self.width):
            self.stdscr.addch(self.start_y - 1, x, '─')
            if self.start_y + self.game_height < self.height:
                self.stdscr.addch(self.start_y + self.game_height, x, '─')
        
        # Side borders
        for y in range(self.start_y, self.start_y + self.game_height):
            self.stdscr.addch(y, self.start_x - 1, '│')
            if self.start_x + self.game_width < self.width:
                self.stdscr.addch(y, self.start_x + self.game_width, '│')
        
        # Corners
        self.stdscr.addch(self.start_y - 1, self.start_x - 1, '┌')
        self.stdscr.addch(self.start_y - 1, self.start_x + self.game_width, '┐')
        self.stdscr.addch(self.start_y + self.game_height, self.start_x - 1, '└')
        self.stdscr.addch(self.start_y + self.game_height, self.start_x + self.game_width, '┘')
    
    def draw_snake(self):
        """Draw the snake"""
        for i, segment in enumerate(self.snake):
            y = self.start_y + segment.y
            x = self.start_x + segment.x
            
            if curses.has_colors():
                self.stdscr.attron(curses.color_pair(1))
            
            # Head is different from body
            if i == 0:
                self.stdscr.addch(y, x, '@')  # Head
            else:
                self.stdscr.addch(y, x, 'O')  # Body
            
            if curses.has_colors():
                self.stdscr.attroff(curses.color_pair(1))
    
    def draw_food(self):
        """Draw the food"""
        y = self.start_y + self.food.y
        x = self.start_x + self.food.x
        
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(2))
        
        self.stdscr.addch(y, x, '*')
        
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(2))
    
    def draw_ui(self):
        """Draw UI elements (score, instructions)"""
        # Score
        score_text = f"Score: {self.score}"
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(0, 0, score_text)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(3))
        
        # Instructions
        instructions = "Arrow Keys/WASD: Move | Q: Quit"
        if len(instructions) < self.width:
            self.stdscr.addstr(0, self.width - len(instructions), instructions)
        
        # Game over message
        if self.game_over:
            game_over_text = f"GAME OVER! Final Score: {self.score} | Press R to restart or Q to quit"
            if len(game_over_text) < self.width:
                msg_y = self.height // 2
                msg_x = (self.width - len(game_over_text)) // 2
                self.stdscr.attron(curses.A_BOLD)
                self.stdscr.addstr(msg_y, msg_x, game_over_text)
                self.stdscr.attroff(curses.A_BOLD)
    
    def get_input(self):
        """Handle user input"""
        key = self.stdscr.getch()
        
        if key == ord('q') or key == ord('Q'):
            return 'quit'
        
        if self.game_over and (key == ord('r') or key == ord('R')):
            return 'restart'
        
        if self.game_over:
            return None
        
        # Direction changes
        direction_map = {
            curses.KEY_UP: Direction.UP,
            ord('w'): Direction.UP,
            ord('W'): Direction.UP,
            curses.KEY_DOWN: Direction.DOWN,
            ord('s'): Direction.DOWN,
            ord('S'): Direction.DOWN,
            curses.KEY_LEFT: Direction.LEFT,
            ord('a'): Direction.LEFT,
            ord('A'): Direction.LEFT,
            curses.KEY_RIGHT: Direction.RIGHT,
            ord('d'): Direction.RIGHT,
            ord('D'): Direction.RIGHT,
        }
        
        if key in direction_map:
            new_direction = direction_map[key]
            # Prevent reversing into itself
            opposite = {
                Direction.UP: Direction.DOWN,
                Direction.DOWN: Direction.UP,
                Direction.LEFT: Direction.RIGHT,
                Direction.RIGHT: Direction.LEFT
            }
            
            if new_direction != opposite[self.direction]:
                self.direction = new_direction
        
        return None
    
    def update_game(self):
        """Update game state"""
        if self.game_over:
            return
        
        # Calculate new head position
        new_head = self.snake[0] + self.direction
        
        # Check wall collision
        if (new_head.y < 0 or new_head.y >= self.game_height or
            new_head.x < 0 or new_head.x >= self.game_width):
            self.game_over = True
            return
        
        # Check self collision
        if new_head in self.snake:
            self.game_over = True
            return
        
        # Move snake
        self.snake.insert(0, new_head)
        
        # Check food collision
        if new_head == self.food:
            self.score += 10
            self.place_food()
            # Increase speed slightly
            current_timeout = self.stdscr.timeout(-1)  # Get current timeout
            if current_timeout is None:
                current_timeout = 150
            new_timeout = max(50, current_timeout - 2)
            self.stdscr.timeout(new_timeout)
        else:
            # Remove tail if no food eaten
            self.snake.pop()
    
    def draw(self):
        """Draw everything"""
        self.stdscr.clear()
        self.draw_border()
        self.draw_snake()
        self.draw_food()
        self.draw_ui()
        self.stdscr.refresh()
    
    def run(self):
        """Main game loop"""
        while True:
            self.draw()
            
            action = self.get_input()
            
            if action == 'quit':
                break
            elif action == 'restart':
                self.reset_game()
                self.stdscr.timeout(150)  # Reset speed
                continue
            
            self.update_game()


def main(stdscr):
    """Main function that runs the game"""
    # Check terminal size
    height, width = stdscr.getmaxyx()
    if height < 10 or width < 30:
        stdscr.addstr(0, 0, "Terminal too small! Minimum size: 30x10")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.getch()
        return
    
    game = SnakeGame(stdscr)
    game.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("Game interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Make sure your terminal supports curses and has sufficient size.")
