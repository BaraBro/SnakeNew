# 🐍 Перенос Змейки на Android

## Обзор архитектуры

Игра разработана с использованием паттерна **MVP (Model-View-Presenter)**, что позволяет легко адаптировать её под разные платформы:

- **Model** (`core/game_engine.py`) - Бизнес-логика игры
- **View** - Реализации для разных платформ (Terminal, Android, Web)
- **Presenter** - Связующее звено между Model и View

## Рекомендуемая технология: Kivy

**Kivy** - это кроссплатформенный Python-фреймворк, идеально подходящий для создания мобильных игр.

### Преимущества Kivy:
- ✅ Нативная поддержка Android
- ✅ Сенсорное управление
- ✅ GPU-ускоренная графика
- ✅ Возможность публикации в Google Play
- ✅ Поддержка звуков, вибрации, уведомлений

## Установка и настройка

### 1. Установка Kivy

```bash
# Установка Kivy (экранирование для zsh)
pip3 install 'kivy[base,media]'

# Для разработки под Android
pip3 install buildozer
```

### 2. Установка Android SDK

```bash
# Установка Java Development Kit
brew install openjdk@11

# Android SDK через Android Studio или командную строку
brew install android-sdk
```

### 3. Настройка Buildozer

```bash
# Инициализация проекта
buildozer init

# Первая сборка (займёт много времени)
buildozer android debug
```

## Структура Android-приложения

```
android/
├── main.py                 # Точка входа Kivy-приложения
├── renderer_android.py     # Android-специфичный рендерер
├── input_android.py        # Обработка сенсорного ввода
├── buildozer.spec          # Конфигурация сборки
├── assets/                 # Ресурсы приложения
│   ├── sounds/            # Звуковые эффекты
│   ├── images/            # Иконки и спрайты
│   └── fonts/             # Шрифты
└── layouts/               # KV-файлы интерфейса
```

## Этапы портирования

### Этап 1: Создание Android-рендерера

```python
# android/renderer_android.py
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Ellipse, Color
from core.game_engine import GameRenderer, Point

class AndroidRenderer(GameRenderer, Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_graphics)
    
    def draw_game_field(self, snake, food, field_width, field_height):
        with self.canvas:
            # Очистка
            self.canvas.clear()
            
            # Рисование змейки
            Color(0, 1, 0)  # Зелёный
            for segment in snake:
                x = segment.x * self.cell_size + self.offset_x
                y = segment.y * self.cell_size + self.offset_y
                Rectangle(pos=(x, y), size=(self.cell_size, self.cell_size))
            
            # Рисование еды
            Color(1, 0, 0)  # Красный
            food_x = food.x * self.cell_size + self.offset_x
            food_y = food.y * self.cell_size + self.offset_y
            Ellipse(pos=(food_x, food_y), size=(self.cell_size, self.cell_size))
```

### Этап 2: Сенсорное управление

```python
# android/input_android.py
from kivy.uix.widget import Widget
from core.game_engine import Direction, InputHandler

class AndroidInputHandler(InputHandler, Widget):
    def __init__(self, game_engine, **kwargs):
        super().__init__(**kwargs)
        self.game_engine = game_engine
        self.touch_start = None
    
    def on_touch_down(self, touch):
        self.touch_start = touch.pos
        return True
    
    def on_touch_up(self, touch):
        if not self.touch_start:
            return False
            
        dx = touch.pos[0] - self.touch_start[0]
        dy = touch.pos[1] - self.touch_start[1]
        
        # Определение направления свайпа
        if abs(dx) > abs(dy):
            direction = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            direction = Direction.UP if dy > 0 else Direction.DOWN
            
        self.game_engine.handle_direction_input(direction)
        return True
```

### Этап 3: Главное Android-приложение

