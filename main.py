import winsound
import time
from ultralytics import YOLO
import cv2

# Load YOLO model
model = YOLO("yolov8n.pt")

# Start camera
cap = cv2.VideoCapture(0)

# Severity mapping
severity_map = {
    "person": 3,
    "car": 5,
    "bus": 5,
    "truck": 5,
    "motorbike": 4,
    "bicycle": 2,
    "chair": 1,
    "bottle": 1
}

last_alert_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera error")
        break

    results = model(frame, verbose=False)
    risk_scores = []

    frame_area = frame.shape[0] * frame.shape[1]

    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]

            severity = severity_map.get(label, 1)

            x1, y1, x2, y2 = box.xyxy[0]
            box_area = (x2 - x1) * (y2 - y1)

            distance_factor = box_area / frame_area
            risk_score = severity * distance_factor

            risk_scores.append((label, risk_score))

    risk_text = "NO OBJECT"
    color = (0, 255, 0)

    if risk_scores:
        highest_risk = max(risk_scores, key=lambda x: x[1])
        label, score = highest_risk

        current_time = time.time()

        if score > 0.20:
            risk_level = "HIGH RISK"
            color = (0, 0, 255)

            if current_time - last_alert_time > 2:
                winsound.Beep(1000, 500)
                last_alert_time = current_time

        elif score > 0.05:
            risk_level = "MEDIUM RISK"
            color = (0, 165, 255)

            if current_time - last_alert_time > 2:
                winsound.Beep(700, 400)
                last_alert_time = current_time

        else:
            risk_level = "LOW RISK"
            color = (0, 255, 0)

            if current_time - last_alert_time > 2:
                winsound.Beep(400, 200)
                last_alert_time = current_time

        risk_text = f"{label} - {risk_level}"

    annotated_frame = results[0].plot()

    cv2.putText(
        annotated_frame,
        risk_text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        3
    )

    cv2.imshow("Detection - Press Q to Exit", annotated_frame)

    key = cv2.waitKey(10) & 0xFF

    if key == ord('q'):
        print("Q pressed - Closing...")
        break

    if key == 27:  # ESC
        print("ESC pressed - Closing...")
        break

cap.release()
cv2.destroyAllWindows()