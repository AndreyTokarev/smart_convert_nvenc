# Chat: optimal codec for MPEG-4 compression

Русский: [../ru/chat-optimal-mpeg4-codec.md](../ru/chat-optimal-mpeg4-codec.md).

> Source: dialogue with another model/bot.  
> Moved into project documentation without editing the bot's answers.  
> Critical review: see [review-codec-advice.md](./review-codec-advice.md).

---
## USER
which codec is best to compress mpeg4 even more. so quality stays the same but file size gets smaller

## ASSISTANT
The term "MPEG-4" is very broad: most likely your video is encoded either in **H.264 (AVC)** or in the older **DivX/Xvid (MPEG-4 Part 2)**.

To reduce file size while keeping visual quality at the same level, you need to re-encode the video into more modern and efficient codecs. As of today (2026), there are two main leaders for the "quality/size" ratio.

### 1. AV1 (AOMedia Video 1) — Absolute compression leader
This is the most modern open codec. It delivers **20–30% smaller file size** compared to H.265 at the same quality, and 40–50% smaller than old H.264.
* **Pros:** Maximum compression, free, great for streaming and archives.
* **Cons:** Slow encoding (requires a powerful CPU).
* **Note:** In 2026, AV1 hardware decoding is available on all modern smartphones, GPUs, and Smart TVs, but on very old TVs (older than 5–7 years) it may not play.

### 2. H.265 (HEVC) — The golden middle
If AV1 takes too long to encode, H.265 is your choice. It gives **40–50% smaller size** compared to H.264 at identical quality.
* **Pros:** Excellent compression, encodes much faster than AV1. Supported by almost any modern device.
* **Cons:** Patented (but for home use that does not matter).

---

### 🌟 Main secret to preserving quality: CRF
To avoid quality loss while reducing size, **never set a fixed bitrate**. Use the **CRF (Constant Rate Factor)** parameter. It makes the codec allocate more bitrate to complex scenes and less to simple ones.

* **For H.265 (x265):** Ideal CRF is **22 to 26**. (Lower number = higher quality and larger size. 23–24 is visually lossless.)
* **For AV1:** Ideal CRF is **28 to 32**. (AV1 scale is slightly different; numbers are higher.)

**Second secret: Preset**
Always set the encoding preset to **"Slow"** or **"Slower"**. The longer the computer thinks over each frame, the more efficiently it compresses it. The file will be smaller at the same CRF.

---

### Don't forget audio!
Often half of a video file's size is a "heavy" audio track.
* Re-encode audio to **AAC** (128–160 kbps bitrate) or **Opus** (96–128 kbps — Opus at 128 kbps is indistinguishable from the original but weighs almost nothing).

---

### Which programs to use?

