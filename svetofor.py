#!!!65-72, 199-210, 353-355, 606-634 изменения в коде, убрал абсолютные ссылки на файлы.!!!

import tkinter as tk
from tkinter import simpledialog, messagebox, PhotoImage
import time
from PIL import Image, ImageTk
import random
# Заглушка для звука (чтобы не ломать вызовы)
class DummySound:
    def play(self, *args, **kwargs): pass
    def stop(self): pass

sound = DummySound()
#import pygame  # Добавляем импорт pygame для работы со звуком

# Инициализация pygame для работы со звуком
#pygame.mixer.init()

# Загрузка звукового файла
#sound = pygame.mixer.Sound("sound.mp3")
#sound.set_volume(0.1)  # Устанавливаем уровень громкости на 30%

# Создаем главное окно
root = tk.Tk()
root.title("Симуляция светофора")

# Устанавливаем окно на полный экран
root.state('zoomed')
root.resizable(False, False)  # Запрещаем изменение размера окна

# Основная рамка для размещения всех элементов
main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

# Создаем панель меню слева
menu_frame = tk.Frame(main_frame, bg="lightgrey", width=200)
menu_frame.pack(side="left", fill="y")

# Переменные для таймера и состояния светофора
pedestrian_light_state = "red"
driver_light_state = "green"
timer_value = 0
timer_text_id = None
waiting_for_green = False
timer_running = False
green_duration = 25
red_duration = 20
simulation_started = False
last_update_time = 0

# Переменные для машин
cars = []
car_images = []
car_speed = 21  # пикселей за кадр
car_spawn_interval = 1  # секунды между появлением новых машин
last_car_spawn_time = 0

# Переменные для пешеходов
pedestrians = []
pedestrian_spawn_interval = 5  # секунды между появлением новых пешеходов
last_pedestrian_spawn_time = 0
max_pedestrians = 7  # Максимальное количество пешеходов

# Загрузка изображений машин
car_images = []
for i in range(1, 5):
    image = Image.open(f"assets/cars/car{i}.png")
    image = image.resize((200, 100), Image.LANCZOS)
    car_images.append(ImageTk.PhotoImage(image))
    flipped_image = image.transpose(Image.FLIP_LEFT_RIGHT)
    car_images.append(ImageTk.PhotoImage(flipped_image))


class Car:
    def __init__(self, canvas, x, y, direction, image):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.direction = direction
        self.image = image
        self.id = canvas.create_image(x, y, image=image, anchor="nw", tags="car")
        self.stopped = False

    def move(self):
        if not self.stopped:
            if self.direction == "left":
                self.x -= car_speed
            else:
                self.x += car_speed
            self.canvas.move(self.id, -car_speed if self.direction == "left" else car_speed, 0)

    def stop(self):
        self.stopped = True

    def resume(self):
        self.stopped = False

    def is_at_stop_line(self):
        canvas_width = self.canvas.winfo_width()
        if self.direction == "left":
            stop_line_x = canvas_width // 2 + 225  # Изменено положение стоп-линии для верхней полосы
            return self.x <= stop_line_x
        else:  # direction == "right"
            stop_line_x = canvas_width // 2 - 170  # Изменено положение стоп-линии для нижней полосы
            return self.x + 250 >= stop_line_x

    def is_past_stop_line(self):
        canvas_width = self.canvas.winfo_width()
        if self.direction == "left":
            stop_line_x = canvas_width // 2 + 180  # Изменено положение стоп-линии для верхней полосы
            return self.x + 250 < stop_line_x
        else:  # direction == "right"
            stop_line_x = canvas_width // 2 - 180  # Изменено положение стоп-линии для нижней полосы
            return self.x > stop_line_x

    def is_off_screen(self):
        canvas_width = self.canvas.winfo_width()
        return self.x + 250 < 0 or self.x > canvas_width

    def is_on_crosswalk(self):
        canvas_width = self.canvas.winfo_width()
        crosswalk_start = canvas_width // 2 - 130
        crosswalk_end = canvas_width // 2 + 150
        return crosswalk_start <= self.x <= crosswalk_end or crosswalk_start <= self.x + 250 <= crosswalk_end

    def is_near_pedestrian(self, pedestrians):
        for pedestrian in pedestrians:
            if self.direction == "left":
                if (self.x - pedestrian.x < 100 and self.x > pedestrian.x) and abs(self.y - pedestrian.y) < 50:
                    return True
            else:
                if (pedestrian.x - (self.x + 250) < 100 and self.x < pedestrian.x) and abs(self.y - pedestrian.y) < 50:
                    return True
        return False


