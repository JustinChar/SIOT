import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# File path for the combined data
combined_file = "/Users/bocai/Desktop/Sensing and Internet of Things/Analysis/28NOVNight.csv"

# Load combined data
def load_combined_data(file):
    try:
        # Load the data from the CSV file
        data = pd.read_csv(file)
        data["Timestamp"] = pd.to_datetime(data["Timestamp"], format="%Y-%m-%d %H:%M:%S")
        print("Combined data loaded successfully!")
        return data
    except FileNotFoundError:
        print(f"File {file} not found.")
        exit()
        data["Attention Score"] = 1 - abs(data["Average EAR"] - 0.25) / 0.30 - (data["Left Speed"] + data["Right Speed"]) / (2 * 300)
        data["Attention Score"] = data["Attention Score"].clip(lower=0, upper=1)  # Restrict values to the range [0, 1]

        # Plot the attention curve
        plt.figure(figsize=(12, 6))
        plt.plot(data["Timestamp"], data["Attention Score"], marker='o', linestyle='-', label="Attention Score")
        plt.axhline(y=0.5, color="red", linestyle="--", label="Threshold")  # Add threshold line
        plt.title("Attention Curve Over Time", fontsize=16)
        plt.xlabel("Time", fontsize=12)
        plt.ylabel("Attention Score", fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.close()
    
# Plot Eye Movement Hotspot Map
def plot_hotspot_map(data):
    left_eye_coords = data[["Left Eye X", "Left Eye Y"]].values
    right_eye_coords = data[["Right Eye X", "Right Eye Y"]].values
    all_coords = np.vstack((left_eye_coords, right_eye_coords))

    heatmap, xedges, yedges = np.histogram2d(
        all_coords[:, 0], all_coords[:, 1], bins=(100, 100)
    )
    plt.figure(figsize=(8, 6))
    plt.imshow(heatmap.T, origin="lower", cmap="hot", extent=[0, 1920, 0, 1080])  # Adjust extent to match resolution
    plt.colorbar(label="Frequency")
    plt.title("Eye Movement Hotspot Map")
    plt.xlabel("Horizontal Position (pixels)")
    plt.ylabel("Vertical Position (pixels)")
    plt.tight_layout()
    plt.show()

# Plot Speed Over Time
def plot_speed_over_time(data):
    timestamps = data["Timestamp"]
    left_speeds = data["Left Speed"]
    right_speeds = data["Right Speed"]

    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, left_speeds, label="Left Eye Speed", linewidth=2)
    plt.plot(timestamps, right_speeds, label="Right Eye Speed", linewidth=2)
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%H:%M:%S"))
    plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
    plt.title("Eye Movement Speed Over Time")
    plt.xlabel("Time (HH:MM:SS)")
    plt.ylabel("Speed (pixels/second)")
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Plot EAR Over Time with Averages
def plot_ear_over_time(data):
    timestamps = data["Timestamp"]
    avg_ears = data["Average EAR"]

    # Calculate 3-minute averages
    data.set_index("Timestamp", inplace=True)
    rolling_3min_avg = data["Average EAR"].resample("3min").mean()  # Updated to "10min"

    # Overall average EAR
    overall_avg_ear = avg_ears.mean()

    # Reset index
    data.reset_index(inplace=True)

    # Plot EAR over time
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
    plt.show()



# Plot Cumulative Blink Count Over Time
def plot_cumulative_blinks(data):
    timestamps = data["Timestamp"]
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
    plt.show()

# Plot Blink Frequency in Intervals
def plot_blink_frequency(data):
    timestamps = data["Timestamp"]
    blink_counts = data["Blink Count"]

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
    plt.show()

# Main function to generate all plots
def generate_all_plots(file):
    # Load data
    data = load_combined_data(file)

    # Generate plots
    plot_hotspot_map(data)
    plot_speed_over_time(data)
    plot_ear_over_time(data)
    plot_cumulative_blinks(data)
    plot_blink_frequency(data)

# Call the main function
generate_all_plots(combined_file)
