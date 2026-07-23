# Чат: оптимальный кодек для сжатия MPEG-4

> Источник: диалог с другой моделью/ботом.  
> Перенесено в документацию проекта без правок содержания ответов бота.  
> Критический разбор: см. [review-codec-advice.md](./review-codec-advice.md).

---
## USER
какой кодек лучше использовать чтобы сжать mpeg4 еще сильней. чтобы качество осталось но размер уменьшился

## ASSISTANT
Термин «MPEG-4» очень широкий: скорее всего, ваше видео закодировано либо в **H.264 (AVC)**, либо в более старом **DivX/Xvid (MPEG-4 Part 2)**. 

Чтобы уменьшить размер файла, сохранив визуальное качество на том же уровне, вам нужно перекодировать видео в более современные и эффективные кодеки. На сегодняшний день (2026 год) есть два главных лидера по соотношению «качество/размер».

### 1. AV1 (AOMedia Video 1) — Абсолютный лидер по сжатию
Это самый современный открытый кодек. Он обеспечивает **на 20-30% меньший размер** файла по сравнению с H.265 при том же качестве, и на 40-50% меньше, чем старый H.264.
* **Плюсы:** Максимальное сжатие, бесплатен, отлично подходит для стриминга и архивов.
* **Минусы:** Долгое кодирование (требует мощного процессора).
* **Нюанс:** В 2026 году аппаратное декодирование AV1 есть во всех современных смартфонах, видеокартах и Smart TV, но на очень старых телевизорах (старше 5-7 лет) он может не воспроизводиться.

### 2. H.265 (HEVC) — Золотая середина
Если AV1 кодируется слишком долго, H.265 — ваш выбор. Он дает **на 40-50% меньший размер** по сравнению с H.264 при идентичном качестве.
* **Плюсы:** Отличное сжатие, кодируется намного быстрее, чем AV1. Поддерживается практически любыми современными устройствами.
* **Минусы:** Запатентован (но для домашнего использования это не имеет значения).

---

### 🌟 Главный секрет сохранения качества: CRF
Чтобы качество не упало, а размер уменьшился, **никогда не задавайте фиксированный битрейт**. Используйте параметр **CRF (Constant Rate Factor)**. Он заставляет кодек выделять больше битрейта на сложные сцены и меньше на простые.

* **Для H.265 (x265):** Идеальное значение CRF — **от 22 до 26**. (Чем меньше число, тем выше качество и больше размер. 23-24 — невидимая потеря качества).
* **Для AV1:** Идеальное значение CRF — **от 28 до 32**. (Шкала AV1 немного другая, цифры выше).

**Второй секрет: Пресет (Preset)**
Всегда ставьте пресет кодирования на **«Slow» (Медленно)** или **«Slower»**. Чем дольше компьютер будет думать над каждым кадром, тем эффективнее он его сожмет. Файл будет меньше при том же CRF.

---

### Не забудьте про звук!
Часто половину размера видеофайла занимает «тяжелая» аудиодорожка. 
* Перекодируйте звук в **AAC** (битрейт 128-160 kbps) или в **Opus** (96-128 kbps — качество Opus на 128 kbps неотличимо от оригинала, а весит копейки).

---

### В каких программах это сделать?