class Pedestrian:
    def __init__(self, canvas, image_path, x, y):
        self.canvas = canvas
        self.image = PhotoImage(file=image_path)
        self.image = self.image.subsample(10, 10)  # Уменьшаем размер изображений
        self.id = canvas.create_image(x, y, image=self.image, tags="pedestrian")
        self.x = x
        self.y = y
        self.state = "walking_to_crosswalk"
        self.target_y = canvas.winfo_height() // 2 + road_height // 2 + 20  # Целевая позиция чуть ниже перехода
        self.crosswalk_center_y = canvas.winfo_height() // 2
        self.normal_speed = 2
        self.crossing_speed = self.normal_speed
        self.current_speed = self.normal_speed
        self.acceleration = 0.1  # Ускорение для плавного изменения скорости
        self.x_offset = random.uniform(-0.5, 0.5)  # Случайное отклонение по горизонтали
        self.relaxed_speed = self.normal_speed * 0.7  # Скорость для спокойного перехода
        self.hurry_threshold = 5  # Порог времени, когда нужно начинать торопиться

    def move(self):
        global timer_value, pedestrian_light_state
        if self.state == "walking_to_crosswalk":
            if self.y > self.target_y:
                self.current_speed = min(self.current_speed + self.acceleration, self.normal_speed)
                self.canvas.move(self.id, self.x_offset, -self.current_speed)
                self.x += self.x_offset
                self.y -= self.current_speed
            else:
                self.state = "waiting_at_crosswalk"
                self.current_speed = 0
        elif self.state == "waiting_at_crosswalk":
            if pedestrian_light_state == "green" and timer_value > 2:
                self.state = "crossing_road"
                distance_to_cross = road_height
                self.crossing_speed = distance_to_cross / (green_duration * 10)
        elif self.state == "crossing_road":
            if self.y > self.crosswalk_center_y - road_height // 2:
                if timer_value > self.hurry_threshold:
                    # Идем спокойно, если времени достаточно
                    self.current_speed = min(self.current_speed + self.acceleration, self.relaxed_speed)
                elif timer_value <= self.hurry_threshold:
                    # Ускоряемся, когда времени мало
                    self.current_speed = min(self.current_speed + self.acceleration * 2, self.crossing_speed * 1.5)
                self.canvas.move(self.id, 0, -self.current_speed)
                self.y -= self.current_speed
            else:
                self.state = "leaving_scene"
                self.current_speed = self.normal_speed
        elif self.state == "leaving_scene":
            if self.y > 0:
                # Плавно замедляемся после перехода дороги
                target_speed = self.normal_speed * 0.5
                if self.current_speed > target_speed:
                    self.current_speed = max(self.current_speed - self.acceleration, target_speed)
                self.canvas.move(self.id, self.x_offset, -self.current_speed)
                self.x += self.x_offset
                self.y -= self.current_speed
            else:
                self.state = "crossed"


def load_pedestrian_models(canvas):
    global pedestrians, last_pedestrian_spawn_time
    pedestrians = []
    models = [
        "assets/people/model1.png",
        "assets/people/model2.png",
        "assets/people/model3.png"
    ]
    crosswalk_start = canvas.winfo_width() // 2 - 130
    crosswalk_end = canvas.winfo_width() // 2 + 150
    crosswalk_width = crosswalk_end - crosswalk_start
    spacing = crosswalk_width // (len(models) + 1)

    for i, model in enumerate(models, 1):
        x = crosswalk_start + i * spacing
        y = canvas.winfo_height() + 50 + i * 50
        pedestrian = Pedestrian(canvas, model, x, y)
        pedestrians.append(pedestrian)

    last_pedestrian_spawn_time = time.time()

    # Вычисляем расстояние между пешеходами
    spacing = crosswalk_width // (len(models) + 1)

    for i, model in enumerate(models, 1):
        x = crosswalk_start + i * spacing
        y = canvas.winfo_height() + 50 + i * 50  # Начинаем ниже нижней границы экрана, с разной высотой
        pedestrian = Pedestrian(canvas, model, x, y)
        pedestrians.append(pedestrian)

    last_pedestrian_spawn_time = time.time()


