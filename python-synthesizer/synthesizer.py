import sounddevice as sd
import numpy as np
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QComboBox, QDial, QPushButton, QGroupBox, QFileDialog)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot, QRect
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont
import threading
import time
from scipy.signal import butter, lfilter
import pyqtgraph as pg
from numba import jit

# --- Settings ---
SAMPLE_RATE = 44100
BUFFER_SIZE = 512
CHANNELS = 1
DARK_STYLESHEET = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #777;
        border-radius: 5px;
        margin-top: 0.5em;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 3px 0 3px;
    }
    QWidget {
        background-color: #2e2e2e;
        color: #e0e0e0;
        font-family: Arial, sans-serif;
    }
    QMainWindow {
        background-color: #2e2e2e;
    }
    QDial, QSlider {
        background-color: transparent;
    }
    QPushButton {
        background-color: #555;
        border: 1px solid #777;
        padding: 5px;
        border-radius: 3px;
        min-width: 60px;
    }
    QPushButton:hover {
        background-color: #666;
    }
    QPushButton:pressed {
        background-color: #444;
    }
    QComboBox {
        background-color: #555;
        border: 1px solid #777;
        padding: 5px;
        border-radius: 3px;
    }
    QLabel {
        font-size: 10pt;
    }
"""

# --- Note Frequencies (C-1 to G9) ---
NOTE_FREQS = {i: 8.1758 * (2**(i/12)) for i in range(128)}

# --- Numba-JIT Optimized Functions ---

@jit(nopython=True)
def poly_blep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    else:
        return 0.0

@jit(nopython=True)
def process_saw_polyblep(n_samples, phase, dt):
    wave = np.zeros(n_samples)
    for i in range(n_samples):
        t = phase / (2 * np.pi)
        naive_saw = 2.0 * t - 1.0
        wave[i] = naive_saw - poly_blep(t, dt)
        phase += dt * 2 * np.pi
        if phase >= 2 * np.pi:
            phase -= 2 * np.pi
    return wave, phase

@jit(nopython=True)
def process_square_polyblep(n_samples, phase, dt):
    wave = np.zeros(n_samples)
    for i in range(n_samples):
        t = phase / (2 * np.pi)
        naive_square = 1.0 if t < 0.5 else -1.0
        blep = poly_blep(t, dt)
        blep -= poly_blep((t + 0.5) % 1.0, dt)
        wave[i] = naive_square - blep
        phase += dt * 2 * np.pi
        if phase >= 2 * np.pi:
            phase -= 2 * np.pi
    return wave, phase

@jit(nopython=True)
def process_string_polyblep(n_samples, phases, dt):
    wave = np.zeros(n_samples)
    freq_mults = np.array([0.995, 1.0, 1.005])
    
    for j in range(3):
        phase = phases[j]
        d = dt * freq_mults[j]
        for i in range(n_samples):
            t = phase / (2 * np.pi)
            naive_saw = 2.0 * t - 1.0
            wave[i] += (naive_saw - poly_blep(t, d)) / 3.0
            phase += d * 2 * np.pi
            if phase >= 2 * np.pi:
                phase -= 2 * np.pi
        phases[j] = phase
    return wave, phases

class SynthParameters:
    # ... (no changes from previous step)
    def __init__(self):
        self.lock = threading.Lock()
        self.params = {
            'attack': 0.05, 'decay': 0.2, 'sustain': 0.7, 'release': 0.3,
            'cutoff': 0.99, 'resonance': 0.1,
            'reverb': 0.0, 'delay': 0.0,
            'instrument': 'Synth Lead'
        }
    def get(self, name):
        with self.lock: return self.params.get(name)
    def set(self, name, value):
        with self.lock: self.params[name] = value
    def get_all(self):
        with self.lock: return self.params.copy()
    def set_all(self, new_params):
        with self.lock: self.params.update(new_params)

class ADSREnvelope:
    # ... (no changes from previous step)
    def __init__(self, params):
        self.params = params
        self.state = "attack"
        self.value = 0.0
    def process(self, n_samples):
        attack_time=self.params.get('attack'); decay_time=self.params.get('decay'); sustain_level=self.params.get('sustain'); release_time=self.params.get('release')
        env = np.zeros(n_samples)
        for i in range(n_samples):
            if self.state == "attack":
                if attack_time > 0.001: self.value += 1.0 / (attack_time * SAMPLE_RATE)
                else: self.value = 1.0
                if self.value >= 1.0: self.value = 1.0; self.state = "decay"
            elif self.state == "decay":
                if decay_time > 0.001: self.value -= (1.0 - sustain_level) / (decay_time * SAMPLE_RATE)
                else: self.value = sustain_level
                if self.value <= sustain_level: self.value = sustain_level; self.state = "sustain"
            elif self.state == "sustain": self.value = sustain_level
            elif self.state == "release":
                if release_time > 0.001: self.value -= self.value / (release_time * SAMPLE_RATE)
                else: self.value = 0.0
                if self.value <= 0.0: self.value = 0.0; self.state = "off"
            env[i] = self.value**2
        return env
    def note_off(self): self.state = "release"
    def is_off(self): return self.state == "off"

class Voice:
    # ... (no changes from previous step)
    def __init__(self, note, velocity, params):
        self.note = note
        self.velocity = velocity
        self.params = params
        self.instrument = INSTRUMENTS[params.get('instrument')]()
        self.age = 0; self.phase = 0; self.phases = np.array([0.0, 0.0, 0.0])
        self.envelope = ADSREnvelope(params)
        self.filter_zi = None
    def get_samples(self, n_samples):
        if self.envelope.is_off(): return np.zeros(n_samples)
        self.age += n_samples
        wave = self.instrument.process(self, n_samples)
        cutoff_freq = self.params.get('cutoff')**(2) * (SAMPLE_RATE / 2.1)
        if cutoff_freq < SAMPLE_RATE / 2.2:
            reso = 10**(self.params.get('resonance') * -1)
            b, a = butter(2, max(1, cutoff_freq), btype='low', fs=SAMPLE_RATE, output='ba')
            if self.filter_zi is None: self.filter_zi = np.zeros(len(b)-1)
            wave, self.filter_zi = lfilter(b, a, wave, zi=self.filter_zi)
        env = self.envelope.process(n_samples)
        return wave * env * (self.velocity / 127.0) * 0.7
    def note_off(self): self.envelope.note_off()

# --- Instruments ---
class Instrument:
    def process(self, voice, n_samples): raise NotImplementedError
class SineInstrument(Instrument):
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        t = (voice.phase + np.arange(n_samples)) / SAMPLE_RATE
        wave = np.sin(2 * np.pi * freq * t)
        voice.phase += n_samples
        return wave

class SawInstrument(Instrument):
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        dt = freq / SAMPLE_RATE
        wave, new_phase = process_saw_polyblep(n_samples, voice.phase, dt)
        voice.phase = new_phase
        return wave

class SquareInstrument(Instrument):
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        dt = freq / SAMPLE_RATE
        wave, new_phase = process_square_polyblep(n_samples, voice.phase, dt)
        voice.phase = new_phase
        return wave

class StringInstrument(Instrument):
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        dt = freq / SAMPLE_RATE
        wave, new_phases = process_string_polyblep(n_samples, voice.phases, dt)
        voice.phases = new_phases
        return wave

class EPianoInstrument(Instrument):
    # ... (no changes from previous step)
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        t = (voice.phase + np.arange(n_samples)) / SAMPLE_RATE
        mod_freq_ratio = 1.0
        mod_depth = freq * 1.5
        mod_wave = mod_depth * np.sin(2 * np.pi * freq * mod_freq_ratio * t)
        wave = np.sin(2 * np.pi * (freq + mod_wave) * t)
        voice.phase += n_samples
        return wave

class PadInstrument(Instrument):
    # ... (no changes from previous step)
    def process(self, voice, n_samples):
        freq = NOTE_FREQS.get(voice.note, 440)
        t = (voice.phase + np.arange(n_samples)) / SAMPLE_RATE
        sine_wave = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-1, 1, n_samples)
        b, a = butter(4, freq * 2 if freq > 0 else 1, btype='low', fs=SAMPLE_RATE)
        filtered_noise = lfilter(b, a, noise)
        voice.phase += n_samples
        return (sine_wave * 0.6 + filtered_noise * 0.4)

class DrumKitInstrument(Instrument):
    # ... (no changes from previous step)
    def process(self, voice, n_samples):
        note, age, wave = voice.note, voice.age, np.zeros(n_samples)
        if note == 60: # Kick
            pitch_env = np.maximum(0, 1 - (age + np.arange(n_samples)) / (SAMPLE_RATE*0.15))
            freq = 150 * pitch_env + 50
            wave = np.sin(2 * np.pi * freq * ((voice.phase + np.arange(n_samples))/SAMPLE_RATE))
        elif note == 62: # Snare
            wave = lfilter(*butter(4, 4000, btype='high', fs=SAMPLE_RATE), np.random.uniform(-1, 1, n_samples))
        elif note == 64: # Hi-hat
            wave = lfilter(*butter(8, 8000, btype='high', fs=SAMPLE_RATE), np.random.uniform(-1, 1, n_samples))
        voice.phase += n_samples
        return wave

INSTRUMENTS = {"Synth Lead": SawInstrument, "Electric Piano": EPianoInstrument, "String Ensemble": StringInstrument, "Sub Bass": SquareInstrument, "Pad": PadInstrument, "Acoustic Piano": EPianoInstrument, "Drum Kit": DrumKitInstrument}

class AudioEngine(QObject):
    # ... (no changes from previous step)
    buffer_ready = pyqtSignal(np.ndarray)
    def __init__(self, params):
        super().__init__(); self.params = params; self.stream = None; self.active_voices = []; self.lock = threading.Lock()
    def audio_callback(self, outdata, frames, time, status):
        if status: print(status, file=sys.stderr)
        buffer = np.zeros((frames, CHANNELS))
        with self.lock:
            self.active_voices = [v for v in self.active_voices if not v.envelope.is_off()]
            for voice in self.active_voices:
                buffer[:, 0] += voice.get_samples(frames)
        self.buffer_ready.emit(buffer)
        outdata[:] = np.clip(buffer.reshape(outdata.shape), -1.0, 1.0)
    def note_on(self, note, velocity=127):
        with self.lock:
            if len(self.active_voices) > 16:
                oldest_voice = min(self.active_voices, key=lambda v: v.age, default=None)
                if oldest_voice: oldest_voice.note_off()
            voice = Voice(note, velocity, self.params)
            self.active_voices.append(voice)
            if self.params.get('instrument') == 'Drum Kit' and note != 64: voice.note_off()
    def note_off(self, note):
        with self.lock:
            for voice in self.active_voices:
                if voice.note == note: voice.note_off()
    def start(self):
        try:
            self.stream = sd.OutputStream(samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE, channels=CHANNELS, callback=self.audio_callback, dtype='float32')
            self.stream.start()
        except Exception as e: print(f"Error starting audio stream: {e}"); sys.exit(1)
    def stop(self):
        if self.stream: self.stream.stop(); self.stream.close()

class PianoWidget(QWidget):
    # ... (no changes from previous step)
    note_on = pyqtSignal(int); note_off = pyqtSignal(int)
    def __init__(self, start_note=48, num_octaves=2):
        super().__init__(); self.start_note = start_note; self.num_octaves = num_octaves; self.num_keys = num_octaves * 12
        self.white_key_width=35; self.white_key_height=140; self.black_key_width=22; self.black_key_height=90
        self.setMinimumSize(self.white_key_width * 7 * self.num_octaves, self.white_key_height)
        self.key_rects = {}; self.pressed_keys_set = set()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        white_key_count = 0; w_key_notes = []; b_key_notes = []
        for i in range(self.num_keys + 1):
            note = self.start_note + i
            if note % 12 not in [1, 3, 6, 8, 10]:
                x = white_key_count * self.white_key_width; rect = (x, 0, self.white_key_width, self.white_key_height)
                self.key_rects[note] = rect; w_key_notes.append((note, rect)); white_key_count += 1
        white_key_count = 0
        for i in range(self.num_keys + 1):
            note = self.start_note + i
            if note % 12 not in [1, 3, 6, 8, 10]: white_key_count += 1
            else:
                x = white_key_count * self.white_key_width - self.black_key_width // 2; rect = (x, 0, self.black_key_width, self.black_key_height)
                self.key_rects[note] = rect; b_key_notes.append((note, rect))
        for note, rect in w_key_notes:
            painter.setBrush(QBrush(QColor("#88aaff")) if note in self.pressed_keys_set else QBrush(Qt.GlobalColor.white))
            painter.setPen(QPen(Qt.GlobalColor.black)); painter.drawRect(*rect)
        for note, rect in b_key_notes:
            painter.setBrush(QBrush(QColor("#555")) if note in self.pressed_keys_set else QBrush(Qt.GlobalColor.black))
            painter.setPen(QPen(Qt.GlobalColor.black)); painter.drawRect(*rect)
    def get_note_at(self, pos):
        for note, rect in self.key_rects.items():
            if note % 12 in [1, 3, 6, 8, 10] and QRect(*rect).contains(pos): return note
        for note, rect in self.key_rects.items():
            if note % 12 not in [1, 3, 6, 8, 10] and QRect(*rect).contains(pos): return note
        return None
    def mousePressEvent(self, event):
        note = self.get_note_at(event.pos())
        if note: self.note_on.emit(note); self.pressed_keys_set.add(note); self.update()
    def mouseReleaseEvent(self, event):
        for note in self.pressed_keys_set: self.note_off.emit(note)
        self.pressed_keys_set.clear(); self.update()

class SynthesizerApp(QMainWindow):
    # ... (no changes from previous step)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Synthesizer"); self.setGeometry(100, 100, 1000, 700); self.setStyleSheet(DARK_STYLESHEET)
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget); self.main_layout = QVBoxLayout(self.central_widget)
        self.params = SynthParameters(); self.audio_engine = AudioEngine(self.params)
        self.create_controls(); self.create_visualizer(); self.create_keyboard(); self.connect_controls(); self.update_ui_from_params()
        self.key_map = {Qt.Key.Key_A: 60, Qt.Key.Key_W: 61, Qt.Key.Key_S: 62, Qt.Key.Key_E: 63, Qt.Key.Key_D: 64, Qt.Key.Key_F: 65, Qt.Key.Key_T: 66, Qt.Key.Key_G: 67, Qt.Key.Key_Y: 68, Qt.Key.Key_H: 69, Qt.Key.Key_U: 70, Qt.Key.Key_J: 71, Qt.Key.Key_K: 72}
        self.pressed_keys = set()
    def create_controls(self):
        self.controls = {}; top_layout = QHBoxLayout()
        instr_preset_box = QGroupBox("Global"); instr_preset_layout = QVBoxLayout()
        self.instrument_combo = QComboBox(); self.instrument_combo.addItems(list(INSTRUMENTS.keys()))
        instr_preset_layout.addWidget(self.instrument_combo)
        preset_buttons_layout = QHBoxLayout(); self.save_button = QPushButton("Save"); self.load_button = QPushButton("Load")
        preset_buttons_layout.addWidget(self.save_button); preset_buttons_layout.addWidget(self.load_button)
        instr_preset_layout.addLayout(preset_buttons_layout)
        instr_preset_box.setLayout(instr_preset_layout); top_layout.addWidget(instr_preset_box)
        top_layout.addWidget(self.create_knob_group("ADSR", ["Attack", "Decay", "Sustain", "Release"]))
        top_layout.addWidget(self.create_knob_group("Filter", ["Cutoff", "Resonance"]))
        top_layout.addWidget(self.create_knob_group("Effects", ["Reverb", "Delay"]))
        self.main_layout.addLayout(top_layout)
    def create_knob_group(self, name, knob_names):
        box = QGroupBox(name); layout = QHBoxLayout()
        for knob_name in knob_names:
            knob_layout = QVBoxLayout(); knob_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            knob_layout.addWidget(QLabel(knob_name)); dial = QDial(); dial.setNotchesVisible(True); dial.setRange(0, 100)
            knob_layout.addWidget(dial); value_label = QLabel("0.00"); value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            knob_layout.addWidget(value_label); layout.addLayout(knob_layout)
            self.controls[knob_name.lower()] = (dial, value_label)
        box.setLayout(layout); return box
    def create_visualizer(self):
        self.plot_widget = pg.PlotWidget(); self.plot_widget.setMinimumHeight(150); self.plot_widget.setYRange(-1, 1)
        self.plot_widget.setXRange(0, BUFFER_SIZE); self.plot_widget.getPlotItem().hideAxis('bottom'); self.plot_widget.getPlotItem().hideAxis('left')
        self.plot_curve = self.plot_widget.plot(pen='c', width=2); self.main_layout.addWidget(self.plot_widget)
    def create_keyboard(self):
        self.piano_widget = PianoWidget(start_note=60, num_octaves=2); self.main_layout.addWidget(self.piano_widget)
    def connect_controls(self):
        self.piano_widget.note_on.connect(self.audio_engine.note_on); self.piano_widget.note_off.connect(self.audio_engine.note_off)
        self.instrument_combo.currentTextChanged.connect(lambda s: self.params.set('instrument', s))
        self.controls['attack'][0].valueChanged.connect(lambda v: self.update_param('attack', v/100.0*2.0))
        self.controls['decay'][0].valueChanged.connect(lambda v: self.update_param('decay', v/100.0*2.0))
        self.controls['sustain'][0].valueChanged.connect(lambda v: self.update_param('sustain', v/100.0))
        self.controls['release'][0].valueChanged.connect(lambda v: self.update_param('release', v/100.0*5.0))
        self.controls['cutoff'][0].valueChanged.connect(lambda v: self.update_param('cutoff', (v/100.0)))
        self.controls['resonance'][0].valueChanged.connect(lambda v: self.update_param('resonance', v/100.0))
        self.save_button.clicked.connect(self.save_preset); self.load_button.clicked.connect(self.load_preset)
        self.audio_engine.buffer_ready.connect(self.update_plot)
    @pyqtSlot(np.ndarray)
    def update_plot(self, buffer): self.plot_curve.setData(buffer[:, 0])
    def update_param(self, name, value):
        self.params.set(name, value)
        if name in self.controls: self.controls[name][1].setText(f"{value:.2f}")
    def update_ui_from_params(self):
        p = self.params.get_all()
        self.instrument_combo.setCurrentText(p['instrument'])
        self.controls['attack'][0].setValue(int(p['attack']/2.0*100)); self.update_param('attack', p['attack'])
        self.controls['decay'][0].setValue(int(p['decay']/2.0*100)); self.update_param('decay', p['decay'])
        self.controls['sustain'][0].setValue(int(p['sustain']*100)); self.update_param('sustain', p['sustain'])
        self.controls['release'][0].setValue(int(p['release']/5.0*100)); self.update_param('release', p['release'])
        self.controls['cutoff'][0].setValue(int(p['cutoff']*100)); self.update_param('cutoff', p['cutoff'])
        self.controls['resonance'][0].setValue(int(p['resonance']*100)); self.update_param('resonance', p['resonance'])
    def save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f: json.dump(self.params.get_all(), f, indent=4)
    def load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if path:
            with open(path, 'r') as f: self.params.set_all(json.load(f))
            self.update_ui_from_params()
    def start_audio(self): self.audio_engine.start()
    def keyPressEvent(self, event):
        if not event.isAutoRepeat() and event.key() in self.key_map and event.key() not in self.pressed_keys:
            note = self.key_map[event.key()]; self.audio_engine.note_on(note); self.piano_widget.pressed_keys_set.add(note)
            self.piano_widget.update(); self.pressed_keys.add(event.key())
    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat() and event.key() in self.key_map:
            note = self.key_map[event.key()]; self.audio_engine.note_off(note); self.piano_widget.pressed_keys_set.discard(note)
            self.piano_widget.update(); self.pressed_keys.discard(event.key())
    def closeEvent(self, event): self.audio_engine.stop(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv); pg.setConfigOptions(antialias=True)
    main_win = SynthesizerApp(); main_win.show(); main_win.start_audio()
    sys.exit(app.exec())
