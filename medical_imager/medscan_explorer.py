# 🩺 medscan_explorer.py
# Educational prototype — NOT for clinical diagnosis
# Requires: Python 3.9+, requests, pillow, tkinter
# Author: For jerrysyre — learning/demo purposes only

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import requests
import json
import os
import sys
import io
import base64

# ======================
# 🔐 CONFIGURATION — EDIT THIS SECTION
# ======================
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Models
VISION_MODEL = "llava:7b"  # Vision model for image analysis
LLM_MODEL = "phi3:latest"       # For explanations

# Safety settings
CONFIDENCE_THRESHOLD = 0.60  # Only show findings ≥60% confidence (Note: This is now illustrative, as LLM output is text)
MAX_FINDINGS = 5

# ======================
# 🧠 Inference Functions
# ======================

def get_image_base64(image_path):
    """Converts an image file to a base64 encoded string."""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if not already
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Resize if image is very large to reduce payload size
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Image processing failed: {e}")

def query_vision_model(image_path):
    """
    Send image to local Ollama Vision API (LLaVA).
    Returns a textual description of findings.
    """
    try:
        image_b64 = get_image_base64(image_path)
        
        prompt = (
            "You are a medical imaging analysis assistant specializing in ophthalmology. Analyze the provided retina scan image. "
            "Identify and list key potential abnormalities or notable features specific to retinal health. For each finding, provide a short, neutral description. "
            "If there are no clear findings, state that. Present the output as a simple list. Do not add conversational text or disclaimers."
            "\n\nExample Output:\n- Macular Edema: Swelling observed in the macular region.\n- Retinal Hemorrhage: Presence of bleeding on the retinal surface."
        )

        payload = {
            "model": VISION_MODEL,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=360)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(result["error"])

        # The response from Ollama is a single text block.
        # We return it directly for the LLM to process.
        return result.get("response", "No response from vision model.").strip()

    except requests.exceptions.Timeout:
        raise Exception("Request timed out — Is Ollama running and is the model pulled?")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}. Is Ollama running at {OLLAMA_API_URL}?")
    except Exception as e:
        raise Exception(f"Vision model error: {e}")

def query_llm(prompt, max_tokens=500):
    """
    Query LLM with a prompt.
    Returns generated text.
    """
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9
        }
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=360)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(result["error"])
        
        return result.get("response", "").strip()

    except Exception as e:
        raise Exception(f"LLM error: {e}")

# ======================
# 🖥️ Tkinter Application
# ======================