# Функции для кнопок
def start_simulation():
    global timer_running, simulation_started, last_update_time, last_car_spawn_time, pedestrians
    if simulation_started:
        return  # Если симуляция уже запущена, ничего не делаем
    timer_running = True
    simulation_started = True
    last_update_time = time.time()
    last_car_spawn_time = time.time()
    load_pedestrian_models(canvas)  # Загружаем пешеходов при старте симуляции
    update_lights()
    move_cars()
    spawn_cars()
    spawn_pedestrians()
    print("Симуляция начата")


def pause_simulation():
    global timer_running
    if not simulation_started:
        messagebox.showinfo("Внимание", "Необходимо начать симуляцию")
        return
    timer_running = False
    print("Симуляция приостановлена")


def resume_simulation():
    global timer_running, last_update_time
    if not simulation_started:
        messagebox.showinfo("Внимание", "Необходимо начать симуляцию")
        return
    if timer_running:
        return  # Если симуляция уже запущена, ничего не делаем
    timer_running = True
    last_update_time = time.time()
    update_lights()
    move_cars()
    spawn_cars()
    spawn_pedestrians()
    print("Симуляция продолжается")


def stop_simulation():
    global timer_running, pedestrian_light_state, driver_light_state, timer_value, waiting_for_green, simulation_started, cars, pedestrians
    timer_running = False
    simulation_started = False
    pedestrian_light_state = "red"
    driver_light_state = "green"
    timer_value = 0
    waiting_for_green = False
    update_lights()
    for car in cars:
        canvas.delete(car.id)
    cars = []
    for pedestrian in pedestrians:
        canvas.delete(pedestrian.id)
    pedestrians = []
    sound.stop()  # Останавливаем звук при завершении симуляции
    print("Симуляция завершена")


def open_settings():
    global green_duration, red_duration
    settings_window = tk.Toplevel(root)
    settings_window.title("Настройки")

    tk.Label(settings_window, text="Длительность зеленого сигнала (в секундах):").grid(row=0, column=0, padx=5, pady=5)
    green_entry = tk.Entry(settings_window)
    green_entry.insert(0, str(green_duration))
    green_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(settings_window, text="Длительность красного сигнала (в секундах):").grid(row=1, column=0, padx=5, pady=5)
    red_entry = tk.Entry(settings_window)
    red_entry.insert(0, str(red_duration))
    red_entry.grid(row=1, column=1, padx=5, pady=5)

    def save_settings():
        global green_duration, red_duration
        try:
            new_green_duration = int(green_entry.get())
            new_red_duration = int(red_entry.get())
            if new_green_duration <= 0 or new_red_duration <= 0:
                raise ValueError("Значения должны быть положительными")
            green_duration = new_green_duration
            red_duration = new_red_duration
            # Обновляем скорость пешеходов
            for pedestrian in pedestrians:
                if pedestrian.state == "crossing_road":
                    distance_to_cross = road_height
                    pedestrian.speed = distance_to_cross / (green_duration * 10)
            settings_window.destroy()
            messagebox.showinfo("Настройки сохранены",
                                "Для применения новых настроек необходимо перезапустить симуляцию")
        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите положительные целые числа (отличные от нуля)")

    tk.Button(settings_window, text="Сохранить", command=save_settings).grid(row=2, column=0, columnspan=2, pady=10)

def exit_application():
    if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
        root.quit()

# Кнопки в меню
buttons = {
    "Начать симуляцию": start_simulation,
    "Приостановить": pause_simulation,
    "Продолжить": resume_simulation,
    "Закончить симуляцию": stop_simulation,
    "Настройки": open_settings,
    "Выход": exit_application,
}

# Создаем и размещаем кнопки
for btn_text, func in buttons.items():
    button = tk.Button(menu_frame, text=btn_text, command=func, font=("Arial", 12), height=2, width=20)
    button.pack(pady=5)

# Поле для симуляции
canvas = tk.Canvas(main_frame, bg="white")
canvas.pack(side="right", fill="both", expand=True)

# Загрузка фонового изображения
background_image = Image.open("assets/bg/fon.png")
background_photo = ImageTk.PhotoImage(background_image)


