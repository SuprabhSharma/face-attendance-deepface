from flask import Flask, render_template, request, jsonify
import cv2
import os
import numpy as np
import face_recognition
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Folder for storing faces
path = 'faces'
images = []
names = []
sections = []

# Ensure 'faces' folder exists
if not os.path.exists(path):
    os.makedirs(path)

# 1. Load images from sub-folders (Section wise)
def load_images():
    images.clear()
    names.clear()
    sections.clear()
    
    # os.walk automatically goes inside sub-folders
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(('.jpg', '.jpeg', '.png')):
                img = cv2.imread(os.path.join(root, file))
                if img is not None:
                    images.append(img)
                    names.append(os.path.splitext(file)[0])
                    sections.append(os.path.basename(root))  # Folder name is section

# 2. Encode faces
def encode_faces(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        if len(encodings) > 0:
            encodeList.append(encodings[0])
    return encodeList

@app.route('/')
def index():
    return "Face Recognition Attendance System with Section Support"

# 3. Register Face Route
@app.route('/register', methods=['POST'])
def register():
    # Using request.form.get to avoid KeyError
    name = request.form.get('name')
    section = request.form.get('section')

    if not name or not section:
        return "Error: Please provide both 'name' and 'section' in form-data!", 400
    
    name = name.strip()
    section = section.strip().upper()

    # Create section folder
    section_path = os.path.join(path, section)
    if not os.path.exists(section_path):
        os.makedirs(section_path)

    load_images()
    encodeListKnown = encode_faces(images) if len(images) > 0 else []

    cap = cv2.VideoCapture(0)
    msg = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            msg = "Error: Camera access failed."
            break
            
        cv2.putText(frame, f"Registering: {name} | Section: {section}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Register Face - Press 'q' to Capture", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(img_rgb)
            
            if len(face_locations) == 0:
                msg = "Error: No face detected!"
                break
                
            new_encode = face_recognition.face_encodings(img_rgb, face_locations)[0]
            
            # Duplicate check
            duplicate_found = False
            if len(encodeListKnown) > 0:
                matches = face_recognition.compare_faces(encodeListKnown, new_encode, tolerance=0.5)
                if True in matches:
                    matchIndex = matches.index(True)
                    existing_name = names[matchIndex]
                    existing_sec = sections[matchIndex]
                    duplicate_found = True
                    msg = f"Failed! This face is already registered as '{existing_name}' in Section '{existing_sec}'."
                    break

            if not duplicate_found:
                # Save image in section folder
                img_path = os.path.join(section_path, f'{name}.jpg')
                cv2.imwrite(img_path, frame)
                msg = f"Success! '{name}' registered successfully in Section '{section}'."
                break

    cap.release()
    cv2.destroyAllWindows()
    return msg

# 4. Attendance Route
@app.route('/attendance')
def attendance():
    load_images()
    if len(images) == 0:
        return "Error: No registered faces. Please register first."
        
    encodeListKnown = encode_faces(images)
    cap = cv2.VideoCapture(0)

    while True:
        success, img = cap.read()
        if not success: break
            
        imgS = cv2.resize(img, (0,0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

        facesCurFrame = face_recognition.face_locations(imgS)
        encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

        for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

            if len(faceDis) > 0:
                matchIndex = np.argmin(faceDis)
                if matches[matchIndex]:
                    matched_name = names[matchIndex].upper()
                    matched_section = sections[matchIndex]
                    mark_attendance(matched_name, matched_section)
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    return f"Attendance Marked: {matched_name} (Section: {matched_section})"

        cv2.imshow("Attendance - Press 'q' to Quit", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
    return "Attendance Closed."

# 5. Save Attendance Logic
def mark_attendance(name, section):
    file_name = 'attendance.csv'
    # Add headers if file is new
    if not os.path.isfile(file_name):
        with open(file_name, 'w') as f:
            f.write('Name,Section,Date,Time\n')

    with open(file_name, 'a') as f:
        now = datetime.now()
        f.write(f"{name},{section},{now.strftime('%Y-%m-%d')},{now.strftime('%H:%M:%S')}\n")

if __name__ == "__main__":
    app.run(debug=True)