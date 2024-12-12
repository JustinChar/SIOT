import cv2
import mediapipe as mp
import numpy as np
import time
import csv

# Initialize Mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# EAR calculation function
def calculate_ear(eye):
    A = np.linalg.norm(eye[1] - eye[5])  # Vertical distance 1
    B = np.linalg.norm(eye[2] - eye[4])  # Vertical distance 2
    C = np.linalg.norm(eye[0] - eye[3])  # Horizontal distance
    return (A + B) / (2.0 * C)

# Calculate eye center
def calculate_eye_center(eye):
    x_coords = [point[0] for point in eye]
    y_coords = [point[1] for point in eye]
    center_x = int(sum(x_coords) / len(x_coords))
    center_y = int(sum(y_coords) / len(y_coords))
    return center_x, center_y

# Define left and right eye landmarks
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Parameter settings
EAR_THRESHOLD_LOW = 0.21  # Low EAR threshold
EAR_THRESHOLD_HIGH = 0.23   # High EAR threshold
FPS = 60  # Camera frame rate
RECORD_INTERVAL = 1  # Record all data every second

# Initialize variables
blink_count = 0
blink_in_progress = False  # Track blink status
last_record_time = time.time()  # Start time for recording

# Initialize combined CSV file
output_csv_file = "inputfilename.csv"
try:
    with open(output_csv_file, mode='x', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp", "Left Eye X", "Left Eye Y", "Right Eye X", "Right Eye Y",
            "Left Speed", "Right Speed", "Average EAR", "Blink Count"
        ])  # Write header
except FileExistsError:
    pass

# Initialize camera
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FPS, FPS)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Previous eye center and time
prev_left_eye_center = None
prev_right_eye_center = None
prev_time = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to RGB image
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            height, width, _ = frame.shape
            landmarks = np.array([(int(point.x * width), int(point.y * height))
                                   for point in face_landmarks.landmark])

            # Extract left and right eye landmarks
            left_eye = landmarks[LEFT_EYE]
            right_eye = landmarks[RIGHT_EYE]

            # Calculate EAR for both eyes
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)
            avg_ear = (left_ear + right_ear) / 2.0

            # Blink detection logic with optimization
            if left_ear < EAR_THRESHOLD_LOW or right_ear < EAR_THRESHOLD_LOW:  # Start of a blink (either eye)
                blink_in_progress = True
            elif left_ear > EAR_THRESHOLD_HIGH and right_ear > EAR_THRESHOLD_HIGH and blink_in_progress:  # End of a blink
                blink_count += 1
                blink_in_progress = False
                print(f"Blink detected at {time.strftime('%Y-%m-%d %H:%M:%S')}! Total blinks: {blink_count}")

            # Calculate eye centers
            left_eye_center = calculate_eye_center(left_eye)
            right_eye_center = calculate_eye_center(right_eye)

            # Calculate movement speed
            current_time = time.time()
            if prev_left_eye_center and prev_right_eye_center and prev_time:
                time_delta = current_time - prev_time
                left_speed = np.linalg.norm(np.array(left_eye_center) - np.array(prev_left_eye_center)) / time_delta
                right_speed = np.linalg.norm(np.array(right_eye_center) - np.array(prev_right_eye_center)) / time_delta
            else:
                left_speed, right_speed = 0, 0

            prev_left_eye_center = left_eye_center
            prev_right_eye_center = right_eye_center
            prev_time = current_time

            # Record all data every second
            if current_time - last_record_time >= RECORD_INTERVAL:
                with open(output_csv_file, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)),
                        left_eye_center[0], left_eye_center[1],
                        right_eye_center[0], right_eye_center[1],
                        left_speed, right_speed, avg_ear, blink_count
                    ])
                last_record_time = current_time

            # Draw green keypoints for eyes
            for eye in [left_eye, right_eye]:
                for point in eye:
                    cv2.circle(frame, tuple(point), 2, (0, 255, 0), -1)

            # Display EAR and blink count
            cv2.putText(frame, f"EAR: {avg_ear:.2f}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.putText(frame, f"Blinks: {blink_count}", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Display the frame
    cv2.imshow("Blink and EAR Detection", frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print(f"Combined data saved to {output_csv_file}")