class MedScanExplorer:
    def __init__(self, root):
        self.root = root
        self.root.title("🩺 MedScan Explorer — Educational Prototype")
        self.root.geometry("900x720")
        self.root.configure(bg="#f8f9fa")

        # Styling
        self.font_normal = ("Segoe UI", 10)
        self.font_bold = ("Segoe UI", 10, "bold")
        self.font_small = ("Segoe UI", 9)

        self.setup_ui()
        self.current_image_path = None

    def setup_ui(self):
                # Create a main frame to hold all widgets
                main_frame = tk.Frame(self.root, bg="#f8f9fa")
                main_frame.pack(fill=tk.BOTH, expand=True)
        
                # Create a canvas and a scrollbar
                canvas = tk.Canvas(main_frame, bg="#f8f9fa")
                scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
                scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(
                        scrollregion=canvas.bbox("all")
                    )
                )
        
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
        
                # Pack the canvas and scrollbar
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
                # Top banner
                banner = tk.Frame(scrollable_frame, bg="#e3342f", height=60)
                banner.pack(fill="x")
                tk.Label(
                    banner,
                    text="🚨 MEDICAL SCAN EXPLORER (EDUCATIONAL USE ONLY)",
                    font=("Segoe UI", 14, "bold"),
                    fg="white",
                    bg="#e3342f"
                ).pack(pady=12)
        
                warning_text = (
                    "This tool uses local AI models (Ollama) for academic demonstration. "
                    "It does NOT provide medical diagnoses. "
                    "ALWAYS consult a licensed radiologist or physician."
                )
                tk.Label(
                    scrollable_frame,
                    text=warning_text,
                    font=self.font_small,
                    fg="#d9534f",
                    bg="#f8f9fa",
                    wraplength=850,
                    justify="center"
                ).pack(pady=(5, 15))
        
                # Upload section
                upload_frame = tk.Frame(scrollable_frame, bg="#f8f9fa")
                upload_frame.pack(pady=5)
        
                self.upload_btn = tk.Button(
                    upload_frame,
                    text="📁 Upload Medical Image (PNG/JPG)",
                    command=self.upload_image,
                    font=self.font_bold,
                    bg="#5cb85c",
                    fg="white",
                    relief="flat",
                    padx=20,
                    pady=8
                )
                self.upload_btn.pack()
        
                # Image preview
                self.image_label = tk.Label(scrollable_frame, bg="white", relief="solid", bd=1)
                self.image_label.pack(pady=15)
        
                # Analyze button
                self.analyze_btn = tk.Button(
                    scrollable_frame,
                    text="🔍 Analyze Scan (via Ollama)",
                    command=self.analyze,
                    font=self.font_bold,
                    bg="#5bc0de",
                    fg="white",
                    relief="flat",
                    padx=25,
                    pady=10,
                    state="disabled"
                )
                self.analyze_btn.pack(pady=5)
        
                # Status bar
                self.status_var = tk.StringVar(value="Ready — Upload an image to begin.")
                self.status_label = tk.Label(
                    scrollable_frame,
                    textvariable=self.status_var,
                    font=self.font_small,
                    fg="#6c757d",
                    bg="#f8f9fa"
                )
                self.status_label.pack(pady=(5, 0))
        
                # Results panel
                tk.Label(scrollable_frame, text="Analysis Results", font=self.font_bold, bg="#f8f9fa").pack(pady=(15, 5))
        
                self.result_text = scrolledtext.ScrolledText(
                    scrollable_frame,
                    wrap=tk.WORD,
                    font=("Consolas", 10),
                    bg="#f1f3f5",
                    height=30
                )
                self.result_text.pack(padx=20, pady=(0, 15), fill=tk.BOTH, expand=True)
                self.result_text.insert(tk.END, "📤 Upload a medical image to start analysis...\n")
                self.result_text.configure(state="disabled")
        
                # Footer
                footer = tk.Frame(scrollable_frame, bg="#343a40", height=40)
                footer.pack(fill="x", side="bottom")
                tk.Label(
                    footer,
                    text=f"Made for educational purposes | Models: {VISION_MODEL} + {LLM_MODEL} | Ollama API",
                    font=self.font_small,
                    fg="lightgray",
                    bg="#343a40"
                ).pack(pady=10)

    def upload_image(self):
        path = filedialog.askopenfilename(
            title="Select Medical Image",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")
            ]
        )
        if not path:
            return

        try:
            self.status_var.set("Loading image...")
            self.root.update()

            self.current_image_path = path

            # Load for preview
            img = Image.open(path)
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            if img.mode != "RGB":
                img = img.convert("RGB")
            self.tk_img = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_img, text="")

            # Enable analyze
            self.analyze_btn.config(state="normal")
            self.status_var.set(f"✅ Loaded: {os.path.basename(path)} — Ready to analyze.")
            self.result_text.configure(state="normal")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"Image loaded: {os.path.basename(path)}\nClick 'Analyze Scan' to proceed.")
            self.result_text.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Image Error", f"Could not load image:\n{e}")
            self.status_var.set("❌ Image load failed.")

    def analyze(self):
        if not self.current_image_path:
            return

        self.analyze_btn.config(state="disabled")
        self.status_var.set(f"📡 Sending to Ollama ({VISION_MODEL})...")
        self.root.update()

        try:
            # Step 1: Vision model
            vision_findings = query_vision_model(self.current_image_path)
            self.status_var.set(f"🤖 Generating educational explanation ({LLM_MODEL})...")
            self.root.update()

            # Step 2: LLM for explanation
            prompt = f"""You are an educational AI assistant helping students understand AI-assisted medical imaging.

A vision model analyzed a medical scan and reported the following raw observations:
---
{vision_findings}
---

❗ Critical Instructions:
1.  Synthesize these raw findings into a clear, educational summary.
2.  For each finding, briefly explain what it *might* suggest in general medical terms, but strictly avoid making a diagnosis.
3.  Emphasize the critical limitations: AI models can make mistakes, misinterpret images, and completely lack the clinical context of a real patient.
4.  Conclude with a strong, unmissable warning: "This AI-generated output is for educational purposes ONLY and must be reviewed by a licensed medical professional (e.g., a radiologist) before any clinical consideration."
5.  Keep the tone professional, cautious, and safety-focused. Do not use overly confident language.

Educational Explanation:"""

            explanation = query_llm(prompt)

            # Format output
            self.result_text.configure(state="normal")
            self.result_text.delete(1.0, tk.END)

            self.result_text.insert(tk.END, "✅ ANALYSIS COMPLETE\n", "header")
            self.result_text.insert(tk.END, "\n🔬 Raw Vision Model Observations:\n", "subheader")
            self.result_text.insert(tk.END, vision_findings + "\n", "finding")

            self.result_text.insert(tk.END, "\n💬 Educational Interpretation:\n", "subheader")
            self.result_text.insert(tk.END, explanation + "\n\n", "explanation")
            self.result_text.insert(tk.END,
                "⚠️ SAFETY REMINDER:\n"
                "• This tool is for academic demonstration only.\n"
                "• NEVER use it for real patient diagnosis or treatment.\n"
                "• Always consult a board-certified radiologist or physician.\n",
                "warning"
            )

            # Configure text tags
            self.result_text.tag_config("header", font=("Segoe UI", 12, "bold"), foreground="#2c3e50")
            self.result_text.tag_config("subheader", font=("Segoe UI", 10, "bold"), foreground="#1a5276")
            self.result_text.tag_config("finding", font=("Segoe UI", 10, "italic"), foreground="#555")
            self.result_text.tag_config("explanation", font=("Segoe UI", 10), foreground="#2c3e50")
            self.result_text.tag_config("warning", font=("Segoe UI", 10, "bold"), foreground="#e74c3c")

            self.status_var.set("✅ Analysis complete. Review results carefully.")

        except Exception as e:
            error_msg = f"❌ Analysis failed:\n{e}"
            self.result_text.configure(state="normal")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, error_msg)
            self.result_text.configure(state="disabled")
            self.status_var.set("❌ Analysis failed. Check if Ollama is running.")
            messagebox.showerror("Error", str(e))
        finally:
            self.analyze_btn.config(state="normal")

# ======================
# 🚀 Main Entry
# ======================

if __name__ == "__main__":
    # Check if Ollama is running
    try:
        requests.get("http://localhost:11434", timeout=3)
    except requests.exceptions.ConnectionError:
        print("\n⚠️  ERROR: Ollama server not found at http://localhost:11434.")
        print("   Please make sure Ollama is running on your local machine.")
        print("   You can download it from https://ollama.com")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    root = tk.Tk()
    app = MedScanExplorer(root)
    root.mainloop()