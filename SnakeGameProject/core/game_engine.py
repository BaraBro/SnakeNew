#!/usr/bin/env python3
"""
🐍 ИГРОВОЙ ДВИЖОК ЗМЕЙКИ v3.0
Основная логика игры без привязки к конкретной платформе
Может использоваться для терминала, Android, веб и других платформ.
"""

import random
import time
import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod


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
        return isinstance(other, Point) and self.y == other.y and self.x == other.x
    
    def __hash__(self):
        return hash((self.y, self.x))


@dataclass
class FieldSize:
    name: str
    width: int
    height: int
    description: str


# Стандартные размеры полей
FIELD_SIZES = {
    "Small": FieldSize("Small", 15, 10, "Маленькое поле - быстрые игры"),
    "Medium": FieldSize("Medium", 20, 15, "Средний размер - оптимально"), 
    "Large": FieldSize("Large", 30, 20, "Большое поле - долгие игры"),
    "Classic": FieldSize("Classic", 25, 18, "Классический размер Nokia")
}


@dataclass
class GameSettings:
    initial_speed: int = 150
    difficulty: str = "Medium"
    show_grid: bool = True
    smooth_animation: bool = True
    sound_effects: bool = False
    theme: str = "Classic"
    field_size: str = "Medium"
    timer_mode: bool = True
    auto_speed_increase: bool = True
    vibration: bool = True  # Для мобильных устройств
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
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
    moves_made: int = 0
    pauses_count: int = 0
    
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GameRenderer(ABC):
    """Абстрактный интерфейс для рендерера (терминал, Android UI, веб и т.д.)"""
    
    @abstractmethod
    def draw_menu(self, menu_items: List[str], selected_index: int):
        pass
    
    @abstractmethod 
    def draw_game_field(self, snake: List[Point], food: Point, field_width: int, field_height: int):
        pass
    
    @abstractmethod
    def draw_ui(self, score: int, high_score: int, timer: str, speed: int):
        pass
    
    @abstractmethod
    def draw_settings(self, settings_items: List[str], selected_index: int):
        pass
    
    @abstractmethod
    def draw_high_scores(self, scores: List[Dict]):
        pass
    
    @abstractmethod
    def draw_name_input(self, name: str, cursor_pos: int, is_new_record: bool, score: int):
        pass
    
    @abstractmethod
    def show_message(self, message: str, message_type: str = "info"):
        pass


class InputHandler(ABC):
    """Абстрактный интерфейс для обработки ввода"""
    
    @abstractmethod
    def get_input(self) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_direction_input(self) -> Optional[Direction]:
        pass


