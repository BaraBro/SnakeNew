#!/usr/bin/env python3
"""
Современная Змейка для терминала
Продвинутая версия с главным меню, настройками, плавной анимацией и улучшенной графикой.

Автор: AI Assistant
Версия: 2.0
"""

import curses
import random
import time
import json
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    SETTINGS = "settings"
    HIGH_SCORES = "high_scores"


@dataclass
class Point:
    y: int
    x: int
    
    def __add__(self, direction: Direction):
        dy, dx = direction.value
        return Point(self.y + dy, self.x + dx)
    
    def __eq__(self, other):
        return self.y == other.y and self.x == other.x


@dataclass
class GameSettings:
    initial_speed: int = 120
    difficulty: str = "Medium"
    show_grid: bool = True
    smooth_animation: bool = True
    sound_effects: bool = False
    theme: str = "Classic"
    field_size: str = "Medium"
    timer_mode: bool = True
    
    def to_dict(self):
        return {
            'initial_speed': self.initial_speed,
            'difficulty': self.difficulty,
            'show_grid': self.show_grid,
            'smooth_animation': self.smooth_animation,
            'sound_effects': self.sound_effects,
            'theme': self.theme
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class HighScoreManager:
    def __init__(self, filename="snake_scores.json"):
        self.filename = Path.home() / filename
        self.scores = self.load_scores()
    
    def load_scores(self):
        try:
            if self.filename.exists():
                with open(self.filename, 'r') as f:
                    return json.load(f)
            return []
        except:
            return []
    
    def save_scores(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.scores, f, indent=2)
        except:
            pass
    
    def add_score(self, score, name="Player"):
        self.scores.append({
            'score': score,
            'name': name,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:10]  # Топ 10
        self.save_scores()
    
    def get_high_score(self):
        return self.scores[0]['score'] if self.scores else 0


class ModernSnakeGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Настройки дисплея
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.nodelay(True)
        
        # Инициализация цветов
        self.init_colors()
        
        # Состояние игры
        self.state = GameState.MENU
        self.settings = self.load_settings()
        self.high_scores = HighScoreManager()
        self.menu_index = 0
        self.settings_index = 0
        
        # Игровые переменные
        self.game_height = self.height - 6
        self.game_width = self.width - 4
        self.start_y = 3
        self.start_x = 2
        
        # Буферы для плавной анимации
        self.frame_buffer = []
        self.last_frame_time = 0
        
        self.reset_game()
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        config_file = Path.home() / "snake_config.json"
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                return GameSettings.from_dict(data)
        except:
            pass
        return GameSettings()
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        config_file = Path.home() / "snake_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
        except:
            pass
    
    def init_colors(self):
        """Инициализация расширенной цветовой схемы"""
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Основные цвета
            curses.init_pair(1, curses.COLOR_GREEN, -1)    # Змейка
            curses.init_pair(2, curses.COLOR_RED, -1)      # Еда
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Счёт
            curses.init_pair(4, curses.COLOR_CYAN, -1)     # Рамка
            curses.init_pair(5, curses.COLOR_WHITE, -1)    # Текст меню
            curses.init_pair(6, curses.COLOR_BLUE, -1)     # Выбранный пункт
            curses.init_pair(7, curses.COLOR_MAGENTA, -1)  # Акценты
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Инверсия
            
            # Дополнительные стили
            curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Тёмная змейка
            curses.init_pair(11, curses.COLOR_RED, curses.COLOR_BLACK)    # Тёмная еда
    
    def reset_game(self):
        """Сброс игры к начальному состоянию"""
        start_y = self.game_height // 2
        start_x = self.game_width // 2
        self.snake = [
            Point(start_y, start_x),
            Point(start_y, start_x - 1),
            Point(start_y, start_x - 2)
        ]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.paused = False
        self.place_food()
        self.current_speed = self.settings.initial_speed
    
    def place_food(self):
        """Размещение еды в случайном месте"""
        attempts = 0
        while attempts < 100:
            food_y = random.randint(1, self.game_height - 2)
            food_x = random.randint(1, self.game_width - 2)
            self.food = Point(food_y, food_x)
            
            if self.food not in self.snake:
                break
            attempts += 1
    
    def draw_fancy_border(self, y, x, height, width, title=""):
        """Рисование красивой рамки с заголовком"""
        # Углы и линии
        chars = {
            'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
            'h': '═', 'v': '║'
        }
        
        # Верхняя линия
        self.stdscr.addch(y, x, chars['tl'], curses.color_pair(4))
        for i in range(1, width - 1):
            self.stdscr.addch(y, x + i, chars['h'], curses.color_pair(4))
        self.stdscr.addch(y, x + width - 1, chars['tr'], curses.color_pair(4))
        
        # Боковые линии
        for i in range(1, height - 1):
            self.stdscr.addch(y + i, x, chars['v'], curses.color_pair(4))
            self.stdscr.addch(y + i, x + width - 1, chars['v'], curses.color_pair(4))
        
        # Нижняя линия
        self.stdscr.addch(y + height - 1, x, chars['bl'], curses.color_pair(4))
        for i in range(1, width - 1):
            self.stdscr.addch(y + height - 1, x + i, chars['h'], curses.color_pair(4))
        self.stdscr.addch(y + height - 1, x + width - 1, chars['br'], curses.color_pair(4))
        
        # Заголовок
        if title:
            title_x = x + (width - len(title)) // 2
            self.stdscr.addstr(y, title_x - 1, f' {title} ', curses.color_pair(7) | curses.A_BOLD)
    
    def draw_grid(self):
        """Рисование фоновой сетки"""
        if not self.settings.show_grid:
            return
        
        for y in range(self.start_y + 1, self.start_y + self.game_height - 1):
            for x in range(self.start_x + 1, self.start_x + self.game_width - 1):
                if (y + x) % 2 == 0:
                    self.stdscr.addch(y, x, '·', curses.color_pair(4) | curses.A_DIM)
    
    def draw_snake_modern(self):
        """Современное отображение змейки"""
        snake_chars = ['●', '○', '◐', '◑', '◒', '◓']
        
        for i, segment in enumerate(self.snake):
            y = self.start_y + segment.y
            x = self.start_x + segment.x
            
            if i == 0:  # Голова
                char = '◉'
                color = curses.color_pair(1) | curses.A_BOLD
            else:  # Тело
                char_index = min(i - 1, len(snake_chars) - 1)
                char = snake_chars[char_index % len(snake_chars)]
                color = curses.color_pair(1) | (curses.A_DIM if i > 3 else curses.A_NORMAL)
            
            self.stdscr.addch(y, x, char, color)
    
    def draw_food_modern(self):
        """Современное отображение еды"""
        y = self.start_y + self.food.y
        x = self.start_x + self.food.x
        
        # Анимированная еда
        food_chars = ['◆', '◇', '◈', '◉']
        char_index = (int(time.time() * 4) % len(food_chars))
        char = food_chars[char_index]
        
        self.stdscr.addch(y, x, char, curses.color_pair(2) | curses.A_BOLD)
    
    def draw_game_ui(self):
        """Отображение игрового интерфейса"""
        # Счёт
        score_text = f" СЧЁТ: {self.score} "
        self.stdscr.addstr(0, 0, score_text, curses.color_pair(3) | curses.A_BOLD)
        
        # Лучший счёт
        high_score = self.high_scores.get_high_score()
        high_text = f" РЕКОРД: {high_score} "
        self.stdscr.addstr(0, self.width - len(high_text), high_text, curses.color_pair(7))
        
        # Скорость
        speed_text = f" СКОРОСТЬ: {200 - self.current_speed} "
        self.stdscr.addstr(1, 0, speed_text, curses.color_pair(5))
        
        # Управление
        controls = " [WASD/Стрелки] Движение | [P] Пауза | [Q] Выход "
        if len(controls) < self.width:
            self.stdscr.addstr(1, self.width - len(controls), controls, curses.color_pair(5))
        
        # Статус паузы
        if self.paused:
            pause_text = "*** ПАУЗА ***"
            pause_x = (self.width - len(pause_text)) // 2
            self.stdscr.addstr(self.height // 2, pause_x, pause_text, 
                             curses.color_pair(8) | curses.A_BLINK | curses.A_BOLD)
    
    def draw_menu(self):
        """Отображение главного меню"""
        self.stdscr.clear()
        
        # Заголовок игры
        title = "🐍 СОВРЕМЕННАЯ ЗМЕЙКА 🐍"
        subtitle = "v2.0 - Премиум издание"
        
        title_y = self.height // 4
        title_x = (self.width - len(title)) // 2
        subtitle_x = (self.width - len(subtitle)) // 2
        
        self.stdscr.addstr(title_y, title_x, title, curses.color_pair(7) | curses.A_BOLD)
        self.stdscr.addstr(title_y + 1, subtitle_x, subtitle, curses.color_pair(5))
        
        # Пункты меню
        menu_items = [
            "🎮 НАЧАТЬ ИГРУ",
            "⚙️  НАСТРОЙКИ",
            "🏆 ЛУЧШИЕ СЧЕТА",
            "❌ ВЫХОД"
        ]
        
        menu_y = self.height // 2
        for i, item in enumerate(menu_items):
            item_x = (self.width - len(item)) // 2
            color = curses.color_pair(6) | curses.A_BOLD if i == self.menu_index else curses.color_pair(5)
            prefix = "▶ " if i == self.menu_index else "  "
            self.stdscr.addstr(menu_y + i * 2, item_x - 2, prefix + item, color)
        
        # Информация внизу
        info = f"Лучший счёт: {self.high_scores.get_high_score()}"
        info_x = (self.width - len(info)) // 2
        self.stdscr.addstr(self.height - 3, info_x, info, curses.color_pair(3))
    
    def draw_settings(self):
        """Отображение меню настроек"""
        self.stdscr.clear()
        
        # Заголовок
        title = "⚙️ НАСТРОЙКИ"
        title_x = (self.width - len(title)) // 2
        self.stdscr.addstr(2, title_x, title, curses.color_pair(7) | curses.A_BOLD)
        
        # Настройки
        settings_items = [
            f"Сложность: {self.settings.difficulty}",
            f"Показать сетку: {'Да' if self.settings.show_grid else 'Нет'}",
            f"Плавная анимация: {'Да' if self.settings.smooth_animation else 'Нет'}",
            f"Тема: {self.settings.theme}",
            "",
            "НАЗАД"
        ]
        
        start_y = self.height // 3
        for i, item in enumerate(settings_items):
            if not item:
                continue
            item_x = (self.width - len(item)) // 2
            color = curses.color_pair(6) | curses.A_BOLD if i == self.settings_index else curses.color_pair(5)
            prefix = "▶ " if i == self.settings_index else "  "
            self.stdscr.addstr(start_y + i * 2, item_x - 2, prefix + item, color)
        
        # Подсказки
        help_text = "Стрелки: выбор | Enter: изменить | Escape: назад"
        help_x = (self.width - len(help_text)) // 2
        self.stdscr.addstr(self.height - 3, help_x, help_text, curses.color_pair(5))
    
    def draw_high_scores(self):
        """Отображение лучших счетов"""
        self.stdscr.clear()
        
        title = "🏆 ЛУЧШИЕ СЧЕТА"
        title_x = (self.width - len(title)) // 2
        self.stdscr.addstr(2, title_x, title, curses.color_pair(7) | curses.A_BOLD)
        
        scores = self.high_scores.scores
        start_y = 5
        
        if not scores:
            no_scores = "Пока нет рекордов. Сыграйте первую игру!"
            no_scores_x = (self.width - len(no_scores)) // 2
            self.stdscr.addstr(self.height // 2, no_scores_x, no_scores, curses.color_pair(5))
        else:
            for i, score in enumerate(scores[:10]):
                rank = f"{i+1:2d}."
                name = score['name'][:15]
                points = str(score['score'])
                date = score['timestamp'][:10]
                
                line = f"{rank} {name:15} {points:6} {date}"
                line_x = (self.width - len(line)) // 2
                
                color = curses.color_pair(3) | curses.A_BOLD if i == 0 else curses.color_pair(5)
                self.stdscr.addstr(start_y + i, line_x, line, color)
        
        # Назад
        back_text = "Нажмите любую клавишу для возврата"
        back_x = (self.width - len(back_text)) // 2
        self.stdscr.addstr(self.height - 3, back_x, back_text, curses.color_pair(5))
    
    def draw_game_over(self):
        """Экран окончания игры"""
        # Полупрозрачное overlay
        for y in range(self.height // 3, self.height // 3 + 8):
            for x in range(self.width // 4, 3 * self.width // 4):
                try:
                    self.stdscr.addch(y, x, ' ', curses.color_pair(8))
                except:
                    pass
        
        # Game Over
        game_over_text = "ИГРА ОКОНЧЕНА!"
        score_text = f"Ваш счёт: {self.score}"
        high_score = self.high_scores.get_high_score()
        
        center_y = self.height // 2 - 2
        center_x_go = (self.width - len(game_over_text)) // 2
        center_x_score = (self.width - len(score_text)) // 2
        
        self.stdscr.addstr(center_y, center_x_go, game_over_text, 
                         curses.color_pair(2) | curses.A_BOLD | curses.A_BLINK)
        self.stdscr.addstr(center_y + 2, center_x_score, score_text, 
                         curses.color_pair(3) | curses.A_BOLD)
        
        if self.score > high_score:
            new_record = "🎉 НОВЫЙ РЕКОРД! 🎉"
            record_x = (self.width - len(new_record)) // 2
            self.stdscr.addstr(center_y + 4, record_x, new_record, 
                             curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK)
        
        restart_text = "R - играть снова | M - меню | Q - выход"
        restart_x = (self.width - len(restart_text)) // 2
        self.stdscr.addstr(center_y + 6, restart_x, restart_text, curses.color_pair(5))
    
    def handle_menu_input(self, key):
        """Обработка ввода в меню"""
        if key in [curses.KEY_UP, ord('w'), ord('W')]:
            self.menu_index = (self.menu_index - 1) % 4
        elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
            self.menu_index = (self.menu_index + 1) % 4
        elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
            if self.menu_index == 0:  # Начать игру
                self.state = GameState.PLAYING
                self.reset_game()
            elif self.menu_index == 1:  # Настройки
                self.state = GameState.SETTINGS
                self.settings_index = 0
            elif self.menu_index == 2:  # Лучшие счета
                self.state = GameState.HIGH_SCORES
            elif self.menu_index == 3:  # Выход
                return True
        return False
    
    def handle_settings_input(self, key):
        """Обработка ввода в настройках"""
        if key in [curses.KEY_UP, ord('w'), ord('W')]:
            self.settings_index = (self.settings_index - 1) % 6
        elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
            self.settings_index = (self.settings_index + 1) % 6
        elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
            if self.settings_index == 0:  # Сложность
                difficulties = ["Easy", "Medium", "Hard", "Extreme"]
                current = difficulties.index(self.settings.difficulty)
                self.settings.difficulty = difficulties[(current + 1) % len(difficulties)]
                speeds = {"Easy": 150, "Medium": 120, "Hard": 80, "Extreme": 50}
                self.settings.initial_speed = speeds[self.settings.difficulty]
            elif self.settings_index == 1:  # Показать сетку
                self.settings.show_grid = not self.settings.show_grid
            elif self.settings_index == 2:  # Плавная анимация
                self.settings.smooth_animation = not self.settings.smooth_animation
            elif self.settings_index == 3:  # Тема
                themes = ["Classic", "Modern", "Retro"]
                current = themes.index(self.settings.theme)
                self.settings.theme = themes[(current + 1) % len(themes)]
            elif self.settings_index == 5:  # Назад
                self.save_settings()
                self.state = GameState.MENU
        elif key == 27:  # Escape
            self.save_settings()
            self.state = GameState.MENU
    
    def handle_game_input(self, key):
        """Обработка ввода в игре"""
        if key == ord('q') or key == ord('Q'):
            self.state = GameState.MENU
            return
        elif key == ord('p') or key == ord('P'):
            self.paused = not self.paused
            return
        elif key == ord('r') or key == ord('R'):
            if self.game_over:
                self.reset_game()
                return
        elif key == ord('m') or key == ord('M'):
            if self.game_over:
                self.state = GameState.MENU
                return
        
        if self.paused or self.game_over:
            return
        
        # Управление движением
        direction_map = {
            curses.KEY_UP: Direction.UP,
            ord('w'): Direction.UP, ord('W'): Direction.UP,
            curses.KEY_DOWN: Direction.DOWN,
            ord('s'): Direction.DOWN, ord('S'): Direction.DOWN,
            curses.KEY_LEFT: Direction.LEFT,
            ord('a'): Direction.LEFT, ord('A'): Direction.LEFT,
            curses.KEY_RIGHT: Direction.RIGHT,
            ord('d'): Direction.RIGHT, ord('D'): Direction.RIGHT,
        }
        
        if key in direction_map:
            new_direction = direction_map[key]
            opposite = {
                Direction.UP: Direction.DOWN,
                Direction.DOWN: Direction.UP,
                Direction.LEFT: Direction.RIGHT,
                Direction.RIGHT: Direction.LEFT
            }
            
            if new_direction != opposite[self.direction]:
                self.next_direction = new_direction
    
    def update_game(self):
        """Обновление состояния игры"""
        if self.game_over or self.paused:
            return
        
        # Плавное изменение направления
        self.direction = self.next_direction
        
        # Расчёт новой позиции головы
        new_head = self.snake[0] + self.direction
        
        # Проверка столкновений со стенами
        if (new_head.y < 1 or new_head.y >= self.game_height - 1 or
            new_head.x < 1 or new_head.x >= self.game_width - 1):
            self.game_over = True
            self.high_scores.add_score(self.score)
            return
        
        # Проверка столкновения с собой
        if new_head in self.snake:
            self.game_over = True
            self.high_scores.add_score(self.score)
            return
        
        # Перемещение змейки
        self.snake.insert(0, new_head)
        
        # Проверка поедания еды
        if new_head == self.food:
            self.score += 10
            self.place_food()
            # Увеличение скорости
            self.current_speed = max(30, self.current_speed - 3)
        else:
            self.snake.pop()
    
    def run(self):
        """Основной игровой цикл"""
        while True:
            current_time = time.time()
            
            # Получение ввода
            key = self.stdscr.getch()
            
            # Обработка ввода в зависимости от состояния
            if self.state == GameState.MENU:
                if self.handle_menu_input(key):
                    break
                self.draw_menu()
                
            elif self.state == GameState.SETTINGS:
                self.handle_settings_input(key)
                self.draw_settings()
                
            elif self.state == GameState.HIGH_SCORES:
                if key != -1:  # Любая клавиша
                    self.state = GameState.MENU
                self.draw_high_scores()
                
            elif self.state == GameState.PLAYING:
                self.handle_game_input(key)
                
                # Обновление игры с контролем FPS
                if current_time - self.last_frame_time >= self.current_speed / 1000.0:
                    self.update_game()
                    self.last_frame_time = current_time
                
                # Отрисовка игры
                self.stdscr.clear()
                self.draw_fancy_border(self.start_y - 1, self.start_x - 1, 
                                     self.game_height + 2, self.game_width + 2, "SNAKE GAME")
                
                if self.settings.show_grid:
                    self.draw_grid()
                
                self.draw_snake_modern()
                self.draw_food_modern()
                self.draw_game_ui()
                
                if self.game_over:
                    self.draw_game_over()
            
            # Обновление экрана
            try:
                self.stdscr.refresh()
            except:
                pass
            
            # Контроль FPS для плавности
            if self.settings.smooth_animation:
                time.sleep(0.016)  # ~60 FPS


def main(stdscr):
    """Главная функция"""
    # Проверка размера терминала
    height, width = stdscr.getmaxyx()
    if height < 20 or width < 60:
        stdscr.addstr(0, 0, "Терминал слишком мал!")
        stdscr.addstr(1, 0, "Минимальный размер: 60x20")
        stdscr.addstr(2, 0, "Нажмите любую клавишу...")
        stdscr.getch()
        return
    
    game = ModernSnakeGame(stdscr)
    game.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nИгра прервана пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        print("Убедитесь, что терминал поддерживает curses и имеет достаточный размер.")
