#!/usr/bin/env python3
"""
🐍 ПРЕМИУМ ЗМЕЙКА v3.0 🐍
Полнофункциональная версия с расширенными возможностями и подготовкой под мобильные платформы.

Новые функции:
- Выбор размера поля (Small, Medium, Large, Classic)
- Таймер увеличения скорости
- Ввод имени игрока при окончании игры
- Улучшенная система счёта
- Подготовка архитектуры под Android
"""

import curses
import random
import time
import json
import os
import string
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any
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
    NAME_INPUT = "name_input"


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
class FieldSize:
    name: str
    width: int
    height: int
    description: str


# Стандартные размеры полей из классических змеек
FIELD_SIZES = {
    "Small": FieldSize("Small", 20, 15, "Маленькое поле - быстрые игры"),
    "Medium": FieldSize("Medium", 30, 20, "Средний размер - оптимально"),
    "Large": FieldSize("Large", 40, 25, "Большое поле - долгие игры"),
    "Classic": FieldSize("Classic", 25, 18, "Классический размер Nokia")
}


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
    auto_speed_increase: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Фильтруем только известные поля
        known_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


@dataclass 
class GameSession:
    """Данные игровой сессии для аналитики"""
    start_time: float
    end_time: float = 0
    score: int = 0
    foods_eaten: int = 0
    max_length: int = 3
    field_size: str = "Medium"
    difficulty: str = "Medium"
    
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HighScoreManager:
    def __init__(self, filename="snake_premium_scores.json"):
        self.filename = Path.home() / filename
        self.scores = self.load_scores()
    
    def load_scores(self) -> List[Dict]:
        try:
            if self.filename.exists():
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Ошибка загрузки счетов: {e}")
            return []
    
    def save_scores(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.scores, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения счетов: {e}")
    
    def add_score(self, score: int, name: str = "Player", session: GameSession = None):
        entry = {
            'score': score,
            'name': name.strip() or "Аноним",
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'field_size': session.field_size if session else "Medium",
            'difficulty': session.difficulty if session else "Medium",
            'duration': session.duration() if session else 0,
            'foods_eaten': session.foods_eaten if session else 0
        }
        
        self.scores.append(entry)
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:20]  # Увеличен топ до 20
        self.save_scores()
    
    def get_high_score(self) -> int:
        return self.scores[0]['score'] if self.scores else 0
    
    def get_scores_by_field(self, field_size: str) -> List[Dict]:
        return [s for s in self.scores if s.get('field_size', 'Medium') == field_size]


