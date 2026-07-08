import discord
from discord import app_commands
import asyncio
import os
import cv2
from PIL import Image
import time

# =================== НАСТРОЙКИ ===================
CLIP_FRAMES = 6571          # общее число кадров в видео (можно уточнить)
WIDTH = 60                  # ширина ASCII-арта
TIMEOUT = 0.07              # задержка между кадрами (подберите под своё видео)
# ================================================

ASCII_CHARS = ['⠀','⠄','⠆','⠖','⠶','⡶','⣩','⣪','⣫','⣾','⣿']

def resize(image, new_width=WIDTH):
    old_width, old_height = image.size
    aspect_ratio = old_height / old_width
    new_height = int((aspect_ratio * new_width) / 2)
    return image.resize((new_width, new_height))

def grayscalify(image):
    return image.convert('L')

def modify(image, buckets=25):
    pixels = list(image.getdata())
    return ''.join(ASCII_CHARS[p // buckets] for p in pixels)

def image_to_ascii(image_path):
    try:
        img = Image.open(image_path)
    except Exception:
        return None
    img = resize(img)
    img = grayscalify(img)
    ascii_str = modify(img)
    return '\n'.join(ascii_str[i:i+WIDTH] for i in range(0, len(ascii_str), WIDTH))

# ---------- ГЕНЕРАЦИЯ КАДРОВ (если папка пуста) ----------
def generate_frames(video_path="bad_apple.mp4"):
    if not os.path.exists(video_path):
        print(f"❌ Видео {video_path} не найдено!")
        return False

    if not os.path.exists("frames"):
        os.makedirs("frames")

    cap = cv2.VideoCapture(video_path)
    count = 0
    success = True
    generated = 0

    while success:
        success, frame = cap.read()
        if not success:
            break
        if count % 4 == 0:      # берём каждый 4-й кадр
            cv2.imwrite(f"frames/frame{count}.jpg", frame)
            generated += 1
        count += 1

    cap.release()
    print(f"✅ Сгенерировано {generated} кадров в папку frames/")
    return True

# ---------- ЗАГРУЗКА КАДРОВ В ПАМЯТЬ ----------
def load_frames():
    frames = []
    if not os.path.exists("frames"):
        print("❌ Папка frames не найдена. Генерируем кадры...")
        if not generate_frames():
            return []

    # Проверяем, есть ли файлы
    existing = [f for f in os.listdir("frames") if f.endswith(".jpg")]
    if not existing:
        print("❌ В папке frames нет кадров. Генерируем...")
        if not generate_frames():
            return []

    # Загружаем только те, что кратны 4 (как в боте)
    for i in range(0, CLIP_FRAMES, 4):
        path = f"frames/frame{i}.jpg"
        if os.path.exists(path):
            ascii_art = image_to_ascii(path)
            frames.append(ascii_art if ascii_art else "⚠️ Кадр повреждён")
        else:
            frames.append(None)   # чтобы не нарушать индексацию
    return frames

# =================== БОТ ===================
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

frames = []   # будет заполнено при запуске

@bot.event
async def on_ready():
    global frames
    await tree.sync()   # синхронизируем слеш-команды
    print(f"✅ Бот {bot.user} запущен!")
    print("Загрузка кадров...")
    frames = load_frames()
    loaded = sum(1 for f in frames if f is not None)
    print(f"Загружено {loaded} из {len(frames)} кадров.")
    if loaded == 0:
        print("⚠️ Нет кадров! Проверьте видео или папку frames.")

@tree.command(name="badapple", description="Запустить проигрывание Bad Apple")
async def badapple(interaction: discord.Interaction):
    if not frames or all(f is None for f in frames):
        await interaction.response.send_message("❌ Кадры не загружены. Попробуйте перезапустить бота.")
        return

    await interaction.response.send_message("▶️ Воспроизведение началось!")

    old_time = time.time()
    i = 0
    total_frames = len(frames)

    while i < total_frames:
        frame_text = frames[int(i)]
        if frame_text is not None:
            try:
                await interaction.channel.send(frame_text[:2000])  # Discord лимит 2000 символов
            except Exception as e:
                print(f"Ошибка отправки: {e}")
                # Если кадр слишком длинный, обрезаем или пропускаем
        else:
            # Если кадр не загружен – пропускаем
            pass

        # Ждём нужное время
        await asyncio.sleep(TIMEOUT)
        i += 1
        if i >= total_frames:
            break

    await interaction.channel.send("✅ Воспроизведение завершено!")

# Для обратной совместимости – оставляем префиксную команду !badapple (по желанию)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.startswith('!badapple'):
        # Просто перенаправляем на слеш-команду (но это не обязательно)
        await message.channel.send("Используйте команду `/badapple`")
    # Не забываем обработать другие команды, если они появятся

# =================== ЗАПУСК ===================
if __name__ == "__main__":
    # Вставьте сюда свой токен (или храните в переменной окружения)
    TOKEN = "ВАШ_ТОКЕН"
    bot.run(TOKEN)