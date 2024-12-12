import cv2
import os
import numpy as np
import mediapipe as mp
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_pdf import PdfPages
import threading
import time
import csv
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage

# Set the files, output csv and output pdf
name = datetime.now().strftime("%Y%m%d_%H%M%S")
outcsv = f"{name}.csv"
outpdf = f"{name}_FocusReport.pdf"

with open(outcsv, mode='x', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([
        "Timestamp", "Left Eye X", "Left Eye Y", "Right Eye X", "Right Eye Y", "Left Speed", "Right Speed", "Average EAR", "Blink Count"
    ])

# Initialize Mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# EAR calculation
def Ear(eye):
    A = np.linalg.norm(eye[1] - eye[5])  # Vertical distance 1
    B = np.linalg.norm(eye[2] - eye[4])  # Vertical distance 2
    C = np.linalg.norm(eye[0] - eye[3])  # Horizontal distance
    return (A + B) / (2.0 * C)

# Calculate eye center
def Eyecentre(eye):
    x_coords = [point[0] for point in eye]
    y_coords = [point[1] for point in eye]
    xcentre = int(sum(x_coords) / len(x_coords))
    ycentre = int(sum(y_coords) / len(y_coords))
    return xcentre, ycentre

# Define left and right eye landmarks
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Attention data, set as the initial value
attention = { "ear": 0.0, "speed": 0.0, "focus_score": 0.5, "prev_ear": 0.5, "prev_speed": 0.5, "prev_focus_score": 0.5 }

# Initialize the dashboard
fig, ax = plt.subplots(3, 1, figsize=(6, 8))
fig.suptitle("Attention Monitoring Dashboard")
p_ear = ax[0].barh(0, 0, color="green", align="center")
p_speed = ax[1].barh(0, 0, color="green", align="center")
p_focus = ax[2].barh(0, 0, color="blue", align="center")
for i, a in enumerate(ax):
    a.set_xlim(0, 1)
    a.set_ylim(-0.5, 0.5)
    if i == 0:
        a.axvline(x=0.25 / 0.30, color="red", linestyle="--", label="Fatigue Threshold")
        a.set_title("EAR")
    elif i == 1:
        a.axvline(x=150 / 300, color="red", linestyle="--", label="Fatigue Threshold")
        a.set_title("Speed")
    else:
        a.axvline(x=0.5, color="yellow", linestyle="--", label="Threshold")
        a.set_title("Focus Score")
    a.legend(loc="upper right")
    a.axis("off")

# Function to limit change, avoide error and the dashboard changes too quickly
def smoothchange(current, target, change):
    if abs(current - target) > change:
        return current + change if target > current else current - change
    return target

# Update dashboard
def updatedashboard(frame):
    global attention
    ear_value = max(0, min(attention["ear"] / 0.30, 1))
    ear_value = smoothchange(attention["prev_ear"], ear_value, 0.05)
    attention["prev_ear"] = ear_value
    p_ear[0].set_width(ear_value)
    p_ear[0].set_color("red" if attention["ear"] < 0.25 else "green")

    speed_value = max(0, min(attention["speed"] / 300, 1))
    attention["prev_speed"] = speed_value
    p_speed[0].set_width(speed_value)
    p_speed[0].set_color("red" if attention["speed"] > 150 else "green")

    focus_score = 1 - abs(attention["ear"] - 0.25) / 0.30 - attention["speed"] / 300
    focus_score = max(0, min(focus_score, 1))
    attention["prev_focus_score"] = focus_score
    p_focus[0].set_width(focus_score)
    p_focus[0].set_color("blue" if focus_score > 0.5 else "red")

    return p_ear, p_speed, p_focus

# Animation setup
ani = FuncAnimation(fig, updatedashboard, interval=500, cache_frame_data=False)

# Eye detection thread
def detectionthread():
    global attention

    # Camera initialization
    cap = cv2.VideoCapture(1)  # Adjust camera index
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    blinkcounter = 0
    blinking = False
    pre_leyecentre = pre_reyecentre = None
    pretime = lastime = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                height, width, _ = frame.shape
                landmarks = np.array([(int(point.x * width), int(point.y * height))
                                       for point in face_landmarks.landmark])

                leye = landmarks[LEFT_EYE]
                reye = landmarks[RIGHT_EYE]

                lear = Ear(leye)
                rear = Ear(reye)
                averagear = (lear + rear) / 2.0

                if lear < 0.21 or rear < 0.21:
                    blinking = True
                elif lear > 0.23 and rear > 0.23 and blinking:
                    blinkcounter += 1
                    blinking = False

                leyecentre = Eyecentre(leye)
                reyecentre = Eyecentre(reye)

                currentime = time.time()
                if pre_leyecentre and pre_reyecentre and pretime:
                    time_delta = currentime - pretime
                    lspeed = np.linalg.norm(np.array(leyecentre) - np.array(pre_leyecentre)) / time_delta
                    rspeed = np.linalg.norm(np.array(reyecentre) - np.array(pre_reyecentre)) / time_delta
                else:
                    lspeed = rspeed = 0

                averagespeed = (lspeed + rspeed) / 2.0
                attention["ear"] = averagear
                attention["speed"] = averagespeed

                pre_leyecentre, pre_reyecentre = leyecentre, reyecentre
                pretime = currentime

                if currentime - lastime >= 1:
                    with open(outcsv, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            time.strftime("%Y-%m-%d %H:%M:%S"),
                            leyecentre[0], leyecentre[1],
                            reyecentre[0], reyecentre[1],
                            lspeed, rspeed, averagear, blinkcounter
                        ])
                    lastime = currentime

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Start the eye detection thread
thread = threading.Thread(target=detectionthread, daemon=True)
thread.start()

