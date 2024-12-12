import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import ttk
import re
import subprocess

# JavaScript file path
jsfile = "/Users/bocai/Desktop/SIOT/functions/index.js"  # Update this with the actual file path

# Function to update the recipient's email in the JavaScript code
def updateaddress(neweaddress):
    with open(jsfile, "r") as file:
        js_code = file.read()
    updateone = re.sub(r"to: \".*?\"", f'to: "{neweaddress}"', js_code)

    with open(jsfile, "w") as file:
        file.write(updateone)
    return True

# Deployment function
def deploy():
    result = subprocess.run(["firebase", "deploy", "--only", "functions", "--project", "siot-2bfb8"], capture_output=True, text=True)
    if result.returncode == 0:
        print("Great!","Deployment successful.")
        messagebox.showinfo("Deployment Success", "Firebase Functions deployed successfully.")
    else:
        print(f"Deployment failed: {result.stderr}")
        messagebox.showerror("Something wrong","Deployment Error")

# Function to enable user change email address
def updatemail():
    newemail = simpledialog.askstring("Update Email", "Enter the new recipient's email address:")
    if newemail:
        if updateaddress(newemail):
            messagebox.showinfo("Success", f"Email updated to: {newemail}")
            deploy()
        else:
            messagebox.showerror("There is an error","Failed to update the email in the JavaScript file.")
    else:
        messagebox.showwarning("There is no input","Email address was not provided.")

# Function to set daily schedule to send the report to user
def schedule(dialog, timeset):
    timeset = timeset.get().strip()
    try:
        hours, minutes = map(int, timeset.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Please enter a time in HH:MM format.")
        return

    applytime = f"{minutes} {hours} * * *"
    job = "send-pdf-job"
    topic = "send-latest-pdf"
    text = "Trigger to send the latest PDF"
    location = "us-central1"

    gcloud_command = [
        "gcloud",
        "scheduler",
        "jobs",
        "update",
        "pubsub",
        job,
        "--topic", topic,
        "--schedule", applytime,
        "--message-body", text,
        "--location", location
    ]

    result = subprocess.run(gcloud_command, check=False, capture_output=True, text=True)
    if result.returncode == 0:
        messagebox.showinfo( "You have set the schedule successfully!",f"PDF will be sent at {timeset} everyday!")
        dialog.destroy()
    else:
        messagebox.showerror("Error","Fail to set schedule")

# Function to open the schedule dialog
def openschedule():
    # Create a new dialog window
    dialog = tk.Toplevel(ui)
    dialog.title("Schedule")
    dialog.geometry("600x400")
    dialog.resizable(False, False)

    # Instruction
    instru = ttk.Label(dialog, text="Enter the daily time (HH:MM):", font=("Arial", 20))
    instru.pack(pady=20)

    # Time input
    timeset = ttk.Entry(dialog, width=10, font=("Arial", 18))
    timeset.pack(pady=10)

    # Confirm button
    confirm = ttk.Button(
        dialog,
        text="Confirm",
        command=lambda: schedule(dialog, timeset),
        style="Custom.TButton"
    )
    confirm.pack(pady=20)

# Function to ask for a report right now
def requestreport():
    topic = "send-latest-pdf"
    message = "Trigger test"
    publish_command = [
        "gcloud",
        "pubsub",
        "topics",
        "publish",
        topic,
        "--message",
        message
    ]

    result = subprocess.run(publish_command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        messagebox.showinfo("Great!","Report has already sent to your Email")
    else:
        messagebox.showerror("Error", f"Failed to send report.\nDetails: {result.stderr}")

# Function to run Detect.py
def Startdetect():
    python3path = "/usr/local/bin/python3"
    codepath = "/Users/bocai/Desktop/SIOT/Detect.py"
    result = subprocess.run([python3path, codepath], check=False, capture_output=True, text=True)
    if result.returncode == 0:
        messagebox.showinfo("Good Job!","You finished a focus detection")
    else:
        messagebox.showerror("Error", "Error executing script.")

# Main GUI
ui = tk.Tk()
ui.title("SIOT FREE TRIAL")
ui.geometry("900x700")  # Adjust the window size
ui.resizable(True, True)

# UI fonts
style = ttk.Style()
style.configure("TLabel", font=("Arial", 22))
style.configure("TButton", font=("Arial", 20), padding=15)
style.configure("Custom.TButton", font=("Arial", 20), padding=15)

# Header
header = ttk.Label(ui, text="Focus Detection Platform", font=("Arial", 28, "bold"))
header.pack(pady=50)

# Set all Buttons
Startdetectbutton = ttk.Button(ui, text="Start Focus", command=Startdetect, style="Custom.TButton")
Startdetectbutton.pack(pady=20)

openschedulebutton = ttk.Button(ui, text="Set Schedule", command=openschedule, style="Custom.TButton")
openschedulebutton.pack(pady=20)

requestreportbutton = ttk.Button(ui, text="Send Report Now", command=requestreport, style="Custom.TButton")
requestreportbutton.pack(pady=20)

updatemailbutton = ttk.Button(ui, text="Change Email Address", command=updatemail, style="Custom.TButton")
updatemailbutton.pack(pady=20)

ui.mainloop()