# Создаем разметку дороги и перехода
def draw_road():
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # Отображаем фоновое изображение
    canvas.create_image(0, 0, anchor="nw", image=background_photo, tags="background")

    road_y = canvas_height // 2
    global road_height
    road_height = 350
    canvas.create_rectangle(0, road_y - road_height // 2, canvas_width, road_y + road_height // 2, fill="gray",
                            tags="road")
    canvas.create_line(0, road_y, canvas_width, road_y, fill="white", dash=(20, 10), tags="road")


def draw_crosswalk():
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    crosswalk_x = canvas_width // 2 - 130
    crosswalk_width = 280
    crosswalk_start_y = canvas_height // 2 - road_height // 2
    crosswalk_end_y = canvas_height // 2 + road_height // 2

    y = crosswalk_start_y
    while y < crosswalk_end_y:
        canvas.create_rectangle(crosswalk_x, y, crosswalk_x + crosswalk_width, min(y + 30, crosswalk_end_y),
                                fill="yellow", tags="crosswalk")
        y += 30
        if y < crosswalk_end_y:
            canvas.create_rectangle(crosswalk_x, y, crosswalk_x + crosswalk_width, min(y + 30, crosswalk_end_y),
                                    fill="white", tags="crosswalk")
            y += 30

    stop_line_offset = 50
    left_stop_line_x = crosswalk_x - stop_line_offset
    right_stop_line_x = crosswalk_x + crosswalk_width + stop_line_offset
    canvas.create_line(left_stop_line_x, canvas_height // 2, left_stop_line_x, crosswalk_end_y, fill="white",
                       width=5, tags="stop_line")  # Изменено положение левой стоп-линии
    canvas.create_line(right_stop_line_x, crosswalk_start_y, right_stop_line_x, canvas_height // 2, fill="white",
                       width=5, tags="stop_line")  # Изменено положение правой стоп-линии


def start_pedestrian_timer():
    global pedestrian_light_state, timer_value, waiting_for_green, timer_running
    if not simulation_started:
        messagebox.showinfo("Внимание", "Необходимо начать симуляцию")
        return
    if not timer_running:
        messagebox.showinfo("Внимание", "Необходимо продолжить симуляцию или начать заново")
        return
    if pedestrian_light_state == "red" and not waiting_for_green and timer_running:
        waiting_for_green = True
        timer_value = red_duration
        update_lights()


def update_lights():
    global timer_value, pedestrian_light_state, driver_light_state, timer_text_id, waiting_for_green, timer_running, last_update_time
    canvas.delete("pedestrian_light", "driver_light")

    current_time = time.time()
    elapsed_time = current_time - last_update_time
    last_update_time = current_time

    if pedestrian_light_state == "red":
        canvas.create_oval(pedestrian_light_x + 5, pedestrian_light_y + 5, pedestrian_light_x + 40,
                           pedestrian_light_y + 40, fill="red", tags="pedestrian_light")
        if waiting_for_green and timer_running:
            timer_value -= elapsed_time
            if timer_value <= 3:
                driver_light_state = "yellow"
            if timer_value <= 0:
                pedestrian_light_state = "green"
                driver_light_state = "red"
                timer_value = green_duration
                canvas.delete("pedestrian_light")
                canvas.create_oval(pedestrian_light_x + 115, pedestrian_light_y + 5, pedestrian_light_x + 150,
                                   pedestrian_light_y + 40, fill="green", tags="pedestrian_light")
                sound.play(loops=-1)  # Включаем звук при зеленом сигнале светофора
    elif pedestrian_light_state == "green":
        canvas.create_oval(pedestrian_light_x + 115, pedestrian_light_y + 5, pedestrian_light_x + 150,
                           pedestrian_light_y + 40, fill="green", tags="pedestrian_light")
        if timer_running:
            timer_value -= elapsed_time
            if timer_value <= 0:
                pedestrian_light_state = "red"
                driver_light_state = "green"
                timer_value = 0
                waiting_for_green = False
                sound.stop()  # Выключаем звук при красном сигнале светофора

    # Обновляем светофоры для водителей
    draw_driver_lights()

    # Обновляем пешеходов
    for pedestrian in pedestrians:
        if pedestrian_light_state == "green" and pedestrian.y <= pedestrian.target_y:
            pedestrian.waiting = False
        pedestrian.move()
    pedestrians[:] = [p for p in pedestrians if p.state != "crossed"]

    if timer_running or pedestrian_light_state == "green":
        color = "green" if pedestrian_light_state == "green" else "red"
        if timer_text_id is None:
            timer_text_id = canvas.create_text(pedestrian_light_x + 75, pedestrian_light_y + 25,
                                               text=f"{timer_value:.1f}", font=("Arial", 16), fill=color, tags="timer")
        else:
            canvas.itemconfigure(timer_text_id, text=f"{timer_value:.1f}", fill=color)
    else:
        if timer_text_id is not None:
            canvas.itemconfigure(timer_text_id, text=f"{timer_value:.1f}")

    if timer_running:
        canvas.after(100, update_lights)
    else:
        # Сохраняем текущее состояние светофора при паузе
        draw_driver_lights()
        if pedestrian_light_state == "red":
            canvas.create_oval(pedestrian_light_x + 5, pedestrian_light_y + 5, pedestrian_light_x + 40,
                               pedestrian_light_y + 40, fill="red", tags="pedestrian_light")
            canvas.create_oval(pedestrian_light_x + 115, pedestrian_light_y + 5, pedestrian_light_x + 150,
                               pedestrian_light_y + 40, fill="black", tags="pedestrian_light")
        else:
            canvas.create_oval(pedestrian_light_x + 5, pedestrian_light_y + 5, pedestrian_light_x + 40,
                               pedestrian_light_y + 40, fill="black", tags="pedestrian_light")
            canvas.create_oval(pedestrian_light_x + 115, pedestrian_light_y + 5, pedestrian_light_x + 150,
                               pedestrian_light_y + 40, fill="green", tags="pedestrian_light")

    # Устанавливаем порядок слоев
    canvas.tag_raise("traffic_light")
    canvas.tag_raise("timer")
    canvas.tag_raise("pedestrian_light")
    canvas.tag_raise("driver_light")