class DataManager:
    """Управление сохранением/загрузкой данных"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.settings_file = f"{data_dir}/snake_settings.json"
        self.scores_file = f"{data_dir}/snake_scores.json"
    
    def load_settings(self) -> GameSettings:
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return GameSettings.from_dict(data)
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            return GameSettings()
    
    def save_settings(self, settings: GameSettings):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def load_scores(self) -> List[Dict]:
        try:
            with open(self.scores_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            return []
    
    def save_scores(self, scores: List[Dict]):
        try:
            with open(self.scores_file, 'w', encoding='utf-8') as f:
                json.dump(scores, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения счетов: {e}")
    
    def add_score(self, score: int, name: str, session: GameSession) -> List[Dict]:
        scores = self.load_scores()
        
        entry = {
            'score': score,
            'name': name.strip() or "Аноним",
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'field_size': session.field_size,
            'difficulty': session.difficulty,
            'duration': session.duration(),
            'foods_eaten': session.foods_eaten,
            'moves_made': session.moves_made,
            'efficiency': score / max(session.moves_made, 1)  # Очки за ход
        }
        
        scores.append(entry)
        scores.sort(key=lambda x: x['score'], reverse=True)
        scores = scores[:50]  # Топ 50
        
        self.save_scores(scores)
        return scores


class SnakeGameEngine:
    """Основной игровой движок без привязки к платформе"""
    
    def __init__(self, renderer: GameRenderer, input_handler: InputHandler, data_manager: DataManager):
        self.renderer = renderer
        self.input_handler = input_handler
        self.data_manager = data_manager
        
        # Состояние игры
        self.state = GameState.MENU
        self.settings = data_manager.load_settings()
        self.menu_index = 0
        self.settings_index = 0
        
        # Игровые переменные
        self.field_width = 20
        self.field_height = 15
        self.calculate_field_dimensions()
        
        # Игровое состояние
        self.snake: List[Point] = []
        self.food: Point = Point(0, 0)
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.paused = False
        
        # Система ввода имени
        self.player_name = ""
        self.max_name_length = 20
        
        # Статистика и время
        self.current_session: Optional[GameSession] = None
        self.current_speed = 150
        self.last_update_time = 0
        self.last_speed_increase = 0
        self.foods_eaten = 0
        
        # Callbacks для событий
        self.on_food_eaten: Optional[Callable] = None
        self.on_game_over: Optional[Callable] = None
        self.on_score_changed: Optional[Callable] = None
        
    def calculate_field_dimensions(self):
        """Расчёт размеров поля на основе настроек"""
        field_info = FIELD_SIZES[self.settings.field_size]
        self.field_width = field_info.width
        self.field_height = field_info.height
    
    def reset_game(self):
        """Сброс игры к начальному состоянию"""
        self.calculate_field_dimensions()
        
        # Начальная позиция змейки в центре поля
        center_y = self.field_height // 2
        center_x = self.field_width // 2
        
        self.snake = [
            Point(center_y, center_x),
            Point(center_y, center_x - 1), 
            Point(center_y, center_x - 2)
        ]
        
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.paused = False
        self.foods_eaten = 0
        self.current_speed = self.settings.initial_speed
        self.last_speed_increase = 0
        
        self.place_food()
        
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
            food_y = random.randint(0, self.field_height - 1)
            food_x = random.randint(0, self.field_width - 1)
            new_food = Point(food_y, food_x)
            
            if new_food not in self.snake:
                self.food = new_food
                break
            attempts += 1
    
    def get_high_score(self) -> int:
        """Получить лучший результат"""
        scores = self.data_manager.load_scores()
        return scores[0]['score'] if scores else 0
    
    def handle_direction_input(self, new_direction: Direction) -> bool:
        """Обработка ввода направления движения"""
        if self.paused or self.game_over:
            return False
            
        opposite = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        
        if new_direction != opposite[self.direction]:
            self.next_direction = new_direction
            return True
        return False
    
    def handle_menu_navigation(self, action: str) -> bool:
        """Обработка навигации по меню"""
        if action == "up":
            self.menu_index = (self.menu_index - 1) % 4
        elif action == "down":
            self.menu_index = (self.menu_index + 1) % 4
        elif action == "select":
            if self.menu_index == 0:  # Начать игру
                self.state = GameState.PLAYING
                self.reset_game()
            elif self.menu_index == 1:  # Настройки
                self.state = GameState.SETTINGS
                self.settings_index = 0
            elif self.menu_index == 2:  # Рекорды
                self.state = GameState.HIGH_SCORES
            elif self.menu_index == 3:  # Выход
                return True
        return False
    
    def handle_settings_navigation(self, action: str):
        """Обработка навигации по настройкам"""
        max_settings = 9  # Количество настроек + выход
        
        if action == "up":
            self.settings_index = (self.settings_index - 1) % max_settings
        elif action == "down":
            self.settings_index = (self.settings_index + 1) % max_settings
        elif action == "select":
            if self.settings_index == 0:  # Сложность
                difficulties = ["Easy", "Medium", "Hard", "Extreme"]
                current = difficulties.index(self.settings.difficulty)
                self.settings.difficulty = difficulties[(current + 1) % len(difficulties)]
                speeds = {"Easy": 200, "Medium": 150, "Hard": 100, "Extreme": 60}
                self.settings.initial_speed = speeds[self.settings.difficulty]
            elif self.settings_index == 1:  # Размер поля
                sizes = list(FIELD_SIZES.keys())
                current = sizes.index(self.settings.field_size)
                self.settings.field_size = sizes[(current + 1) % len(sizes)]
            elif self.settings_index == 2:  # Сетка
                self.settings.show_grid = not self.settings.show_grid
            elif self.settings_index == 3:  # Анимация
                self.settings.smooth_animation = not self.settings.smooth_animation
            elif self.settings_index == 4:  # Таймер
                self.settings.timer_mode = not self.settings.timer_mode
            elif self.settings_index == 5:  # Авто-ускорение
                self.settings.auto_speed_increase = not self.settings.auto_speed_increase
            elif self.settings_index == 6:  # Звуки
                self.settings.sound_effects = not self.settings.sound_effects
            elif self.settings_index == 7:  # Вибрация
                self.settings.vibration = not self.settings.vibration
            elif self.settings_index == 8:  # Выход
                self.data_manager.save_settings(self.settings)
                self.state = GameState.MENU
        elif action == "back":
            self.state = GameState.MENU
    
    def handle_name_input(self, action: str, char: str = ""):
        """Обработка ввода имени"""
        if action == "char" and char:
            if len(self.player_name) < self.max_name_length and char.isprintable():
                self.player_name += char
        elif action == "backspace":
            if self.player_name:
                self.player_name = self.player_name[:-1]
        elif action == "enter":
            self.finish_game_session()
        elif action == "skip":
            self.player_name = "Аноним"
            self.finish_game_session()
    
    def finish_game_session(self):
        """Завершение игровой сессии и сохранение результатов"""
        if self.current_session:
            self.current_session.end_time = time.time()
            self.current_session.score = self.score
            self.current_session.foods_eaten = self.foods_eaten
            self.current_session.max_length = len(self.snake)
            
            final_name = self.player_name.strip() or "Аноним"
            self.data_manager.add_score(self.score, final_name, self.current_session)
        
        self.player_name = ""
        self.state = GameState.MENU
    
    def toggle_pause(self):
        """Переключение паузы"""
        if self.state == GameState.PLAYING and not self.game_over:
            self.paused = not self.paused
            if self.current_session:
                self.current_session.pauses_count += 1
    
    def update_game_logic(self):
        """Обновление игровой логики"""
        if self.game_over or self.paused:
            return
        
        current_time = time.time()
        
        # Проверка времени для обновления
        if current_time - self.last_update_time < self.current_speed / 1000.0:
            return
        
        self.last_update_time = current_time
        
        # Обновление статистики сессии
        if self.current_session:
            self.current_session.moves_made += 1
            
            # Автоматическое увеличение скорости по времени
            if (self.settings.timer_mode and 
                self.settings.auto_speed_increase and
                current_time - self.current_session.start_time - self.last_speed_increase >= 30):
                
                self.current_speed = max(50, self.current_speed - 10)
                self.last_speed_increase = current_time - self.current_session.start_time
        
        # Обновление направления
        self.direction = self.next_direction
        
        # Новая позиция головы
        new_head = self.snake[0] + self.direction
        
        # Проверка границ
        if (new_head.y < 0 or new_head.y >= self.field_height or
            new_head.x < 0 or new_head.x >= self.field_width):
            self.game_over = True
            self.state = GameState.NAME_INPUT
            if self.on_game_over:
                self.on_game_over()
            return
        
        # Проверка столкновения с собой
        if new_head in self.snake:
            self.game_over = True
            self.state = GameState.NAME_INPUT
            if self.on_game_over:
                self.on_game_over()
            return
        
        # Движение змейки
        self.snake.insert(0, new_head)
        
        # Проверка поедания еды
        if new_head == self.food:
            self.score += 10
            self.foods_eaten += 1
            self.place_food()
            
            # Увеличение скорости при поедании
            if self.settings.auto_speed_increase:
                self.current_speed = max(40, self.current_speed - 3)
            
            if self.on_food_eaten:
                self.on_food_eaten()
            if self.on_score_changed:
                self.on_score_changed(self.score)
        else:
            self.snake.pop()
    
    def get_game_state_data(self) -> Dict[str, Any]:
        """Получить данные состояния игры для рендеринга"""
        timer_str = "00:00"
        if self.current_session:
            elapsed = int(self.current_session.duration())
            timer_str = f"{elapsed//60:02d}:{elapsed%60:02d}"
        
        return {
            'snake': self.snake,
            'food': self.food,
            'score': self.score,
            'high_score': self.get_high_score(),
            'field_width': self.field_width,
            'field_height': self.field_height,
            'timer': timer_str,
            'speed': 200 - self.current_speed,
            'foods_eaten': self.foods_eaten,
            'paused': self.paused,
            'game_over': self.game_over
        }
    
    def get_menu_items(self) -> List[str]:
        """Получить пункты главного меню"""
        return [
            "🎮 НАЧАТЬ ИГРУ",
            "⚙️ НАСТРОЙКИ",
            "🏆 РЕКОРДЫ",
            "❌ ВЫХОД"
        ]
    
    def get_settings_items(self) -> List[str]:
        """Получить пункты меню настроек"""
        return [
            f"Сложность: {self.settings.difficulty}",
            f"Размер поля: {self.settings.field_size}",
            f"Показать сетку: {'Да' if self.settings.show_grid else 'Нет'}",
            f"Плавная анимация: {'Да' if self.settings.smooth_animation else 'Нет'}",
            f"Режим таймера: {'Да' if self.settings.timer_mode else 'Нет'}",
            f"Авто-ускорение: {'Да' if self.settings.auto_speed_increase else 'Нет'}",
            f"Звуковые эффекты: {'Да' if self.settings.sound_effects else 'Нет'}",
            f"Вибрация: {'Да' if self.settings.vibration else 'Нет'}",
            "СОХРАНИТЬ И ВЫЙТИ"
        ]
    
    def run_frame(self):
        """Выполнить один кадр игры"""
        if self.state == GameState.PLAYING:
            self.update_game_logic()
        
        # Рендеринг в зависимости от состояния
        if self.state == GameState.MENU:
            self.renderer.draw_menu(self.get_menu_items(), self.menu_index)
        elif self.state == GameState.SETTINGS:
            self.renderer.draw_settings(self.get_settings_items(), self.settings_index)
        elif self.state == GameState.HIGH_SCORES:
            scores = self.data_manager.load_scores()
            self.renderer.draw_high_scores(scores)
        elif self.state == GameState.NAME_INPUT:
            is_new_record = self.score > self.get_high_score()
            self.renderer.draw_name_input(self.player_name, len(self.player_name), is_new_record, self.score)
        elif self.state == GameState.PLAYING:
            game_data = self.get_game_state_data()
            self.renderer.draw_game_field(game_data['snake'], game_data['food'], 
                                        game_data['field_width'], game_data['field_height'])
            self.renderer.draw_ui(game_data['score'], game_data['high_score'], 
                                game_data['timer'], game_data['speed'])


# Экспорт основных классов для использования в других модулях
__all__ = [
    'SnakeGameEngine', 'GameRenderer', 'InputHandler', 'DataManager',
    'GameState', 'Direction', 'Point', 'GameSettings', 'GameSession',
    'FIELD_SIZES'
]