#### Option 1: HandBrake (Simplest, with a GUI)
1. Download [HandBrake](https://handbrake.fr/) (free).
2. Add your video.
3. On the **Video** tab, choose codec: **H.265 (x265)** or **AV1**.
4. In the **Quality** field, choose **Constant Quality (CRF)** and set `24` (for H.265) or `30` (for AV1).
5. In **Encoder Preset**, choose `Slow`.
6. On the **Audio** tab, choose codec `AAC` or `Opus` and bitrate `128`.
7. Click **Start Encode**.

#### Option 2: FFmpeg (For advanced users / command line)
If you like the console, here are ideal commands:

**For H.265 (HEVC):**
```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 24 -preset slow -tag:v hvc1 -c:a aac -b:a 128k output.mp4
```
*(The `-tag:v hvc1` parameter is needed so the video plays without issues in Safari and on Apple devices.)*

**For AV1 (maximum compression):**
```bash
ffmpeg -i input.mp4 -c:v libsvtav1 -crf 30 -preset 6 -c:a libopus -b:a 128k output.mkv
```
*(Here `libsvtav1` is used — it encodes AV1 many times faster than older implementations.)*

### Summary:
1. If you have a **modern PC/TV/smartphone** and need **maximum size reduction** (e.g. for storage or sending) — use **AV1** with CRF 30.
2. If you need **compatibility** with all devices and reasonable re-encode time — use **H.265** with CRF 24.
3. If your source video is ancient **DivX/Xvid**, re-encoding it even to plain **H.264** (with CRF 18–20) will already shrink size 2–3× with no quality loss.

## USER
write a python script. ffmpeg is already installed. i want a small part encoded in both H.265 and AV1 and then compared on how much that chunk shrank and where compression is more efficient.. and then the whole file converted taking into account which format compressed stronger\or more optimally

## ASSISTANT
Great idea! This approach (test-encoding a fragment) is called **benchmarking**, and it is the most reliable way to pick the optimal codec for a specific video, because different videos (cartoons, movies, fast-paced games) compress differently.

Below is a ready Python script. It does exactly what you asked:
1. Takes the first 30 seconds of video.
2. Encodes that fragment in **H.265** and **AV1** with optimal settings.
3. Compares sizes of the resulting files.
4. Picks the winner (whoever produced the smaller size).
5. Runs **full video** encoding with the chosen codec.
6. Deletes temporary test files.

### 🐍 Python script `smart_convert.py`

```python
import os
import sys
import subprocess
import time

# ================= SETTINGS =================
SAMPLE_DURATION = 30       # Test fragment duration in seconds
H265_CRF = 24              # Quality for H.265 (lower = better quality, larger size)
AV1_CRF = 30               # Quality for AV1 (scale differs; 30 ≈ 24 in H.265)
H265_PRESET = "slow"       # H.265 encoding speed (ultrafast, fast, medium, slow, slower)
AV1_PRESET = "6"           # AV1 encoding speed (0-13; 0 = slowest/best quality, 13 = fast)
# =============================================

def format_size(size_bytes):
    """Convert bytes to readable format (MB)"""
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def run_ffmpeg(cmd, description):
    """Run FFmpeg and show progress"""
    print(f"\n▶️ {description}...")
    print(f"Command: {' '.join(cmd)}")
    
    start_time = time.time()
    # Start process, redirect output to show progress in console
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
    
    for line in process.stdout:
        # Filter output to avoid spam; show only lines with time (progress)
        if "time=" in line:
            print(line.strip())
            
    process.wait()
    
    if process.returncode != 0:
        print(f"❌ FFmpeg error while running: {description}")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    print(f"✅ Finished in {elapsed:.1f} sec.")

def main():
    # 1. Get file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("📁 Enter path to video file (or drag it into the terminal window): ").strip().strip('"')

    if not os.path.isfile(input_file):
        print("❌ File not found. Check the path.")
        sys.exit(1)

    base_name = os.path.splitext(input_file)[0]
    
    # Temporary and final file names
    sample_h265 = f"{base_name}_sample_h265.mp4"
    sample_av1 = f"{base_name}_sample_av1.mkv"
    
    output_h265 = f"{base_name}_converted_h265.mp4"
    output_av1 = f"{base_name}_converted_av1.mkv"

    print(f"\n🎬 Source file: {os.path.basename(input_file)}")
    print(f"⏱️ Test duration: {SAMPLE_DURATION} sec.")
    print("🔄 Starting test encoding of fragments...")

    # 2. Encode H.265 test fragment
    cmd_h265 = [
        "ffmpeg", "-y", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "libx265", "-crf", str(H265_CRF), "-preset", H265_PRESET,
        "-c:a", "aac", "-b:a", "128k",
        sample_h265
    ]
    run_ffmpeg(cmd_h265, "Encoding test fragment in H.265")

    # 3. Encode AV1 test fragment
    cmd_av1 = [
        "ffmpeg", "-y", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "libsvtav1", "-crf", str(AV1_CRF), "-preset", AV1_PRESET,
        "-c:a", "libopus", "-b:a", "128k",
        sample_av1
    ]
    run_ffmpeg(cmd_av1, "Encoding test fragment in AV1")

    # 4. Compare sizes
    size_h265 = os.path.getsize(sample_h265)
    size_av1 = os.path.getsize(sample_av1)

    print("\n" + "="*50)
    print("📊 TEST RESULTS ({} sec. fragment):".format(SAMPLE_DURATION))
    print(f"   H.265 (x265): {format_size(size_h265)}")
    print(f"   AV1 (SVT-AV1): {format_size(size_av1)}")
    print("="*50)

    # 5. Pick winner
    if size_av1 < size_h265:
        winner = "AV1"
        winner_file = output_av1
        print(f"🏆 Winner: AV1 (compressed {((size_h265 - size_av1) / size_h265 * 100):.1f}% more)")
        full_cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "libsvtav1", "-crf", str(AV1_CRF), "-preset", AV1_PRESET,
            "-c:a", "libopus", "-b:a", "128k",
            winner_file
        ]
    else:
        winner = "H.265"
        winner_file = output_h265
        print(f"🏆 Winner: H.265 (compressed {((size_av1 - size_h265) / size_av1 * 100):.1f}% more or equal)")
        full_cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-c:v", "libx265", "-crf", str(H265_CRF), "-preset", H265_PRESET,
            "-c:a", "aac", "-b:a", "128k",
            winner_file
        ]

    # 6. Run full encoding
    print(f"\n🚀 Starting full file encoding in {winner}...")
    print("⚠️  This may take a while. Do not close the window.")
    run_ffmpeg(full_cmd, f"Full encoding in {winner}")

    # 7. Clean up temporary files
    print("\n🧹 Deleting temporary test files...")
    try:
        os.remove(sample_h265)
        os.remove(sample_av1)
        print("✅ Temporary files deleted.")
    except Exception as e:
        print(f"⚠️ Could not delete temporary files: {e}")

    print(f"\n🎉 DONE! Output file saved as:\n📁 {os.path.abspath(winner_file)}")

if __name__ == "__main__":
    main()
```

---

### 🛠️ How to use:

1. Make sure Python (3.6+) is installed.
2. Save the code above to a file named `smart_convert.py`.
3. Open a terminal (command prompt) and run the script with the video path:
   ```bash
   python smart_convert.py "C:\Path\to\your\video.mp4"
   ```
   *(Or just run `python smart_convert.py` and the script will ask you to enter or drag a file into the window.)*

---

### ⚙️ What you can tune (at the top of the script):

- `SAMPLE_DURATION = 30`: For very long videos (e.g. 2 hours), 30 seconds is enough for a representative sample. For short videos or a more accurate test, set `60`.
- `H265_CRF = 24` and `AV1_CRF = 30`: This is a quality balance. For **maximum quality** (near lossless), change to `20` and `26` respectively (files will be larger). For **maximum compression** (archive), set `28` and `34`.
- `AV1_PRESET = "6"`: This is the sweet spot for SVT-AV1. If you have a powerful CPU and want to squeeze another 5–10% size, set `"4"` or `"5"` (encoding will be noticeably slower).

### 💡 Important notes:
1. **AV1 speed:** Test AV1 encoding can take 2–4× longer than H.265, even for 30 seconds. That is normal — the price of super compression.
2. **Codec `libsvtav1`:** The script uses `libsvtav1` (SVT-AV1) because it is many times faster than old `libaom-av1` and is included in most modern FFmpeg builds (e.g. from gyancoder or gyan.dev). If your FFmpeg errors with "Unknown encoder 'libsvtav1'", replace `libsvtav1` with `libaom-av1` in the script (but expect longer waits).
3. **Containers:** The script saves H.265 as `.mp4` and AV1 as `.mkv`. This is intentional: `.mkv` guarantees trouble-free AV1 + Opus without extra compatibility tag work.

## USER
oh forgot i have hardware acceleration cuda card 4060 Ti Nvidia 16 GB VRAM

## ASSISTANT
Great clarification! **RTX 4060 Ti** is a gem for this kind of task. Unlike the 30 series, Ada Lovelace (40 series) chips have a **hardware AV1 encoder**. That means you can compress to AV1 not painfully slowly on CPU, but in seconds on the GPU.

### ⚠️ Important nuance of hardware encoding (NVENC)
You need to understand the difference between software (CPU) and hardware (GPU) encoding:
1. **Speed:** NVENC (hardware) encodes **10–50× faster** than CPU. A 30-second test fragment will be ready in 1–2 seconds.
2. **File size:** At the same *visual* quality, hardware encoding produces a file **10–20% larger** than software. The price of speed.

But since you have a 40 series card, we will compare **two hardware codecs**: `hevc_nvenc` (H.265) and `av1_nvenc` (AV1). AV1 almost always wins on size between them, but we will verify with the script.

---

### 🐍 Updated script `smart_convert_nvenc.py`

NVENC has no `CRF` parameter. Instead it uses **`-cq` (Constant Quality)** together with `-rc vbr`. Lower `-cq` means higher quality and larger size.

```python
import os
import sys
import subprocess
import time

# ================= SETTINGS =================
SAMPLE_DURATION = 30       # Test fragment duration in seconds

# H.265 (hevc_nvenc) settings
H265_CQ = 28               # Quality (CRF analog. 28 is a great balance)
H265_PRESET = "p6"         # Preset (p1-p7. p7 = best compression but slower. p6 = sweet spot)

# AV1 (av1_nvenc) settings - RTX 40 series feature!
AV1_CQ = 32                # Quality for AV1 (scale slightly different; 32 ≈ 28 in H.265)
AV1_PRESET = "p6"          # Preset for AV1
# =============================================

def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def run_ffmpeg(cmd, description):
    print(f"\n▶️ {description}...")
    start_time = time.time()
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
    
    for line in process.stdout:
        if "time=" in line:
            print(line.strip(), end='\r') # Overwrite line for clean progress
            
    process.wait()
    print("\n", end="") # Newline after progress
    
    if process.returncode != 0:
        print(f"❌ FFmpeg error. Your FFmpeg may not support NVENC or AV1.")
        print("Make sure you have a recent FFmpeg build with NVENC support (e.g. from gyan.dev).")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    print(f"✅ Finished in {elapsed:.2f} sec.")

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("📁 Enter path to video file: ").strip().strip('"')

    if not os.path.isfile(input_file):
        print("❌ File not found.")
        sys.exit(1)

    base_name = os.path.splitext(input_file)[0]
    
    sample_h265 = f"{base_name}_sample_h265.mp4"
    sample_av1 = f"{base_name}_sample_av1.mkv"
    output_h265 = f"{base_name}_nvenc_h265.mp4"
    output_av1 = f"{base_name}_nvenc_av1.mkv"

    print(f"\n🎬 Source file: {os.path.basename(input_file)}")
    print(f"⚡ Using NVIDIA NVENC hardware acceleration (RTX 4060 Ti)")
    print("🔄 Starting test encoding of fragments...")

    # 1. H.265 test (hevc_nvenc)
    # -hwaccel auto speeds up source decode when supported
    # -spatial_aq 1 and -temporal_aq 1 enable adaptive quantization (greatly improves quality)
    cmd_h265 = [
        "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "hevc_nvenc", "-preset", H265_PRESET, "-tune", "hq", 
        "-rc", "vbr", "-cq", str(H265_CQ), "-b:v", "0",
        "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
        "-c:a", "aac", "-b:a", "128k",
        sample_h265
    ]
    run_ffmpeg(cmd_h265, "H.265 test (hevc_nvenc)")

    # 2. AV1 test (av1_nvenc)
    cmd_av1 = [
        "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file, "-t", str(SAMPLE_DURATION),
        "-c:v", "av1_nvenc", "-preset", AV1_PRESET, "-tune", "hq",
        "-rc", "vbr", "-cq", str(AV1_CQ), "-b:v", "0",
        "-spatial_aq", "1", "-temporal_aq", "1",
        "-c:a", "libopus", "-b:a", "128k",
        sample_av1
    ]
    run_ffmpeg(cmd_av1, "AV1 test (av1_nvenc)")

    # 3. Comparison
    size_h265 = os.path.getsize(sample_h265)
    size_av1 = os.path.getsize(sample_av1)

    print("\n" + "="*50)
    print(f"📊 TEST RESULTS ({SAMPLE_DURATION} sec. fragment):")
    print(f"   H.265 (NVENC): {format_size(size_h265)}")
    print(f"   AV1  (NVENC):  {format_size(size_av1)}")
    print("="*50)

    # 4. Pick winner
    if size_av1 < size_h265:
        winner = "AV1"
        winner_file = output_av1
        print(f"🏆 Winner: AV1 (compressed {((size_h265 - size_av1) / size_h265 * 100):.1f}% more)")
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
        print(f"🏆 Winner: H.265 (compressed {((size_av1 - size_h265) / size_av1 * 100):.1f}% more or equal)")
        full_cmd = [
            "ffmpeg", "-y", "-hwaccel", "auto", "-i", input_file,
            "-c:v", "hevc_nvenc", "-preset", H265_PRESET, "-tune", "hq",
            "-rc", "vbr", "-cq", str(H265_CQ), "-b:v", "0",
            "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
            "-c:a", "aac", "-b:a", "128k",
            winner_file
        ]

    # 5. Full encoding
    print(f"\n🚀 Starting full file encoding in {winner} via NVENC...")
    run_ffmpeg(full_cmd, f"Full encoding in {winner}")

    # 6. Cleanup
    print("\n🧹 Deleting temporary files...")
    try:
        os.remove(sample_h265)
        os.remove(sample_av1)
        print("✅ Temporary files deleted.")
    except Exception as e:
        print(f"⚠️ Delete error: {e}")

    print(f"\n🎉 DONE! Output file:\n📁 {os.path.abspath(winner_file)}")

if __name__ == "__main__":
    main()
```

---

### 🔍 What changed here and why it matters:

1. **Codecs `hevc_nvenc` and `av1_nvenc`**: They use the physical NVENC and AV1 blocks on your RTX 4060 Ti. CPU will stay almost idle.
2. **Parameter `-cq` instead of `-crf`**: NVIDIA hardware encoding uses Constant Quality (`-cq`). Values `28` (H.265) and `32` (AV1) give excellent picture without artifacts.
3. **Parameter `-preset p6`**: NVENC presets are `p1` (fastest) through `p7` (slowest, best compression). `p6` is the sweet spot for 40 series. For maximum squeeze and ~10% extra wait time, switch to `p7`.
4. **`-spatial_aq 1` and `-temporal_aq 1`**: This is **adaptive quantization**. Critical for NVENC! Without it the GPU may blur dark scenes and cause banding on gradients (e.g. sky). These flags spend bitrate smarter.
5. **`-hwaccel auto`**: Speeds up *reading and decoding* the source with the GPU (if source is H.264/H.265).
6. **`-profile:v main10`**: Enables 10-bit H.265 encoding. Smoother gradients and slightly better compression.

### 💡 Expected results:
- **Speed:** A 2-hour 1080p film will re-encode in about **5–15 minutes** (vs 2–4 hours on CPU).
- **Size:** AV1 will beat H.265 by about 20–25% file size.
- **Load:** During encoding GPU usage in Task Manager will be around 30–50% (NVENC blocks use a small part of the die), and CPU will idle. You can game or work on the PC while encoding!

## USER
can you also make a gui?

## ASSISTANT
Sure! I'll make a modern GUI with **CustomTkinter** — a library that gives a nice dark look like modern apps.

### 📦 First install the library:

```bash
pip install customtkinter
```

---

### 🐍 Full code with GUI: `smart_convert_gui.py`

```python
import os
import sys
import subprocess
import time
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# Theme settings
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
        # Title
        self.title_label = ctk.CTkLabel(
            self, 
            text="🎬 Smart Video Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(20, 10))
        
        self.subtitle_label = ctk.CTkLabel(
            self,
            text="Automatic H.265 vs AV1 comparison with NVIDIA NVENC",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(pady=(0, 20))
        
        # File picker frame
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(file_frame, text="Source file:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path_var, width=500)
        self.file_entry.pack(side="left", padx=(10, 5), pady=10, fill="x", expand=True)
        
        self.browse_btn = ctk.CTkButton(file_frame, text="Browse...", command=self.browse_file, width=100)
        self.browse_btn.pack(side="right", padx=(5, 10), pady=10)
        
        # Settings frame
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(settings_frame, text="Test settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Test duration
        duration_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        duration_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(duration_frame, text="Test duration (sec):").pack(side="left")
        self.duration_var = tk.StringVar(value="30")
        self.duration_entry = ctk.CTkEntry(duration_frame, textvariable=self.duration_var, width=80)
        self.duration_entry.pack(side="left", padx=10)
        
        # H.265 quality
        h265_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        h265_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(h265_frame, text="H.265 CQ (lower = better):").pack(side="left")
        self.h265_cq_var = tk.StringVar(value="28")
        self.h265_cq_entry = ctk.CTkEntry(h265_frame, textvariable=self.h265_cq_var, width=80)
        self.h265_cq_entry.pack(side="left", padx=10)
        
        # AV1 quality
        av1_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        av1_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(av1_frame, text="AV1 CQ (lower = better):").pack(side="left")
        self.av1_cq_var = tk.StringVar(value="32")
        self.av1_cq_entry = ctk.CTkEntry(av1_frame, textvariable=self.av1_cq_var, width=80)
        self.av1_cq_entry.pack(side="left", padx=10)
        
        # Preset
        preset_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(preset_frame, text="Preset (p1-p7, p7 = best compression):").pack(side="left")
        self.preset_var = tk.StringVar(value="p6")
        self.preset_entry = ctk.CTkEntry(preset_frame, textvariable=self.preset_var, width=80)
        self.preset_entry.pack(side="left", padx=10)
        
        # Control buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)
        
        self.start_btn = ctk.CTkButton(
            button_frame, 
            text="🚀 Start conversion",
            command=self.start_conversion,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Stop",
            command=self.stop_conversion,
            width=150,
            height=40,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)
        
        # Progress
        self.progress_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12))
        self.progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        # Log
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(log_frame, text="Log:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(log_frame, height=200, font=ctk.CTkFont(size=11))
        self.log_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select video file",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.input_file = file_path
            self.file_path_var.set(file_path)
            self.log(f"Selected file: {os.path.basename(file_path)}")
            
    def log(self, message):
        """Append message to log"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.update_idletasks()
        
    def set_progress(self, value, text=""):
        """Set progress bar and label text"""
        self.progress_bar.set(value)
        if text:
            self.progress_label.configure(text=text)
        self.update_idletasks()
        
    def start_conversion(self):
        if not self.input_file:
            messagebox.showerror("Error", "Please select a video file!")
            return
            
        if not os.path.isfile(self.input_file):
            messagebox.showerror("Error", "File not found!")
            return
            
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log_text.delete("1.0", "end")
        
        # Run in a separate thread so GUI does not freeze
        thread = threading.Thread(target=self.conversion_thread)
        thread.daemon = True
        thread.start()
        
    def stop_conversion(self):
        self.is_running = False
        self.log("⏹️ Stopped by user")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.set_progress(0, "Stopped")
        
    def conversion_thread(self):
        """Main conversion thread"""
        try:
            # Read settings
            sample_duration = int(self.duration_var.get())
            h265_cq = int(self.h265_cq_var.get())
            av1_cq = int(self.av1_cq_var.get())
            preset = self.preset_var.get()
            
            base_name = os.path.splitext(self.input_file)[0]
            sample_h265 = f"{base_name}_sample_h265.mp4"
            sample_av1 = f"{base_name}_sample_av1.mkv"
            
            self.log("="*50)
            self.log(f"🎬 Source file: {os.path.basename(self.input_file)}")
            self.log(f"⚡ Using NVIDIA NVENC (RTX 4060 Ti)")
            self.log(f"⏱️ Test duration: {sample_duration} sec.")
            self.log("="*50)
            
            # H.265 test
            if not self.is_running:
                return
                
            self.set_progress(0.1, "Testing H.265...")
            self.log("\n▶️ Encoding test fragment in H.265...")
            
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
            
            # AV1 test
            self.set_progress(0.3, "Testing AV1...")
            self.log("\n▶️ Encoding test fragment in AV1...")
            
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
            
            # Comparison
            size_h265 = os.path.getsize(sample_h265)
            size_av1 = os.path.getsize(sample_av1)
            
            self.log("\n" + "="*50)
            self.log(f"📊 TEST RESULTS ({sample_duration} sec. fragment):")
            self.log(f"   H.265 (NVENC): {self.format_size(size_h265)}")
            self.log(f"   AV1  (NVENC):  {self.format_size(size_av1)}")
            self.log("="*50)
            
            # Pick winner
            if size_av1 < size_h265:
                winner = "AV1"
                winner_file = f"{base_name}_nvenc_av1.mkv"
                savings = ((size_h265 - size_av1) / size_h265 * 100)
                self.log(f"\n🏆 Winner: AV1 (compressed {savings:.1f}% more)")
                
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
                self.log(f"\n🏆 Winner: H.265 (compressed {savings:.1f}% more or equal)")
                
                full_cmd = [
                    "ffmpeg", "-y", "-hwaccel", "auto", "-i", self.input_file,
                    "-c:v", "hevc_nvenc", "-preset", preset, "-tune", "hq",
                    "-rc", "vbr", "-cq", str(h265_cq), "-b:v", "0",
                    "-profile:v", "main10", "-spatial_aq", "1", "-temporal_aq", "1",
                    "-c:a", "aac", "-b:a", "128k",
                    winner_file
                ]
            
            # Full encoding
            if not self.is_running:
                return
                
            self.set_progress(0.5, f"Full encoding in {winner}...")
            self.log(f"\n🚀 Starting full file encoding in {winner}...")
            self.log("⚠️ This may take a while. Please wait...")
            
            self.run_ffmpeg(full_cmd)
            
            if not self.is_running:
                return
            
            # Cleanup
            self.set_progress(0.95, "Cleaning temporary files...")
            self.log("\n🧹 Deleting temporary files...")
            try:
                os.remove(sample_h265)
                os.remove(sample_av1)
                self.log("✅ Temporary files deleted.")
            except Exception as e:
                self.log(f"⚠️ Delete error: {e}")
            
            self.set_progress(1.0, "Done!")
            self.log(f"\n🎉 DONE! Output file:\n📁 {os.path.abspath(winner_file)}")
            
            messagebox.showinfo("Success", f"Conversion complete!\n\nFile saved:\n{winner_file}")
            
        except Exception as e:
            self.log(f"\n❌ Error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
            
        finally:
            self.is_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            
    def run_ffmpeg(self, cmd):
        """Run FFmpeg and log output"""
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
                # Update log with latest status
                self.log_text.delete("end-2l", "end-1l")
                self.log(line.strip())
                
        process.wait()
        
        if process.returncode != 0:
            raise Exception("FFmpeg returned an error. Check that FFmpeg is installed and supports NVENC.")
            
    def format_size(self, size_bytes):
        """Format file size"""
        return f"{size_bytes / (1024 * 1024):.2f} MB"

if __name__ == "__main__":
    app = SmartConverterApp()
    app.mainloop()
```

---

### 🚀 How to run:

1. Install the library (if not already installed):
   ```bash
   pip install customtkinter
   ```

2. Save the code to `smart_convert_gui.py`

3. Run:
   ```bash
   python smart_convert_gui.py
   ```

---

### 🎨 What the GUI can do:

✅ **Modern dark interface** like popular apps  
✅ **Browse button** for easy file selection via dialog  
✅ **Configurable parameters**: test duration, H.265/AV1 quality, preset  
✅ **Stop button** — interrupt the process anytime  
✅ **Progress bar** shows workflow stages  
✅ **Detailed real-time log**  
✅ **Non-blocking UI** — everything runs in a separate thread  
✅ **Popup notifications** for success or errors  

---

### 💡 How to use:

1. Click **"Browse..."** and select a video file
2. Change settings if needed (defaults are optimal)
3. Click **"🚀 Start conversion"**
4. Watch progress in the log
5. When done, get the output file in the same folder as the source

The interface is intuitive — just like a normal app! 🎉