# Добавляем кнопку для пешеходного светофора
button_frame = tk.Frame(menu_frame)
button_frame.pack(pady=20)

pedestrian_button = tk.Button(button_frame, text="Переключить пешеходный свет", command=start_pedestrian_timer)
pedestrian_button.pack()


# Функция для отрисовки светофоров
def draw_traffic_lights():
    global pedestrian_light_x, pedestrian_light_y, driver_light_x_left, driver_light_x_right, driver_light_y

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    driver_light_y = canvas_height // 2 - 40
    line_y = canvas_height // 2
    driver_light_x_left = canvas_width // 2 - 170
    driver_light_x_right = canvas_width // 2 + 160

    canvas.create_rectangle(driver_light_x_left, driver_light_y, driver_light_x_left + 30, driver_light_y + 90,
                            fill="black", tags="traffic_light")
    canvas.create_rectangle(driver_light_x_right, driver_light_y, driver_light_x_right + 30, driver_light_y + 90,
                            fill="black", tags="traffic_light")

    pedestrian_light_x = canvas_width // 2 - 60
    pedestrian_light_y = line_y - 30
    canvas.create_rectangle(pedestrian_light_x, pedestrian_light_y, pedestrian_light_x + 155, pedestrian_light_y + 45,
                            fill="black", tags="traffic_light")

    # Рисуем световые сигналы для пешеходов
    canvas.create_oval(pedestrian_light_x + 5, pedestrian_light_y + 5, pedestrian_light_x + 40,
                       pedestrian_light_y + 40, fill="red", tags="pedestrian_light")
    canvas.create_oval(pedestrian_light_x + 115, pedestrian_light_y + 5, pedestrian_light_x + 150,
                       pedestrian_light_y + 40, fill="black", tags="pedestrian_light")

    draw_driver_lights()


def draw_driver_lights():
    # Рисуем световые сигналы для водителей
    for x in [driver_light_x_left, driver_light_x_right]:
        canvas.create_oval(x + 5, driver_light_y + 5, x + 25, driver_light_y + 25,
                           fill="red" if driver_light_state == "red" else "black", tags="driver_light")
        canvas.create_oval(x + 5, driver_light_y + 35, x + 25, driver_light_y + 55,
                           fill="yellow" if driver_light_state == "yellow" else "black", tags="driver_light")
        canvas.create_oval(x + 5, driver_light_y + 65, x + 25, driver_light_y + 85,
                           fill="green" if driver_light_state == "green" else "black", tags="driver_light")