class PremiumSnakeGame:
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
        self.calculate_field_dimensions()
        
        # Система ввода имени
        self.player_name = ""
        self.name_cursor = 0
        self.max_name_length = 15
        
        # Игровая сессия и статистика
        self.current_session = None
        self.game_timer = 0
        self.last_speed_increase = 0
        self.foods_eaten = 0
        
        # Буферы для плавной анимации
        self.frame_buffer = []
        self.last_frame_time = 0
        
        self.reset_game()
    
    def calculate_field_dimensions(self):
        """Расчёт размеров игрового поля на основе настроек"""
        field = FIELD_SIZES[self.settings.field_size]
        
        # Адаптируем размеры под размер терминала
        max_width = min(self.width - 6, field.width)
        max_height = min(self.height - 8, field.height)
        
        self.game_width = max(15, max_width)  # Минимум 15
        self.game_height = max(10, max_height)  # Минимум 10
        
        # Центрирование поля
        self.start_x = (self.width - self.game_width) // 2
        self.start_y = (self.height - self.game_height) // 2 + 1
    
    def load_settings(self) -> GameSettings:
        """Загрузка настроек из файла"""
        config_file = Path.home() / "snake_premium_config.json"
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return GameSettings.from_dict(data)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
        return GameSettings()
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        config_file = Path.home() / "snake_premium_config.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
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
            curses.init_pair(9, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Тёмный фон
    
    def reset_game(self):
        """Сброс игры к начальному состоянию"""
        self.calculate_field_dimensions()
        
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
        self.foods_eaten = 0
        self.game_timer = 0
        self.last_speed_increase = 0
        
        self.place_food()
        self.current_speed = self.settings.initial_speed
        
        # Новая игровая сессия
        self.current_session = GameSession(
            start_time=time.time(),
            field_size=self.settings.field_size,
            difficulty=self.settings.difficulty
        )
    
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
        chars = {
            'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
            'h': '═', 'v': '║'
        }
        
        try:
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
        except curses.error:
            pass  # Игнорируем ошибки отрисовки за пределами экрана
    
    def draw_grid(self):
        """Рисование фоновой сетки"""
        if not self.settings.show_grid:
            return
        
        try:
            for y in range(self.start_y + 1, self.start_y + self.game_height - 1):
                for x in range(self.start_x + 1, self.start_x + self.game_width - 1):
                    if (y + x) % 2 == 0:
                        self.stdscr.addch(y, x, '·', curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
    
    def draw_snake_modern(self):
        """Современное отображение змейки"""
        snake_chars = ['●', '○', '◐', '◑', '◒', '◓']
        
        for i, segment in enumerate(self.snake):
            try:
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
            except curses.error:
                pass
    
    def draw_food_modern(self):
        """Современное отображение еды"""
        try:
            y = self.start_y + self.food.y
            x = self.start_x + self.food.x
            
            # Анимированная еда
            food_chars = ['◆', '◇', '◈', '◉']
            char_index = (int(time.time() * 4) % len(food_chars))
            char = food_chars[char_index]
            
            self.stdscr.addch(y, x, char, curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
    
    def draw_game_ui(self):
        """Отображение игрового интерфейса"""
        try:
            # Счёт
            score_text = f" СЧЁТ: {self.score} "
            self.stdscr.addstr(0, 0, score_text, curses.color_pair(3) | curses.A_BOLD)
            
            # Лучший счёт
            high_score = self.high_scores.get_high_score()
            high_text = f" РЕКОРД: {high_score} "
            self.stdscr.addstr(0, max(0, self.width - len(high_text)), high_text, curses.color_pair(7))
            
            # Статистика игры
            foods_text = f" ЕДА: {self.foods_eaten} "
            self.stdscr.addstr(1, 0, foods_text, curses.color_pair(5))
            
            # Таймер и скорость
            if self.settings.timer_mode and self.current_session:
                elapsed = int(self.current_session.duration())
                timer_text = f" ВРЕМЯ: {elapsed//60:02d}:{elapsed%60:02d} "
                speed_text = f" СКОРОСТЬ: {200 - self.current_speed} "
                
                mid_point = self.width // 2
                self.stdscr.addstr(1, mid_point - len(timer_text)//2, timer_text, curses.color_pair(6))
                self.stdscr.addstr(1, max(0, self.width - len(speed_text)), speed_text, curses.color_pair(5))
            
            # Размер поля
            field_info = f" ПОЛЕ: {self.settings.field_size} ({self.game_width}x{self.game_height}) "
            if len(field_info) < self.width - 20:
                self.stdscr.addstr(self.height - 1, 0, field_info, curses.color_pair(4))
            
            # Управление
            controls = " [WASD/Стрелки] | [P] Пауза | [Q] Меню "
            if len(controls) < self.width:
                self.stdscr.addstr(self.height - 1, max(0, self.width - len(controls)), controls, curses.color_pair(5))
            
            # Статус паузы
            if self.paused:
                pause_text = "*** ПАУЗА ***"
                pause_x = (self.width - len(pause_text)) // 2
                self.stdscr.addstr(self.height // 2, pause_x, pause_text, 
                                 curses.color_pair(8) | curses.A_BLINK | curses.A_BOLD)
        except curses.error:
            pass
    
    def draw_menu(self):
        """Отображение главного меню"""
        self.stdscr.clear()
        
        try:
            # Заголовок игры
            title = "🐍 ПРЕМИУМ ЗМЕЙКА v3.0 🐍"
            subtitle = "Расширенное издание с новыми возможностями"
            
            title_y = self.height // 4
            title_x = max(0, (self.width - len(title)) // 2)
            subtitle_x = max(0, (self.width - len(subtitle)) // 2)
            
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
                item_x = max(0, (self.width - len(item)) // 2)
                color = curses.color_pair(6) | curses.A_BOLD if i == self.menu_index else curses.color_pair(5)
                prefix = "▶ " if i == self.menu_index else "  "
                self.stdscr.addstr(menu_y + i * 2, max(0, item_x - 2), prefix + item, color)
            
            # Информация внизу
            info_lines = [
                f"Лучший счёт: {self.high_scores.get_high_score()}",
                f"Размер поля: {self.settings.field_size}",
                f"Сложность: {self.settings.difficulty}"
            ]
            
            for i, info in enumerate(info_lines):
                info_x = max(0, (self.width - len(info)) // 2)
                self.stdscr.addstr(self.height - 5 + i, info_x, info, curses.color_pair(3))
        except curses.error:
            pass
    
    def draw_settings(self):
        """Отображение меню настроек"""
        self.stdscr.clear()
        
        try:
            # Заголовок
            title = "⚙️ НАСТРОЙКИ ИГРЫ"
            title_x = max(0, (self.width - len(title)) // 2)
            self.stdscr.addstr(2, title_x, title, curses.color_pair(7) | curses.A_BOLD)
            
            # Настройки
            settings_items = [
                f"Сложность: {self.settings.difficulty}",
                f"Размер поля: {self.settings.field_size}",
                f"Показать сетку: {'Да' if self.settings.show_grid else 'Нет'}",
                f"Плавная анимация: {'Да' if self.settings.smooth_animation else 'Нет'}",
                f"Режим таймера: {'Да' if self.settings.timer_mode else 'Нет'}",
                f"Авто-ускорение: {'Да' if self.settings.auto_speed_increase else 'Нет'}",
                f"Тема: {self.settings.theme}",
                "",
                "СОХРАНИТЬ И ВЫЙТИ"
            ]
            
            start_y = self.height // 4
            for i, item in enumerate(settings_items):
                if not item:
                    continue
                item_x = max(0, (self.width - len(item)) // 2)
                color = curses.color_pair(6) | curses.A_BOLD if i == self.settings_index else curses.color_pair(5)
                prefix = "▶ " if i == self.settings_index else "  "
                self.stdscr.addstr(start_y + i * 2, max(0, item_x - 2), prefix + item, color)
            
            # Описание текущего выбора
            descriptions = {
                0: "Влияет на начальную скорость игры",
                1: f"Текущий: {FIELD_SIZES[self.settings.field_size].description}",
                2: "Показывает точки для лучшей ориентации",
                3: "Плавность 60 FPS (может замедлить игру)",
                4: "Отображение времени игры",
                5: "Увеличение скорости при поедании еды",
                6: "Визуальное оформление игры"
            }
            
            if self.settings_index in descriptions:
                desc = descriptions[self.settings_index]
                desc_x = max(0, (self.width - len(desc)) // 2)
                self.stdscr.addstr(self.height - 4, desc_x, desc, curses.color_pair(4))
            
            # Подсказки
            help_text = "Стрелки: выбор | Enter: изменить | Escape: выход без сохранения"
            help_x = max(0, (self.width - len(help_text)) // 2)
            self.stdscr.addstr(self.height - 2, help_x, help_text, curses.color_pair(5))
        except curses.error:
            pass
    
    def draw_high_scores(self):
        """Отображение лучших счетов"""
        self.stdscr.clear()
        
        try:
            title = "🏆 ТАБЛИЦА ЛИДЕРОВ"
            title_x = max(0, (self.width - len(title)) // 2)
            self.stdscr.addstr(2, title_x, title, curses.color_pair(7) | curses.A_BOLD)
            
            scores = self.high_scores.scores
            start_y = 5
            
            if not scores:
                no_scores = "Пока нет рекордов. Сыграйте первую игру!"
                no_scores_x = max(0, (self.width - len(no_scores)) // 2)
                self.stdscr.addstr(self.height // 2, no_scores_x, no_scores, curses.color_pair(5))
            else:
                # Заголовок таблицы
                header = f"{'№':2} {'ИМЯ':15} {'СЧЁТ':6} {'ПОЛЕ':8} {'ВРЕМЯ':8} {'ДАТА':10}"
                header_x = max(0, (self.width - len(header)) // 2)
                self.stdscr.addstr(start_y - 1, header_x, header, curses.color_pair(4) | curses.A_BOLD)
                
                # Счета
                for i, score in enumerate(scores[:min(15, len(scores))]):
                    rank = f"{i+1:2d}"
                    name = score['name'][:15]
                    points = str(score['score'])
                    field = score.get('field_size', 'Medium')[:8]
                    duration = int(score.get('duration', 0))
                    duration_str = f"{duration//60:02d}:{duration%60:02d}"
                    date = score['timestamp'][:10]
                    
                    line = f"{rank} {name:15} {points:6} {field:8} {duration_str:8} {date}"
                    line_x = max(0, (self.width - len(line)) // 2)
                    
                    color = curses.color_pair(3) | curses.A_BOLD if i == 0 else curses.color_pair(5)
                    if i < 3:  # Топ 3
                        color |= curses.A_BOLD
                    
                    self.stdscr.addstr(start_y + i, line_x, line, color)
            
            # Статистика
            if scores:
                total_games = len(scores)
                avg_score = sum(s['score'] for s in scores) // total_games
                stats = f"Всего игр: {total_games} | Средний счёт: {avg_score}"
                stats_x = max(0, (self.width - len(stats)) // 2)
                self.stdscr.addstr(self.height - 4, stats_x, stats, curses.color_pair(6))
            
            # Назад
            back_text = "Нажмите любую клавишу для возврата в меню"
            back_x = max(0, (self.width - len(back_text)) // 2)
            self.stdscr.addstr(self.height - 2, back_x, back_text, curses.color_pair(5))
        except curses.error:
            pass
    
    def draw_name_input(self):
        """Экран ввода имени игрока"""
        try:
            # Фон
            for y in range(self.height // 3, self.height // 3 + 10):
                for x in range(self.width // 4, 3 * self.width // 4):
                    self.stdscr.addch(y, x, ' ', curses.color_pair(9))
            
            center_y = self.height // 2 - 2
            
            # Заголовки
            if self.score > self.high_scores.get_high_score():
                title = "🎉 НОВЫЙ РЕКОРД! 🎉"
                title_color = curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK
            else:
                title = "ИГРА ОКОНЧЕНА"
                title_color = curses.color_pair(2) | curses.A_BOLD
            
            title_x = max(0, (self.width - len(title)) // 2)
            self.stdscr.addstr(center_y - 2, title_x, title, title_color)
            
            # Счёт
            score_text = f"Ваш счёт: {self.score}"
            score_x = max(0, (self.width - len(score_text)) // 2)
            self.stdscr.addstr(center_y, score_x, score_text, curses.color_pair(3) | curses.A_BOLD)
            
            # Поле ввода имени
            name_prompt = "Введите ваше имя:"
            prompt_x = max(0, (self.width - len(name_prompt)) // 2)
            self.stdscr.addstr(center_y + 2, prompt_x, name_prompt, curses.color_pair(5))
            
            # Поле ввода
            input_field = f"[{self.player_name:<{self.max_name_length}}]"
            input_x = max(0, (self.width - len(input_field)) // 2)
            self.stdscr.addstr(center_y + 3, input_x, input_field, curses.color_pair(6) | curses.A_BOLD)
            
            # Курсор
            cursor_x = input_x + 1 + len(self.player_name)
            if cursor_x < self.width:
                self.stdscr.addch(center_y + 3, cursor_x, '|', curses.color_pair(7) | curses.A_BLINK)
            
            # Инструкции
            instructions = [
                "Enter - сохранить | Escape - пропустить",
                "Буквы и цифры для ввода | Backspace - удалить"
            ]
            
            for i, instruction in enumerate(instructions):
                instr_x = max(0, (self.width - len(instruction)) // 2)
                self.stdscr.addstr(center_y + 5 + i, instr_x, instruction, curses.color_pair(5))
                
        except curses.error:
            pass
    
    def draw_game_over(self):
        """Экран окончания игры (устарел, заменён на draw_name_input)"""
        self.draw_name_input()
    
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
        max_settings = 8  # Количество настроек + кнопка выхода
        
        if key in [curses.KEY_UP, ord('w'), ord('W')]:
            self.settings_index = (self.settings_index - 1) % max_settings
        elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
            self.settings_index = (self.settings_index + 1) % max_settings
        elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
            if self.settings_index == 0:  # Сложность
                difficulties = ["Easy", "Medium", "Hard", "Extreme"]
                current = difficulties.index(self.settings.difficulty)
                self.settings.difficulty = difficulties[(current + 1) % len(difficulties)]
                speeds = {"Easy": 150, "Medium": 120, "Hard": 80, "Extreme": 50}
                self.settings.initial_speed = speeds[self.settings.difficulty]
            elif self.settings_index == 1:  # Размер поля
                sizes = list(FIELD_SIZES.keys())
                current = sizes.index(self.settings.field_size)
                self.settings.field_size = sizes[(current + 1) % len(sizes)]
            elif self.settings_index == 2:  # Показать сетку
                self.settings.show_grid = not self.settings.show_grid
            elif self.settings_index == 3:  # Плавная анимация
                self.settings.smooth_animation = not self.settings.smooth_animation
            elif self.settings_index == 4:  # Режим таймера
                self.settings.timer_mode = not self.settings.timer_mode
            elif self.settings_index == 5:  # Авто-ускорение
                self.settings.auto_speed_increase = not self.settings.auto_speed_increase
            elif self.settings_index == 6:  # Тема
                themes = ["Classic", "Modern", "Retro", "Neon"]
                current = themes.index(self.settings.theme)
                self.settings.theme = themes[(current + 1) % len(themes)]
            elif self.settings_index == 8:  # Выход
                self.save_settings()
                self.state = GameState.MENU
        elif key == 27:  # Escape
            self.state = GameState.MENU  # Выход без сохранения
    
    def handle_name_input(self, key):
        """Обработка ввода имени"""
        if key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
            # Сохранить результат
            final_name = self.player_name.strip() or "Аноним"
            if self.current_session:
                self.current_session.end_time = time.time()
                self.current_session.score = self.score
                self.current_session.foods_eaten = self.foods_eaten
                self.current_session.max_length = len(self.snake)
            
            self.high_scores.add_score(self.score, final_name, self.current_session)
            self.player_name = ""
            self.state = GameState.MENU
            
        elif key == 27:  # Escape - пропустить ввод имени
            if self.current_session:
                self.current_session.end_time = time.time()
                self.current_session.score = self.score
                self.current_session.foods_eaten = self.foods_eaten
                self.current_session.max_length = len(self.snake)
            
            self.high_scores.add_score(self.score, "Аноним", self.current_session)
            self.player_name = ""
            self.state = GameState.MENU
            
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            # Удалить символ
            if self.player_name:
                self.player_name = self.player_name[:-1]
                
        elif key >= 32 and key <= 126:  # Печатные символы
            char = chr(key)
            if len(self.player_name) < self.max_name_length and (char.isalnum() or char in " -_"):
                self.player_name += char
    
    def handle_game_input(self, key):
        """Обработка ввода в игре"""
        if key == ord('q') or key == ord('Q'):
            if self.game_over:
                self.state = GameState.NAME_INPUT
            else:
                self.state = GameState.MENU
            return
        elif key == ord('p') or key == ord('P'):
            if not self.game_over:
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
        
        # Обновление таймера
        current_time = time.time()
        if self.current_session:
            self.game_timer = current_time - self.current_session.start_time
            
            # Автоматическое увеличение скорости по таймеру
            if (self.settings.timer_mode and 
                self.settings.auto_speed_increase and
                self.game_timer - self.last_speed_increase >= 30):  # Каждые 30 секунд
                
                self.current_speed = max(40, self.current_speed - 5)
                self.last_speed_increase = self.game_timer
        
        # Плавное изменение направления
        self.direction = self.next_direction
        
        # Расчёт новой позиции головы
        new_head = self.snake[0] + self.direction
        
        # Проверка столкновений со стенами
        if (new_head.y < 1 or new_head.y >= self.game_height - 1 or
            new_head.x < 1 or new_head.x >= self.game_width - 1):
            self.game_over = True
            self.state = GameState.NAME_INPUT
            return
        
        # Проверка столкновения с собой
        if new_head in self.snake:
            self.game_over = True
            self.state = GameState.NAME_INPUT
            return
        
        # Перемещение змейки
        self.snake.insert(0, new_head)
        
        # Проверка поедания еды
        if new_head == self.food:
            self.score += 10
            self.foods_eaten += 1
            self.place_food()
            
            # Увеличение скорости при поедании (если включено)
            if self.settings.auto_speed_increase:
                self.current_speed = max(30, self.current_speed - 2)
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
                
            elif self.state == GameState.NAME_INPUT:
                self.handle_name_input(key)
                self.draw_name_input()
                
            elif self.state == GameState.PLAYING:
                self.handle_game_input(key)
                
                # Обновление игры с контролем FPS
                if current_time - self.last_frame_time >= self.current_speed / 1000.0:
                    self.update_game()
                    self.last_frame_time = current_time
                
                # Отрисовка игры
                self.stdscr.clear()
                self.draw_fancy_border(self.start_y - 1, self.start_x - 1, 
                                     self.game_height + 2, self.game_width + 2, 
                                     f"SNAKE PREMIUM - {self.settings.field_size.upper()}")
                
                if self.settings.show_grid:
                    self.draw_grid()
                
                self.draw_snake_modern()
                self.draw_food_modern()
                self.draw_game_ui()
            
            # Обновление экрана
            try:
                self.stdscr.refresh()
            except curses.error:
                pass
            
            # Контроль FPS для плавности
            if self.settings.smooth_animation:
                time.sleep(0.016)  # ~60 FPS
            else:
                time.sleep(0.01)  # 100 FPS для быстрого отклика


def main(stdscr):
    """Главная функция"""
    # Проверка размера терминала
    height, width = stdscr.getmaxyx()
    if height < 20 or width < 60:
        stdscr.addstr(0, 0, "Терминал слишком мал!")
        stdscr.addstr(1, 0, "Минимальный размер: 60x20")
        stdscr.addstr(2, 0, "Рекомендуемый размер: 100x30")
        stdscr.addstr(3, 0, "Нажмите любую клавишу...")
        stdscr.getch()
        return
    
    game = PremiumSnakeGame(stdscr)
    game.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nИгра прервана пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
        print("Убедитесь, что терминал поддерживает curses и имеет достаточный размер.")