```python
# android/main.py
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from core.game_engine import SnakeGameEngine, DataManager
from renderer_android import AndroidRenderer
from input_android import AndroidInputHandler

class SnakeGameApp(App):
    def build(self):
        # Создание основных компонентов
        self.data_manager = DataManager("/data/data/com.snake.premium/files")
        self.renderer = AndroidRenderer()
        self.input_handler = AndroidInputHandler(None)
        
        # Создание игрового движка
        self.game_engine = SnakeGameEngine(
            self.renderer, 
            self.input_handler, 
            self.data_manager
        )
        
        self.input_handler.game_engine = self.game_engine
        
        # Настройка игрового цикла
        Clock.schedule_interval(self.update_game, 1.0 / 60.0)
        
        # Создание интерфейса
        layout = FloatLayout()
        layout.add_widget(self.renderer)
        layout.add_widget(self.input_handler)
        
        return layout
    
    def update_game(self, dt):
        self.game_engine.run_frame()

if __name__ == '__main__':
    SnakeGameApp().run()
```

## Настройка buildozer.spec

```ini
[app]
title = Premium Snake Game
package.name = premiumsnake
package.domain = com.snake.premium

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,mp3,wav

version = 1.0
requirements = python3,kivy,pyjnius,android

[android]
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,VIBRATE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31
android.gradle_dependencies = com.google.android.gms:play-services-games:23.1.0
```

## Оптимизация для мобильных устройств

### Адаптивный интерфейс
```python
def calculate_optimal_sizes(self, window_width, window_height):
    # Размеры ячеек в зависимости от размера экрана
    cell_size = min(window_width, window_height) // 25
    
    # Отступы для центрирования
    field_pixel_width = self.field_width * cell_size
    field_pixel_height = self.field_height * cell_size
    
    self.offset_x = (window_width - field_pixel_width) // 2
    self.offset_y = (window_height - field_pixel_height) // 2
```

### Тактильная обратная связь
```python
def on_food_eaten(self):
    # Вибрация при поедании еды
    if self.settings.vibration:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        
        @run_on_ui_thread
        def vibrate():
            Context = autoclass('android.content.Context')
            Vibrator = autoclass('android.os.Vibrator')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
            vibrator.vibrate(100)  # 100ms вибрация
        
        vibrate()
```

## Звуковые эффекты

```python
from kivy.core.audio import SoundLoader

class SoundManager:
    def __init__(self):
        self.sounds = {
            'eat': SoundLoader.load('assets/sounds/eat.wav'),
            'game_over': SoundLoader.load('assets/sounds/game_over.wav'),
            'menu_click': SoundLoader.load('assets/sounds/click.wav')
        }
    
    def play(self, sound_name):
        if sound_name in self.sounds and self.sounds[sound_name]:
            self.sounds[sound_name].play()
```

## Монетизация и публикация

### Возможности монетизации:
1. **Реклама** - Google AdMob
2. **In-App покупки** - премиум темы, убрать рекламу
3. **Платная версия** - расширенные функции

### Интеграция Google Play Services:
```python
# Достижения и таблицы лидеров
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass
    
    class PlayGamesManager:
        def submit_score(self, score):
            # Отправка результата в Google Play Games
            pass
        
        def unlock_achievement(self, achievement_id):
            # Разблокировка достижения
            pass
```

## Команды для сборки и публикации

```bash
# Отладочная сборка
buildozer android debug

# Релизная сборка
buildozer android release

# Установка на подключённое устройство
adb install bin/premiumsnake-1.0-arm64-v8a-debug.apk

# Подпись APK для Google Play
jarsigner -keystore my-release-key.keystore bin/premiumsnake-release.apk alias_name
zipalign -v 4 bin/premiumsnake-release.apk bin/premiumsnake-release-aligned.apk
```

## Тестирование

### Тестирование на эмуляторе:
```bash
# Создание эмулятора
avdmanager create avd -n test_device -k "system-images;android-31;google_apis;x86_64"

# Запуск эмулятора
emulator -avd test_device
```

### Тестирование производительности:
- Мониторинг FPS
- Проверка расхода батареи
- Тестирование на разных размерах экранов
- Тестирование сенсорного управления

## Дальнейшее развитие

### Возможные улучшения для Android:
1. **Мультиплеер** через Google Play Games
2. **Облачные сохранения** 
3. **Различные режимы игры**
4. **Система достижений**
5. **Еженедельные турниры**
6. **Социальные функции** (поделиться результатом)

Этот план поможет вам успешно перенести терминальную змейку на Android и подготовить её к публикации в Google Play Store.