# Функция для обновления размеров при изменении размера окна
def update_canvas(event):
    canvas.delete("all")

    # Обновляем размер фонового изображения
    global background_photo
    resized_background = background_image.resize((event.width, event.height), Image.LANCZOS)
    background_photo = ImageTk.PhotoImage(resized_background)

    draw_road()
    draw_crosswalk()
    draw_traffic_lights()
    if simulation_started:
        load_pedestrian_models(canvas)

    # Устанавливаем порядок слоев
    canvas.tag_raise("background")
    canvas.tag_raise("road")
    canvas.tag_raise("stop_line")
    canvas.tag_raise("crosswalk")
    canvas.tag_raise("pedestrian")
    canvas.tag_raise("car")
    canvas.tag_raise("traffic_light")
    canvas.tag_raise("timer")
    canvas.tag_raise("pedestrian_light")
    canvas.tag_raise("driver_light")


# Привязываем функцию обновления к изменению размеров окна
canvas.bind("<Configure>", update_canvas)


def spawn_cars():
    global last_car_spawn_time
    if not simulation_started or not timer_running:
        return

    current_time = time.time()
    if current_time - last_car_spawn_time >= car_spawn_interval:
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        # Спавн машины на верхней полосе (движение влево)
        if len([car for car in cars if car.direction == "left"]) < 3:
            random_car_index = random.randint(0,
                                              len(car_images) // 2 - 1) * 2 + 1  # Выбираем случайную машину для левой полосы
            new_car = Car(canvas, canvas_width, canvas_height // 2 - 125, "left", car_images[random_car_index])
            cars.append(new_car)

        # Спавн машины на нижней полосе (движение вправо)
        if len([car for car in cars if car.direction == "right"]) < 3:
            random_car_index = random.randint(0,
                                              len(car_images) // 2 - 1) * 2  # Выбираем случайную машину для правой полосы
            new_car = Car(canvas, -250, canvas_height // 2 + 50, "right", car_images[random_car_index])
            cars.append(new_car)

        last_car_spawn_time = current_time

    if timer_running:
        canvas.after(1000, spawn_cars)


def spawn_pedestrians():
    global last_pedestrian_spawn_time, pedestrians
    if not simulation_started or not timer_running:
        return

    current_time = time.time()
    if current_time - last_pedestrian_spawn_time >= pedestrian_spawn_interval and len(pedestrians) < max_pedestrians:
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        models = [
            "assets/people/model1.png",
            "assets/people/model2.png",
            "assets/people/model3.png"
        ]
        crosswalk_start = canvas_width // 2 - 130
        crosswalk_end = canvas_width // 2 + 150

        x = random.randint(crosswalk_start, crosswalk_end)
        y = canvas_height + 50

        model = random.choice(models)
        new_pedestrian = Pedestrian(canvas, model, x, y)
        pedestrians.append(new_pedestrian)

        last_pedestrian_spawn_time = current_time

    if timer_running:
        canvas.after(1000, spawn_pedestrians)


def move_cars():
    if not simulation_started or not timer_running:
        return

    for car in cars:
        if not car.is_on_crosswalk():
            if (driver_light_state in ["red",
                                       "yellow"] and car.is_at_stop_line() and not car.is_past_stop_line()) or car.is_near_pedestrian(
                pedestrians):
                car.stop()
            elif driver_light_state == "green" or car.is_past_stop_line():
                car.resume()
        else:
            if car.is_near_pedestrian(pedestrians):
                car.stop()
            else:
                car.resume()

        car.move()

        # Проверка на столкновение с другими машинами
        for other_car in cars:
            if car != other_car and car.direction == other_car.direction:
                if car.direction == "left":
                    if car.x - (other_car.x + 150) < 50 and car.x > other_car.x:
                        car.stop()
                        break
                else:
                    if other_car.x - (car.x + 150) < 50 and car.x < other_car.x:
                        car.stop()
                        break
        else:
            if not car.is_at_stop_line() and not car.is_near_pedestrian(pedestrians):
                if driver_light_state == "green" or car.is_on_crosswalk():
                    car.resume()

    # Удаление машин, выехавших за пределы экрана
    cars[:] = [car for car in cars if not car.is_off_screen()]

    if timer_running:
        canvas.after(50, move_cars)

# Рисуем все элементы
draw_road()
draw_crosswalk()
draw_traffic_lights()

# Запускаем основной цикл приложения
root.mainloop()
