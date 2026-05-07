import time
import csv
import os
import platform
import threading
from datetime import datetime
from ultralytics import YOLO
import cv2
import tkinter as tk
from tkinter import ttk, scrolledtext
import pyttsx3
 

def beep(freq, duration_ms):
    system = platform.system()
    if system == "Windows":
        import winsound
        winsound.Beep(freq, duration_ms)
    else:
        # Linux / Mac — use terminal bell as fallback
        print('\a', end='', flush=True)
 

engine_lock = threading.Lock()
 
def speak(text):
    def _speak():
        with engine_lock:
            try:
                tts = pyttsx3.init()
                tts.setProperty('rate', 160)
                tts.say(text)
                tts.runAndWait()
            except Exception:
                pass
    threading.Thread(target=_speak, daemon=True).start()

LOG_FILE = "detection_log.csv"
 
def init_csv():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Object", "Risk Level", "Risk Score"])
 
def log_detection(label, risk_level, score):
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), label, risk_level, f"{score:.4f}"])
 
severity_map = {
    
    "car": 5, "bus": 5, "truck": 5, "train": 5,
    "motorbike": 4, "motorcycle": 4,
    "bicycle": 3,
    "boat": 3, "airplane": 5,
 
    
    "person": 3,
 
    
    "dog": 3, "cat": 2, "horse": 4, "cow": 4, "sheep": 2, "bird": 1,
 
    
    "chair": 1, "bottle": 1, "cup": 1, "laptop": 1,
    "backpack": 1, "handbag": 1, "suitcase": 2,
    "umbrella": 1, "bench": 2, "table": 2,
 
  
    "sports ball": 1, "skateboard": 2, "surfboard": 2,
 
    
    "knife": 5, "scissors": 3, "fire hydrant": 2,
}
 
class RiskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚨 Real-Time Risk Detection System")
        self.root.configure(bg="#0d0d0d")
        self.root.geometry("900x650")
        self.root.resizable(False, False)
 
        header = tk.Frame(root, bg="#0d0d0d")
        header.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(header, text="🚨 Real-Time Risk Detection System",
                 font=("Courier New", 18, "bold"), fg="#00ff88", bg="#0d0d0d").pack(side="left")
        self.status_label = tk.Label(header, text="● RUNNING",
                                     font=("Courier New", 11), fg="#00ff88", bg="#0d0d0d")
        self.status_label.pack(side="right")
 
        
        risk_frame = tk.Frame(root, bg="#111111", relief="flat", bd=0)
        risk_frame.pack(fill="x", padx=20, pady=8)
 
        self.risk_label = tk.Label(risk_frame, text="NO OBJECT DETECTED",
                                   font=("Courier New", 22, "bold"),
                                   fg="#ffffff", bg="#111111", pady=15)
        self.risk_label.pack()
 
        self.score_label = tk.Label(risk_frame, text="Risk Score: 0.0000",
                                    font=("Courier New", 12), fg="#888888", bg="#111111")
        self.score_label.pack(pady=(0, 10))
 
        
        bar_frame = tk.Frame(root, bg="#0d0d0d")
        bar_frame.pack(fill="x", padx=20, pady=4)
        tk.Label(bar_frame, text="RISK METER", font=("Courier New", 9),
                 fg="#555555", bg="#0d0d0d").pack(anchor="w")
        self.progress = ttk.Progressbar(bar_frame, orient="horizontal",
                                        length=860, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=4)
 
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor="#1a1a1a",
                        background="#00ff88", thickness=18)
 
        # ── Stats Row ──
        stats_frame = tk.Frame(root, bg="#0d0d0d")
        stats_frame.pack(fill="x", padx=20, pady=6)
 
        self.total_label   = self._stat_box(stats_frame, "TOTAL DETECTIONS", "0")
        self.high_label    = self._stat_box(stats_frame, "HIGH RISK", "0", "#ff4444")
        self.medium_label  = self._stat_box(stats_frame, "MEDIUM RISK", "0", "#ff9900")
        self.low_label     = self._stat_box(stats_frame, "LOW RISK", "0", "#00ff88")
 
        log_frame = tk.Frame(root, bg="#0d0d0d")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(4, 10))
        tk.Label(log_frame, text="DETECTION LOG", font=("Courier New", 9),
                 fg="#555555", bg="#0d0d0d").pack(anchor="w")
        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=10, bg="#111111", fg="#cccccc",
            font=("Courier New", 10), bd=0, relief="flat", state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)
 
       
        btn_frame = tk.Frame(root, bg="#0d0d0d")
        btn_frame.pack(fill="x", padx=20, pady=(0, 12))
 
        self.voice_var = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_frame, text="🔊 Voice Alerts",
                       variable=self.voice_var,
                       font=("Courier New", 10), fg="#aaaaaa",
                       bg="#0d0d0d", activebackground="#0d0d0d",
                       selectcolor="#0d0d0d").pack(side="left", padx=5)
 
        tk.Button(btn_frame, text="📂 Open Log CSV",
                  command=self.open_log,
                  font=("Courier New", 10), fg="#00ff88",
                  bg="#1a1a1a", relief="flat", padx=10, pady=4).pack(side="right", padx=5)
 
        tk.Button(btn_frame, text="🛑 Stop",
                  command=self.stop,
                  font=("Courier New", 10), fg="#ff4444",
                  bg="#1a1a1a", relief="flat", padx=10, pady=4).pack(side="right", padx=5)
 
        
        self.running = True
        self.total = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0
        self.last_alert_time = 0
 
    def _stat_box(self, parent, title, value, color="#ffffff"):
        frame = tk.Frame(parent, bg="#111111", padx=15, pady=8)
        frame.pack(side="left", expand=True, fill="x", padx=4)
        tk.Label(frame, text=title, font=("Courier New", 8),
                 fg="#555555", bg="#111111").pack()
        lbl = tk.Label(frame, text=value, font=("Courier New", 20, "bold"),
                       fg=color, bg="#111111")
        lbl.pack()
        return lbl
 
    def update_risk(self, label, risk_level, score):
        colors = {
            "HIGH RISK":   ("#ff4444", "#ff0000"),
            "MEDIUM RISK": ("#ff9900", "#ff6600"),
            "LOW RISK":    ("#00ff88", "#00cc66"),
            "NONE":        ("#ffffff", "#888888"),
        }
        text_color, _ = colors.get(risk_level, ("#ffffff", "#888888"))
 
        display = f"{label.upper()}  —  {risk_level}" if label != "NONE" else "NO OBJECT DETECTED"
        self.risk_label.config(text=display, fg=text_color)
        self.score_label.config(text=f"Risk Score: {score:.4f}")
        self.progress["value"] = min(score * 300, 100)
 
        
        if risk_level != "NONE":
            self.total += 1
            self.total_label.config(text=str(self.total))
            if risk_level == "HIGH RISK":
                self.high_count += 1
                self.high_label.config(text=str(self.high_count))
            elif risk_level == "MEDIUM RISK":
                self.medium_count += 1
                self.medium_label.config(text=str(self.medium_count))
            else:
                self.low_count += 1
                self.low_label.config(text=str(self.low_count))
 
        
        if risk_level != "NONE":
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] {label:<12} → {risk_level}  (score: {score:.4f})\n"
            self.log_box.config(state="normal")
            self.log_box.insert("end", entry)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
 
    def open_log(self):
        system = platform.system()
        if system == "Windows":
            os.startfile(LOG_FILE)
        elif system == "Darwin":
            os.system(f"open {LOG_FILE}")
        else:
            os.system(f"xdg-open {LOG_FILE}")
 
    def stop(self):
        self.running = False
        self.root.destroy()
 
 

