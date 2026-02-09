import tkinter as tk
import numpy as np
import sounddevice as sd

# Audio settings
SAMPLE_RATE = 44100
DURATION = 0.1  # Buffer duration in seconds
frequency = 440.0  # A4 note
is_playing = False

def audio_callback(outdata, frames, time, status):
    global frequency
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
    tone = 0.3 * np.sin(2 * np.pi * frequency * t)  # 0.3 = volume
    outdata[:] = np.column_stack((tone, tone))  # Stereo

def start_sound():
    global is_playing
    if not is_playing:
        sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=2,
            callback=audio_callback,
            blocksize=int(SAMPLE_RATE * DURATION)
        ).start()
        is_playing = True

def set_frequency(val):
    global frequency
    frequency = float(val)

# GUI
root = tk.Tk()
root.title("Simple Synth")

tk.Label(root, text="Frequency (Hz)").pack()
freq_slider = tk.Scale(root, from_=200, to=2000, orient='horizontal', command=set_frequency)
freq_slider.set(440)
freq_slider.pack()

play_btn = tk.Button(root, text="Play", command=start_sound)
play_btn.pack()

root.mainloop()