# Display the dashboard
plt.show()

# Load combined data
def readata(file):
    try:
        data = pd.read_csv(file)
        data["Timestamp"] = pd.to_datetime(data["Timestamp"], format="%Y-%m-%d %H:%M:%S")
        print("Combined data loaded successfully!")
        return data
    except FileNotFoundError:
        print(f"File {file} not found.")
        exit()

# Generate plots and save to PDF
def createpdf(file, pdf_file):
    data = readata(file)
    leyecoords = data[["Left Eye X", "Left Eye Y"]].values
    reyecoords = data[["Right Eye X", "Right Eye Y"]].values
    allcoords = np.vstack((leyecoords, reyecoords))

    with PdfPages(pdf_file) as pdf:
        # Calculate attention score (based on the EAR and speed formula)
        data["Attention Score"] = 1 - abs(data["Average EAR"] - 0.25) / 0.30 - (data["Left Speed"] + data["Right Speed"]) / (2 * 300)
        data["Attention Score"] = data["Attention Score"].clip(lower=0, upper=1)  # Restrict values to the range [0, 1]
        # Calculate 3-minute rolling average line
        data.set_index("Timestamp", inplace=True)
        rolling_fit_curve = data["Attention Score"].resample("3min").mean()
        data.reset_index(inplace=True)

        # Plot the attention curve
        plt.figure(figsize=(12, 6))
        plt.plot(data["Timestamp"], data["Attention Score"], marker='o', linestyle='-', label="Attention Score", alpha=0.7)
        plt.plot(
            rolling_fit_curve.index, rolling_fit_curve.values, linestyle='--', color="orange", label="3-Minute Fit Curve"
        )
        plt.axhline(y=0.5, color="red", linestyle="--", label="Threshold")  # Add threshold line
        plt.title("Attention Curve Over Time", fontsize=16)
        plt.xlabel("Time", fontsize=12)
        plt.ylabel("Attention Score", fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        pdf.savefig()
        plt.close()


        # Plot Eye Movement Hotspot Map
        heatmap, xedges, yedges = np.histogram2d(
            allcoords[:, 0], allcoords[:, 1], bins=(100, 100)
        )
        plt.figure(figsize=(12, 6))
        plt.imshow(heatmap.T, origin="lower", cmap="hot", extent=[0, 1920, 0, 1080])
        plt.colorbar(label="Frequency")
        plt.title("Eye Movement Hotspot Map")
        plt.xlabel("Horizontal Position (pixels)")
        plt.ylabel("Vertical Position (pixels)")
        plt.tight_layout()
        pdf.savefig()
        plt.close()

        # Plot Speed Over Time
        timestamps = data["Timestamp"]
        lspeeds = data["Left Speed"]
        rspeeds = data["Right Speed"]

        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, lspeeds, label="Left Eye Speed", linewidth=2)
        plt.plot(timestamps, rspeeds, label="Right Eye Speed", linewidth=2)
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M:%S"))
        plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
        plt.title("Eye Movement Speed Over Time")
        plt.xlabel("Time (HH:MM:SS)")
        plt.ylabel("Speed (pixels/second)")
        plt.legend()
        plt.grid()
        plt.xticks(rotation=45)
        plt.tight_layout()
        pdf.savefig()
        plt.close()

        # Plot EAR Over Time with Averages
        avg_ears = data["Average EAR"]

        # Calculate 3-minute averages
        data.set_index("Timestamp", inplace=True)
        rolling_3min_avg = data["Average EAR"].resample("3min").mean()
        overall_avg_ear = avg_ears.mean()
        data.reset_index(inplace=True)

        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, avg_ears, label="Average EAR", color="blue", linewidth=2)
        plt.plot(
            rolling_3min_avg.index, rolling_3min_avg.values, label="3-Minute Average EAR", color="orange", linewidth=2
        )
        plt.axhline(overall_avg_ear, color="red", linestyle="--", linewidth=2, label="Overall Average EAR")
        plt.title("EAR (Eye Aspect Ratio) Over Time")
        plt.xlabel("Time (HH:MM:SS)")
        plt.ylabel("EAR")
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)
        plt.grid()
        plt.legend()
        plt.tight_layout()
        pdf.savefig()
        plt.close()

        # Plot Cumulative Blink Count Over Time
        blink_counts = data["Blink Count"]
        cumulative_blinks = blink_counts.cumsum()

        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, cumulative_blinks, label="Cumulative Blink Count", color="green", linewidth=2)
        plt.title("Cumulative Blink Count Over Time")
        plt.xlabel("Time (HH:MM:SS)")
        plt.ylabel("Cumulative Blink Count")
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)
        plt.grid()
        plt.legend()
        plt.tight_layout()
        pdf.savefig()
        plt.close()

        # Plot Blink Frequency in Intervals
        plt.figure(figsize=(12, 6))
        plt.bar(timestamps, blink_counts, width=0.01, label="Blink Frequency", color="purple")
        plt.title("Blink Frequency in Intervals")
        plt.xlabel("Time (HH:MM:SS)")
        plt.ylabel("Blink Count")
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)
        plt.grid()
        plt.legend()
        plt.tight_layout()
        pdf.savefig()
        plt.close()

    print(f"All plots saved to {pdf_file}")


# Initialize Firebase Admin SDK (Ensure the credentials JSON file is available)
cred = credentials.Certificate("/Users/bocai/Desktop/Sensing and Internet of Things/serviceaccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'siot-2bfb8.firebasestorage.app'  # Replace with your Firebase project's storage bucket
})

# Generate plots and save to PDF
createpdf(outcsv, outpdf)


# Function to upload file to Firebase Storage and delete local file
def upload(local_file_path, folder_name):
    bucket = storage.bucket()
    blob = bucket.blob(f"{folder_name}/{os.path.basename(local_file_path)}")
    # Upload the file to Firebase Storage
    blob.upload_from_filename(local_file_path)
    print(f"Uploaded {local_file_path} to {folder_name}/ in Firebase Storage.")

# Upload CSV and PDF to Firebase Storage
try:
    upload(outcsv, "csv")  # Upload CSV to the "csv" folder
    upload(outpdf, "pdf")  # Upload PDF to the "pdf" folder
except Exception as e:
    print(f"Error uploading files to Firebase Storage: {e}")