def run_detection(app):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(0)
    init_csv()
 
    while app.running:
        ret, frame = cap.read()
        if not ret:
            break
 
        results = model(frame, verbose=False)
        frame_area = frame.shape[0] * frame.shape[1]
        risk_scores = []
 
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label  = model.names[cls_id]
                severity = severity_map.get(label, 1)
                x1, y1, x2, y2 = box.xyxy[0]
                box_area = (x2 - x1) * (y2 - y1)
                distance_factor = box_area / frame_area
                risk_score = severity * distance_factor
                risk_scores.append((label, risk_score))
 
        current_time = time.time()
        risk_level = "NONE"
        top_label  = "NONE"
        top_score  = 0.0
 
        if risk_scores:
            top_label, top_score = max(risk_scores, key=lambda x: x[1])
 
            if top_score > 0.20:
                risk_level = "HIGH RISK"
                color = (0, 0, 255)
                if current_time - app.last_alert_time > 2:
                    threading.Thread(target=beep, args=(1000, 500), daemon=True).start()
                    if app.voice_var.get():
                        speak(f"Warning! {top_label} detected. High risk!")
                    log_detection(top_label, risk_level, top_score)
                    app.last_alert_time = current_time
 
            elif top_score > 0.05:
                risk_level = "MEDIUM RISK"
                color = (0, 165, 255)
                if current_time - app.last_alert_time > 2:
                    threading.Thread(target=beep, args=(700, 400), daemon=True).start()
                    if app.voice_var.get():
                        speak(f"{top_label} nearby. Medium risk.")
                    log_detection(top_label, risk_level, top_score)
                    app.last_alert_time = current_time
 
            else:
                risk_level = "LOW RISK"
                color = (0, 255, 0)
                if current_time - app.last_alert_time > 2:
                    threading.Thread(target=beep, args=(400, 200), daemon=True).start()
                    if app.voice_var.get():
                        speak(f"{top_label} detected. Low risk.")
                    log_detection(top_label, risk_level, top_score)
                    app.last_alert_time = current_time
        else:
            color = (0, 255, 0)
 
        
        app.root.after(0, app.update_risk, top_label, risk_level, top_score)
 
        
        annotated = results[0].plot()
        risk_text = f"{top_label} - {risk_level}" if top_label != "NONE" else "NO OBJECT"
        cv2.putText(annotated, risk_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        cv2.imshow("Detection - Press Q / ESC to Exit", annotated)
 
        key = cv2.waitKey(10) & 0xFF
        if key in (ord('q'), 27):
            app.running = False
            break
 
    cap.release()
    cv2.destroyAllWindows()
    try:
        app.root.destroy()
    except Exception:
        pass
 
 

if __name__ == "__main__":
    root = tk.Tk()
    app = RiskApp(root)
 
    # Run detection in background thread
    detection_thread = threading.Thread(target=run_detection, args=(app,), daemon=True)
    detection_thread.start()
 
    root.mainloop()