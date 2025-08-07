#!/usr/bin/env python3
"""
🐍 Демо Android-приложения змейки на Kivy
Простейший пример для тестирования переноса
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Rectangle, Color, Ellipse
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
import random


class SnakeGameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Игровые переменные
        self.snake = [(5, 5), (4, 5), (3, 5)]  # Список координат змейки
        self.food = (10, 10)
        self.direction = 'right'
        self.cell_size = 20
        self.field_width = 20
        self.field_height = 15
        
        # Привязка к размеру для адаптивности
        self.bind(size=self.update_graphics, pos=self.update_graphics)
        
        # Планировщик обновления игры
        Clock.schedule_interval(self.update_game, 0.5)  # Обновление каждые 0.5 секунд
    
    def update_graphics(self, *args):
        """Обновление графики при изменении размеров"""
        if not self.canvas:
            return
            
        # Расчёт размеров ячеек под размер экрана
        self.cell_size = min(self.width // self.field_width, self.height // self.field_height)
        
        # Отступы для центрирования
        self.offset_x = (self.width - self.field_width * self.cell_size) // 2
        self.offset_y = (self.height - self.field_height * self.cell_size) // 2
        
        self.draw_game()
    
    def draw_game(self):
        """Отрисовка игрового поля"""
        with self.canvas:
            self.canvas.clear()
            
            # Фон игрового поля
            Color(0.1, 0.1, 0.1)  # Тёмно-серый
            Rectangle(pos=(self.offset_x, self.offset_y), 
                     size=(self.field_width * self.cell_size, 
                           self.field_height * self.cell_size))
            
            # Сетка
            Color(0.2, 0.2, 0.2)  # Светло-серый
            for i in range(self.field_width + 1):
                x = self.offset_x + i * self.cell_size
                Rectangle(pos=(x, self.offset_y), size=(1, self.field_height * self.cell_size))
            for j in range(self.field_height + 1):
                y = self.offset_y + j * self.cell_size
                Rectangle(pos=(self.offset_x, y), size=(self.field_width * self.cell_size, 1))
            
            # Змейка
            Color(0, 1, 0)  # Зелёный
            for i, (x, y) in enumerate(self.snake):
                pixel_x = self.offset_x + x * self.cell_size
                pixel_y = self.offset_y + y * self.cell_size
                
                if i == 0:  # Голова
                    Color(0, 0.8, 0)  # Тёмно-зелёный
                else:  # Тело
                    Color(0, 1, 0)  # Зелёный
                
                Rectangle(pos=(pixel_x + 1, pixel_y + 1), 
                         size=(self.cell_size - 2, self.cell_size - 2))
            
            # Еда
            Color(1, 0, 0)  # Красный
            food_x = self.offset_x + self.food[0] * self.cell_size
            food_y = self.offset_y + self.food[1] * self.cell_size
            Ellipse(pos=(food_x + 2, food_y + 2), 
                   size=(self.cell_size - 4, self.cell_size - 4))
    
    def update_game(self, dt):
        """Обновление логики игры"""
        # Получение новой позиции головы
        head_x, head_y = self.snake[0]
        
        if self.direction == 'up':
            head_y += 1
        elif self.direction == 'down':
            head_y -= 1
        elif self.direction == 'left':
            head_x -= 1
        elif self.direction == 'right':
            head_x += 1
        
        # Проверка границ (с переносом через стены для простоты)
        head_x = head_x % self.field_width
        head_y = head_y % self.field_height
        
        new_head = (head_x, head_y)
        
        # Проверка столкновения с собой
        if new_head in self.snake:
            self.reset_game()
            return
        
        # Добавление новой головы
        self.snake.insert(0, new_head)
        
        # Проверка поедания еды
        if new_head == self.food:
            self.spawn_food()
        else:
            self.snake.pop()  # Удаление хвоста
        
        self.draw_game()
    
    def spawn_food(self):
        """Размещение новой еды"""
        while True:
            x = random.randint(0, self.field_width - 1)
            y = random.randint(0, self.field_height - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break
    
    def reset_game(self):
        """Сброс игры"""
        self.snake = [(5, 5), (4, 5), (3, 5)]
        self.direction = 'right'
        self.spawn_food()
    
    def change_direction(self, new_direction):
        """Смена направления с защитой от разворота"""
        opposites = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        if opposites.get(new_direction) != self.direction:
            self.direction = new_direction
    
    def on_touch_down(self, touch):
        """Обработка касаний для управления"""
        if not self.collide_point(*touch.pos):
            return False
        
        # Определение направления на основе позиции касания относительно центра
        center_x = self.center_x
        center_y = self.center_y
        
        dx = touch.pos[0] - center_x
        dy = touch.pos[1] - center_y
        
        if abs(dx) > abs(dy):
            if dx > 0:
                self.change_direction('right')
            else:
                self.change_direction('left')
        else:
            if dy > 0:
                self.change_direction('up')
            else:
                self.change_direction('down')
        
        return True


class SnakeApp(App):
    def build(self):
        # Создание главного layout'a
        main_layout = BoxLayout(orientation='vertical')
        
        # Заголовок
        title = Label(text='🐍 Snake Demo for Android', 
                     size_hint=(1, 0.1),
                     font_size='20sp',
                     color=get_color_from_hex('#00FF00'))
        
        # Игровое поле
        game_widget = SnakeGameWidget()
        
        # Панель управления
        control_panel = BoxLayout(size_hint=(1, 0.15))
        
        # Кнопки управления
        btn_up = Button(text='↑', size_hint=(0.25, 1))
        btn_down = Button(text='↓', size_hint=(0.25, 1))
        btn_left = Button(text='←', size_hint=(0.25, 1))
        btn_right = Button(text='→', size_hint=(0.25, 1))
        
        # Привязка событий кнопок
        btn_up.bind(on_press=lambda x: game_widget.change_direction('up'))
        btn_down.bind(on_press=lambda x: game_widget.change_direction('down'))
        btn_left.bind(on_press=lambda x: game_widget.change_direction('left'))
        btn_right.bind(on_press=lambda x: game_widget.change_direction('right'))
        
        control_panel.add_widget(btn_left)
        control_panel.add_widget(btn_down)
        control_panel.add_widget(btn_up)
        control_panel.add_widget(btn_right)
        
        # Сборка интерфейса
        main_layout.add_widget(title)
        main_layout.add_widget(game_widget)
        main_layout.add_widget(control_panel)
        
        return main_layout


if __name__ == '__main__':
    SnakeApp().run()