#### Вариант 1: HandBrake (Самый простой, с интерфейсом)
1. Скачайте [HandBrake](https://handbrake.fr/) (бесплатно).
2. Закиньте ваше видео.
3. Во вкладке **Video** выберите кодек: **H.265 (x265)** или **AV1**.
4. В поле **Quality** выберите **Constant Quality (CRF)** и поставьте `24` (для H.265) или `30` (для AV1).
5. В поле **Encoder Preset** выберите `Slow`.
6. Во вкладке **Audio** выберите кодек `AAC` или `Opus` и битрейт `128`.
7. Жмите **Start Encode**.

#### Вариант 2: FFmpeg (Для продвинутых пользователей / командная строка)
Если вы любите консоль, вот идеальные команды:

**Для H.265 (HEVC):**
```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 24 -preset slow -tag:v hvc1 -c:a aac -b:a 128k output.mp4
```
*(Параметр `-tag:v hvc1` нужен для того, чтобы видео без проблем игралось в браузерах Safari и на устройствах Apple).*

**Для AV1 (максимальное сжатие):**
```bash
ffmpeg -i input.mp4 -c:v libsvtav1 -crf 30 -preset 6 -c:a libopus -b:a 128k output.mkv
```
*(Здесь используется `libsvtav1` — он кодирует AV1 в разы быстрее старых реализаций).*

### Резюме:
1. Если у вас **современный ПК/ТВ/Смартфон** и вам нужно **максимально уменьшить размер** (например, для хранения на диске или отправки) — используйте **AV1** с CRF 30.
2. Если нужна **совместимость** со всеми устройствами и адекватное время перекодирования — используйте **H.265** с CRF 24.
3. Если ваше исходное видео — это древний **DivX/Xvid**, то перекодирование его даже в обычный **H.264** (с CRF 18-20) уже уменьшит размер в 2-3 раза без потери качества.

## USER
напиши скрипт на python.ffmpeg уже установлен. хочу чтобы небольшую часть кодировалось и в H.265 и в AV1  а потом сравнивалось на сколько этот кусок уменьшился и где эффиктивней сжатие.. а потом уже весь файл конвертировался с учетом в какой формат сильней сжалось\ну или оптимальней

## ASSISTANT
Отличная идея! Такой подход (тестовое кодирование фрагмента) называется **бенчмаркингом**, и это самый надежный способ выбрать оптимальный кодек для конкретного видео, так как разные видео (мультики, фильмы, динамичные игры) сжимаются по-разному.

Ниже представлен готовый Python-скрипт. Он делает ровно то, что вы просили:
1. Берет первые 30 секунд видео.
2. Кодирует этот фрагмент в **H.265** и **AV1** с оптимальными настройками.
3. Сравнивает размеры полученных файлов.
4. Выбирает победителя (кто дал меньший размер).
5. Запускает кодирование **полного видео** выбранным кодеком.
6. Удаляет временные тестовые файлы.

### 🐍 Python-скрипт `smart_convert.py`

```python
import os
import sys
import subprocess
import time

# ================= НАСТРОЙКИ =================
SAMPLE_DURATION = 30       # Длительность тестового фрагмента в секундах
H265_CRF = 24              # Качество для H.265 (меньше = лучше качество, больше размер)
AV1_CRF = 30               # Качество для AV1 (шкала отличается, 30 ≈ 24 в H.265)
H265_PRESET = "slow"       # Скорость кодирования H.265 (ultrafast, fast, medium, slow, slower)
AV1_PRESET = "6"           # Скорость кодирования AV1 (0-13, где 0 - максимально медленно/качественно, 13 - быстро)
# =============================================

def format_size(size_bytes):
    """Преобразует байты в читаемый формат (МБ)"""
    return f"{size_bytes / (1024 * 1024):.2f} МБ"

def run_ffmpeg(cmd, description):
    """Запускает FFmpeg и выводит прогресс"""
    print(f"\n▶️ {description}...")
    print(f"Команда: {' '.join(cmd)}")
    
    start_time = time.time()
    # Запускаем процесс, перенаправляем вывод, чтобы видеть прогресс в консоли
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
    
    for line in process.stdout:
        # Фильтруем вывод, чтобы не спамить, показываем только строки с временем (прогресс)
        if "time=" in line:
            print(line.strip())
            
    process.wait()
    
    if process.returncode != 0:
        print(f"❌ Ошибка FFmpeg при выполнении: {description}")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    print(f"✅ Завершено за {elapsed:.1f} сек.")

def main():
    # 1. Получаем путь к файлу
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("📁 Введите путь к видеофайлу (или перетащите его в окно терминала): ").strip().strip('"')

    if not os.path.isfile(input_file):
        print("❌ Файл не найден. Проверьте путь.")
        sys.exit(1)

    base_name = os.path.splitext(input_file)[0]
    
    # Имена временных и итоговых файлов
    sample_h265 = f"{base_name}_sample_h265.mp4"
    sample_av1 = f"{base_name}_sample_av1.mkv"
    
    output_h265 = f"{base_name}_converted_h265.mp4"
    output_av1 = f"{base_name}_converted_av1.mkv"

    print(f"\n🎬 Исходный файл: {os.path.basename(input_file)}")
    print(f"⏱️ Длительность теста: {SAMPLE_DURATION} сек.")
    print("🔄 Начинаю тестовое кодирование фрагментов...")

    # 2. Кодируем тестовый фрагмент H.265
    cmd_h265 = [
        "ffmpeg", "-y", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "libx265", "-crf", str(H265_CRF), "-preset", H265_PRESET,
        "-c:a", "aac", "-b:a", "128k",
        sample_h265
    ]
    run_ffmpeg(cmd_h265, "Кодирование тестового фрагмента в H.265")

    # 3. Кодируем тестовый фрагмент AV1
    cmd_av1 = [
        "ffmpeg", "-y", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "libsvtav1", "-crf", str(AV1_CRF), "-preset", AV1_PRESET,
        "-c:a", "libopus", "-b:a", "128k",
        sample_av1
    ]
    run_ffmpeg(cmd_av1, "Кодирование тестового фрагмента в AV1")

    # 4. Сравниваем размеры
    size_h265 = os.path.getsize(sample_h265)
    size_av1 = os.path.getsize(sample_av1)

    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТА (фрагмент {} сек.):".format(SAMPLE_DURATION))
    print(f"   H.265 (x265): {format_size(size_h265)}")
    print(f"   AV1 (SVT-AV1): {format_size(size_av1)}")
    print("="*50)

    # 5. Выбираем победителя
    if size_av1 < size_h265:
        winner = "AV1"
        winner_file = output_av1
        print(f"🏆 Победитель: AV1 (сжал на {((size_h265 - size_av1) / size_h265 * 100):.1f}% сильнее)")
        full_cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "libsvtav1", "-crf", str(AV1_CRF), "-preset", AV1_PRESET,
            "-c:a", "libopus", "-b:a", "128k",
            winner_file
        ]
    else:
        winner = "H.265"
        winner_file = output_h265
        print(f"🏆 Победитель: H.265 (сжал на {((size_av1 - size_h265) / size_av1 * 100):.1f}% сильнее или равен)")
        full_cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "libx265", "-crf", str(H265_CRF), "-preset", H265_PRESET,
            "-c:a", "aac", "-b:a", "128k",
            winner_file
        ]

    # 6. Запускаем полное кодирование
    print(f"\n🚀 Запускаю полное кодирование всего файла в {winner}...")
    print("⚠️  Это может занять время. Не закрывайте окно.")
    run_ffmpeg(full_cmd, f"Полное кодирование в {winner}")

    # 7. Очистка временных файлов
    print("\n🧹 Удаляю временные тестовые файлы...")
    try:
        os.remove(sample_h265)
        os.remove(sample_av1)
        print("✅ Временные файлы удалены.")
    except Exception as e:
        print(f"⚠️ Не удалось удалить временные файлы: {e}")

    print(f"\n🎉 ГОТОВО! Итоговый файл сохранен как:\n📁 {os.path.abspath(winner_file)}")

if __name__ == "__main__":
    main()
```

---

### 🛠️ Как использовать:

1. Убедитесь, что у вас установлен Python (3.6+).
2. Сохраните код выше в файл с именем `smart_convert.py`.
3. Откройте терминал (командную строку) и запустите скрипт, указав путь к видео:
   ```bash
   python smart_convert.py "C:\Путь\к\вашему\видео.mp4"
   ```
   *(Или просто запустите `python smart_convert.py`, и скрипт сам попросит вас ввести или перетащить файл в окно).*

---

### ⚙️ Что можно настроить (в начале скрипта):

- `SAMPLE_DURATION = 30`: Если видео очень длинное (например, 2 часа), 30 секунд достаточно для репрезентативной выборки. Если видео короткое или вы хотите более точного теста, поставьте `60`.
- `H265_CRF = 24` и `AV1_CRF = 30`: Это баланс качества. Если хотите **максимальное качество** (почти без потерь), измените на `20` и `26` соответственно (файлы будут больше). Если нужно **максимальное сжатие** (для архива), поставьте `28` и `34`.
- `AV1_PRESET = "6"`: Это золотая середина для SVT-AV1. Если у вас мощный процессор и вы хотите выжать еще 5-10% размера, поставьте `"4"` или `"5"` (кодирование будет заметно медленнее).

### 💡 Важные нюансы:
1. **Скорость AV1:** Тестовое кодирование AV1 может занять в 2-4 раза больше времени, чем H.265, даже для 30 секунд. Это нормально, такова плата за супер-сжатие.
2. **Кодек `libsvtav1`:** Скрипт использует `libsvtav1` (SVT-AV1), так как он в разы быстрее старого `libaom-av1` и входит в большинство современных сборок FFmpeg (например, от gyancoder или gyan.dev). Если ваш FFmpeg вдруг выдаст ошибку "Unknown encoder 'libsvtav1'", замените в скрипте `libsvtav1` на `libaom-av1` (но будьте готовы ждать дольше).
3. **Контейнеры:** Скрипт сохраняет H.265 в `.mp4`, а AV1 в `.mkv`. Это сделано намеренно: `.mkv` гарантирует беспроблемную запись AV1 + Opus без дополнительных танцев с бубном и тегами совместимости.

## USER
да забыл что аппаратное ускорение есть cuda карта 4060 Ti Nvidia 16 GB VRAM

## ASSISTANT
Отличное уточнение! **RTX 4060 Ti** — это просто находка для таких задач. В отличие от 30-й серии, в чипах 40-й серии (Ada Lovelace) есть **аппаратный энкодер AV1**. Это значит, что вы можете сжимать видео в AV1 не мучительно долго на процессоре, а за секунды на видеокарте.

### ⚠️ Важный нюанс аппаратного кодирования (NVENC)
Вам нужно понимать разницу между программным (CPU) и аппаратным (GPU) кодированием:
1. **Скорость:** NVENC (аппаратное) кодирует в **10–50 раз быстрее**, чем CPU. Тестовый фрагмент 30 секунд будет готов за 1-2 секунды.
2. **Размер файла:** При одном и том же *визуальном* качестве аппаратный кодек даст файл **на 10-20% больше**, чем программный. Плата за скорость.

Но поскольку у вас 40-я серия, мы будем сравнивать **два аппаратных кодека**: `hevc_nvenc` (H.265) и `av1_nvenc` (AV1). Между ними AV1 почти всегда выиграет по размеру, но мы это проверим скриптом.

---

### 🐍 Обновленный скрипт `smart_convert_nvenc.py`

В NVENC нет параметра `CRF`. Вместо него используется **`-cq` (Constant Quality)** в связке с режимом `-rc vbr`. Чем меньше число `-cq`, тем выше качество и больше размер.

```python
import os
import sys
import subprocess
import time

# ================= НАСТРОЙКИ =================
SAMPLE_DURATION = 30       # Длительность тестового фрагмента в секундах

# Настройки H.265 (hevc_nvenc)
H265_CQ = 28               # Качество (аналог CRF. 28 - отличный баланс)
H265_PRESET = "p6"         # Пресет (p1-p7. p7 - лучшее сжатие, но медленнее. p6 - оптимум)

# Настройки AV1 (av1_nvenc) - Фича RTX 40-й серии!
AV1_CQ = 32                # Качество для AV1 (шкала чуть другая, 32 ≈ 28 в H.265)
AV1_PRESET = "p6"          # Пресет для AV1
# =============================================

def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} МБ"

def run_ffmpeg(cmd, description):
    print(f"\n▶️ {description}...")
    start_time = time.time()
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
    
    for line in process.stdout:
        if "time=" in line:
            print(line.strip(), end='\r') # Перезаписываем строку для чистого прогресса
            
    process.wait()
    print("\n", end="") # Перенос строки после прогресса
    
    if process.returncode != 0:
        print(f"❌ Ошибка FFmpeg. Возможно, ваш FFmpeg не поддерживает NVENC или AV1.")
        print("Убедитесь, что скачан свежий FFmpeg с поддержкой NVENC (например, с gyan.dev).")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    print(f"✅ Завершено за {elapsed:.2f} сек.")

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("📁 Введите путь к видеофайлу: ").strip().strip('"')

    if not os.path.isfile(input_file):
        print("❌ Файл не найден.")
        sys.exit(1)

    base_name = os.path.splitext(input_file)[0]
    
    sample_h265 = f"{base_name}_sample_h265.mp4"
    sample_av1 = f"{base_name}_sample_av1.mkv"
    output_h265 = f"{base_name}_nvenc_h265.mp4"
    output_av1 = f"{base_name}_nvenc_av1.mkv"

    print(f"\n🎬 Исходный файл: {os.path.basename(input_file)}")
    print(f"⚡ Используем аппаратное ускорение NVIDIA NVENC (RTX 4060 Ti)")
    print("🔄 Начинаю тестовое кодирование фрагментов...")

    # 1. Тест H.265 (hevc_nvenc)
    # -hwaccel auto ускоряет декодирование исходника, если оно поддерживается
    # -spatial_aq 1 и -temporal_aq 1 включают адаптивное квантование (сильно улучшает качество)
    cmd_h265 = [
        "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "hevc_nvenc", "-preset", H265_PRESET, "-tune", "hq", 
        "-rc", "vbr", "-cq", str(H265_CQ), "-b:v", "0",
        "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
        "-c:a", "aac", "-b:a", "128k",
        sample_h265
    ]
    run_ffmpeg(cmd_h265, "Тест H.265 (hevc_nvenc)")

    # 2. Тест AV1 (av1_nvenc)
    cmd_av1 = [
        "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "av1_nvenc", "-preset", AV1_PRESET, "-tune", "hq",
        "-rc", "vbr", "-cq", str(AV1_CQ), "-b:v", "0",
        "-spatial_aq", "1", "-temporal_aq", "1",
        "-c:a", "libopus", "-b:a", "128k",
        sample_av1
    ]
    run_ffmpeg(cmd_av1, "Тест AV1 (av1_nvenc)")

    # 3. Сравнение
    size_h265 = os.path.getsize(sample_h265)
    size_av1 = os.path.getsize(sample_av1)

    print("\n" + "="*50)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТА (фрагмент {SAMPLE_DURATION} сек.):")
    print(f"   H.265 (NVENC): {format_size(size_h265)}")
    print(f"   AV1  (NVENC):  {format_size(size_av1)}")
    print("="*50)

    # 4. Выбор победителя
    if size_av1 < size_h265:
        winner = "AV1"
        winner_file = output_av1
        print(f"🏆 Победитель: AV1 (сжал на {((size_h265 - size_av1) / size_h265 * 100):.1f}% сильнее)")
        full_cmd = [
            "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file,
            "-c:v", "av1_nvenc", "-preset", AV1_PRESET, "-tune", "hq",
            "-rc", "vbr", "-cq", str(AV1_CQ), "-b:v", "0",
            "-spatial_aq", "1", "-temporal_aq", "1",
            "-c:a", "libopus", "-b:a", "128k",
            winner_file
        ]
    else:
        winner = "H.265"
        winner_file = output_h265
        print(f"🏆 Победитель: H.265 (сжал на {((size_av1 - size_h265) / size_av1 * 100):.1f}% сильнее или равен)")
        full_cmd = [
            "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file,
            "-c:v", "hevc_nvenc", "-preset", H265_PRESET, "-tune", "hq",
            "-rc", "vbr", "-cq", str(H265_CQ), "-b:v", "0",
            "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
            "-c:a", "aac", "-b:a", "128k",
            winner_file
        ]

    # 5. Полное кодирование
    print(f"\n🚀 Запускаю полное кодирование всего файла в {winner} через NVENC...")
    run_ffmpeg(full_cmd, f"Полное кодирование в {winner}")

    # 6. Очистка
    print("\n🧹 Удаляю временные файлы...")
    try:
        os.remove(sample_h265)
        os.remove(sample_av1)
        print("✅ Временные файлы удалены.")
    except Exception as e:
        print(f"⚠️ Ошибка удаления: {e}")

    print(f"\n🎉 ГОТОВО! Итоговый файл:\n📁 {os.path.abspath(winner_file)}")

if __name__ == "__main__":
    main()
```

---

### 🔍 Что здесь изменено и почему это важно:

1. **Кодеки `hevc_nvenc` и `av1_nvenc`**: Они задействуют физические чипы NVENC и AV1 на вашей RTX 4060 Ti. Процессор (CPU) будет почти не загружен.
2. **Параметр `-cq` вместо `-crf`**: В аппаратном кодировании NVIDIA используется Constant Quality (`-cq`). Значения `28` (для H.265) и `32` (для AV1) дадут отличную картинку без артефактов.
3. **Параметр `-preset p6`**: В NVENC пресеты обозначаются как `p1` (самый быстрый) до `p7` (самый медленный, но с лучшим сжатием). `p6` — это золотая середина для 40-й серии. Если хотите выжать максимум и готовы подождать лишние 10% времени — замените на `p7`.
4. **`-spatial_aq 1` и `-temporal_aq 1`**: Это **адаптивное квантование**. Оно критически важно для NVENC! Без него видеокарта может "мылить" темные сцены и давать "бандинг" (полосы) на градиентах (например, в небе). Эти параметры заставляют карту тратить битрейт умнее.
5. **`-hwaccel auto`**: Ускоряет *чтение и декодирование* исходного файла видеокартой (если исходник в H.264/H.265).
6. **`-profile:v main10`**: Включает 10-битное кодирование для H.265. Это дает более плавные градиенты и чуть лучшее сжатие.

### 💡 Ожидаемые результаты:
- **Скорость:** Фильм длиной 2 часа в 1080p будет перекодирован примерно за **5–15 минут** (вместо 2-4 часов на процессоре).
- **Размер:** AV1 выиграет у H.265 примерно на 20-25% по размеру файла.
- **Загрузка:** Во время кодирования загрузка GPU в диспетчере задач будет около 30-50% (чипы NVENC занимают лишь малую часть кристалла), а CPU будет простаивать. Вы можете спокойно играть или работать за ПК во время кодирования!

## USER
а можеш еще гуй сделать?

## ASSISTANT
Конечно! Сделаю современный графический интерфейс на **CustomTkinter** - это библиотека, которая дает красивый темный вид в стиле современных приложений.

### 📦 Сначала установите библиотеку:

```bash
pip install customtkinter
```

---

### 🐍 Полный код с GUI: `smart_convert_gui.py`

```python
import os
import sys
import subprocess
import time
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# Настройки темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SmartConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Smart Video Converter - H.265 vs AV1 (NVENC)")
        self.geometry("800x700")
        self.resizable(True, True)
        
        self.input_file = None
        self.is_running = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self, 
            text="🎬 Smart Video Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(20, 10))
        
        self.subtitle_label = ctk.CTkLabel(
            self,
            text="Автоматическое сравнение H.265 и AV1 с NVIDIA NVENC",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(pady=(0, 20))
        
        # Фрейм для выбора файла
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(file_frame, text="Исходный файл:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path_var, width=500)
        self.file_entry.pack(side="left", padx=(10, 5), pady=10, fill="x", expand=True)
        
        self.browse_btn = ctk.CTkButton(file_frame, text="Обзор...", command=self.browse_file, width=100)
        self.browse_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Фрейм настроек
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(settings_frame, text="Настройки тестирования:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Длительность теста
        duration_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        duration_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(duration_frame, text="Длительность теста (сек):").pack(side="left")
        self.duration_var = tk.StringVar(value="30")
        self.duration_entry = ctk.CTkEntry(duration_frame, textvariable=self.duration_var, width=80)
        self.duration_entry.pack(side="left", padx=10)
        
        # Качество H.265
        h265_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        h265_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(h265_frame, text="H.265 CQ (меньше = лучше):").pack(side="left")
        self.h265_cq_var = tk.StringVar(value="28")
        self.h265_cq_entry = ctk.CTkEntry(h265_frame, textvariable=self.h265_cq_var, width=80)
        self.h265_cq_entry.pack(side="left", padx=10)
        
        # Качество AV1
        av1_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        av1_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(av1_frame, text="AV1 CQ (меньше = лучше):").pack(side="left")
        self.av1_cq_var = tk.StringVar(value="32")
        self.av1_cq_entry = ctk.CTkEntry(av1_frame, textvariable=self.av1_cq_var, width=80)
        self.av1_cq_entry.pack(side="left", padx=10)
        
        # Пресет
        preset_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(preset_frame, text="Пресет (p1-p7, p7 = лучшее сжатие):").pack(side="left")
        self.preset_var = tk.StringVar(value="p6")
        self.preset_entry = ctk.CTkEntry(preset_frame, textvariable=self.preset_var, width=80)
        self.preset_entry.pack(side="left", padx=10)
        
        # Кнопки управления
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)
        
        self.start_btn = ctk.CTkButton(
            button_frame, 
            text="🚀 Начать конвертацию",
            command=self.start_conversion,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Остановить",
            command=self.stop_conversion,
            width=150,
            height=40,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)
        
        # Прогресс
        self.progress_label = ctk.CTkLabel(self, text="Готов к работе", font=ctk.CTkFont(size=12))
        self.progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        # Лог
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(log_frame, text="Лог:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(log_frame, height=200, font=ctk.CTkFont(size=11))
        self.log_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите видеофайл",
            filetypes=[
                ("Видео файлы", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
                ("Все файлы", "*.*")
            ]
        )
        if file_path:
            self.input_file = file_path
            self.file_path_var.set(file_path)
            self.log(f"Выбран файл: {os.path.basename(file_path)}")
            
    def log(self, message):
        """Добавляет сообщение в лог"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.update_idletasks()
        
    def set_progress(self, value, text=""):
        """Устанавливает прогресс и текст"""
        self.progress_bar.set(value)
        if text:
            self.progress_label.configure(text=text)
        self.update_idletasks()
        
    def start_conversion(self):
        if not self.input_file:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите видеофайл!")
            return
            
        if not os.path.isfile(self.input_file):
            messagebox.showerror("Ошибка", "Файл не найден!")
            return
            
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log_text.delete("1.0", "end")
        
        # Запускаем в отдельном потоке, чтобы GUI не зависал
        thread = threading.Thread(target=self.conversion_thread)
        thread.daemon = True
        thread.start()
        
    def stop_conversion(self):
        self.is_running = False
        self.log("⏹️ Остановлено пользователем")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.set_progress(0, "Остановлено")
        
    def conversion_thread(self):
        """Основной поток конвертации"""
        try:
            # Получаем настройки
            sample_duration = int(self.duration_var.get())
            h265_cq = int(self.h265_cq_var.get())
            av1_cq = int(self.av1_cq_var.get())
            preset = self.preset_var.get()
            
            base_name = os.path.splitext(self.input_file)[0]
            sample_h265 = f"{base_name}_sample_h265.mp4"
            sample_av1 = f"{base_name}_sample_av1.mkv"
            
            self.log("="*50)
            self.log(f"🎬 Исходный файл: {os.path.basename(self.input_file)}")
            self.log(f"⚡ Используем NVIDIA NVENC (RTX 4060 Ti)")
            self.log(f"⏱️ Длительность теста: {sample_duration} сек.")
            self.log("="*50)
            
            # Тест H.265
            if not self.is_running:
                return
                
            self.set_progress(0.1, "Тестирование H.265...")
            self.log("\n▶️ Кодирование тестового фрагмента в H.265...")
            
            cmd_h265 = [
                "ffmpeg", "-y", "-hwaccel", "auto", "-i", self.input_file, "-t", str(sample_duration),
                "-c:v", "hevc_nvenc", "-preset", preset, "-tune", "hq",
                "-rc", "vbr", "-cq", str(h265_cq), "-b:v", "0",
                "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
                "-c:a", "aac", "-b:a", "128k",
                sample_h265
            ]
            
            self.run_ffmpeg(cmd_h265)
            
            if not self.is_running:
                return
            
            # Тест AV1
            self.set_progress(0.3, "Тестирование AV1...")
            self.log("\n▶️ Кодирование тестового фрагмента в AV1...")
            
            cmd_av1 = [
                "ffmpeg", "-y", "-hwaccel", "auto", "-i", self.input_file, "-t", str(sample_duration),
                "-c:v", "av1_nvenc", "-preset", preset, "-tune", "hq",
                "-rc", "vbr", "-cq", str(av1_cq), "-b:v", "0",
                "-spatial_aq", "1", "-temporal_aq", "1",
                "-c:a", "libopus", "-b:a", "128k",
                sample_av1
            ]
            
            self.run_ffmpeg(cmd_av1)
            
            if not self.is_running:
                return
            
            # Сравнение
            size_h265 = os.path.getsize(sample_h265)
            size_av1 = os.path.getsize(sample_av1)
            
            self.log("\n" + "="*50)
            self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТА (фрагмент {sample_duration} сек.):")
            self.log(f"   H.265 (NVENC): {self.format_size(size_h265)}")
            self.log(f"   AV1  (NVENC):  {self.format_size(size_av1)}")
            self.log("="*50)
            
            # Выбор победителя
            if size_av1 < size_h265:
                winner = "AV1"
                winner_file = f"{base_name}_nvenc_av1.mkv"
                savings = ((size_h265 - size_av1) / size_h265 * 100)
                self.log(f"\n🏆 Победитель: AV1 (сжал на {savings:.1f}% сильнее)")
                
                full_cmd = [
                    "ffmpeg", "-y", "-hwaccel", "auto", "-i", self.input_file,
                    "-c:v", "av1_nvenc", "-preset", preset, "-tune", "hq",
                    "-rc", "vbr", "-cq", str(av1_cq), "-b:v", "0",
                    "-spatial_aq", "1", "-temporal_aq", "1",
                    "-c:a", "libopus", "-b:a", "128k",
                    winner_file
                ]
            else:
                winner = "H.265"
                winner_file = f"{base_name}_nvenc_h265.mp4"
                savings = ((size_av1 - size_h265) / size_av1 * 100)
                self.log(f"\n🏆 Победитель: H.265 (сжал на {savings:.1f}% сильнее или равен)")
                
                full_cmd = [
                    "ffmpeg", "-y", "-hwaccel", "auto", "-i", self.input_file,
                    "-c:v", "hevc_nvenc", "-preset", preset, "-tune", "hq",
                    "-rc", "vbr", "-cq", str(h265_cq), "-b:v", "0",
                    "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
                    "-c:a", "aac", "-b:a", "128k",
                    winner_file
                ]
            
            # Полное кодирование
            if not self.is_running:
                return
                
            self.set_progress(0.5, f"Полное кодирование в {winner}...")
            self.log(f"\n🚀 Запускаю полное кодирование всего файла в {winner}...")
            self.log("⚠️ Это может занять время. Пожалуйста, подождите...")
            
            self.run_ffmpeg(full_cmd)
            
            if not self.is_running:
                return
            
            # Очистка
            self.set_progress(0.95, "Очистка временных файлов...")
            self.log("\n🧹 Удаляю временные файлы...")
            try:
                os.remove(sample_h265)
                os.remove(sample_av1)
                self.log("✅ Временные файлы удалены.")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления: {e}")
            
            self.set_progress(1.0, "Готово!")
            self.log(f"\n🎉 ГОТОВО! Итоговый файл:\n📁 {os.path.abspath(winner_file)}")
            
            messagebox.showinfo("Успех", f"Конвертация завершена!\n\nФайл сохранен:\n{winner_file}")
            
        except Exception as e:
            self.log(f"\n❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{e}")
            
        finally:
            self.is_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            
    def run_ffmpeg(self, cmd):
        """Запускает FFmpeg и логирует вывод"""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        for line in process.stdout:
            if not self.is_running:
                process.terminate()
                return
            if "time=" in line:
                # Обновляем лог последним статусом
                self.log_text.delete("end-2l", "end-1l")
                self.log(line.strip())
                
        process.wait()
        
        if process.returncode != 0:
            raise Exception("FFmpeg вернул ошибку. Проверьте, что FFmpeg установлен и поддерживает NVENC.")
            
    def format_size(self, size_bytes):
        """Форматирует размер файла"""
        return f"{size_bytes / (1024 * 1024):.2f} МБ"

if __name__ == "__main__":
    app = SmartConverterApp()
    app.mainloop()
```

---

### 🚀 Как запустить:

1. Установите библиотеку (если еще не установили):
   ```bash
   pip install customtkinter
   ```

2. Сохраните код в файл `smart_convert_gui.py`

3. Запустите:
   ```bash
   python smart_convert_gui.py
   ```

---

### 🎨 Что умеет GUI:

✅ **Современный темный интерфейс** в стиле популярных приложений  
✅ **Кнопка "Обзор"** для удобного выбора файла через диалог  
✅ **Настраиваемые параметры**: длительность теста, качество H.265/AV1, пресет  
✅ **Кнопка "Остановить"** - можно прервать процесс в любой момент  
✅ **Прогресс-бар** показывает этапы работы  
✅ **Подробный лог** в реальном времени  
✅ **Не блокирует интерфейс** - всё работает в отдельном потоке  
✅ **Всплывающие уведомления** об успехе или ошибках  

---

### 💡 Как пользоваться:

1. Нажмите **"Обзор..."** и выберите видеофайл
2. При необходимости измените настройки (по умолчанию стоят оптимальные значения)
3. Нажмите **"🚀 Начать конвертацию"**
4. Наблюдайте за процессом в логе
5. После завершения получите готовый файл в той же папке, что и исходник

Интерфейс интуитивно понятен - просто как обычная программа! 🎉
