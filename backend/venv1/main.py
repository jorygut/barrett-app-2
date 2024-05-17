from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import math
import os
import xml.etree.ElementTree as ET
import cv2
from flask import send_file

app = Flask(__name__)
CORS(app)  # Allow all origins for simplicity
print('app_started')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/api/users", methods=['GET'])
def users():
    return jsonify({"users": ['joe', 'bob', 'jim']})

@app.route("/api/xml", methods=['POST'])
def read_xml_file(file):
    tree = ET.parse(file)
    root = tree.getroot()

    part_count = 0
    detection_count = 0
    tracks_info = {
        'nTracks': int(root.attrib['nTracks']),
        'spaceUnits': root.attrib['spaceUnits'],
        'frameInterval': float(root.attrib['frameInterval']),
        'timeUnits': root.attrib['timeUnits'],
        'generationDateTime': root.attrib['generationDateTime'],
        'from': root.attrib['from']
    }

    particle_data = []
    for particle in root.findall('./particle'):
        part_count += 1
        particle_info = {'nSpots': int(particle.attrib['nSpots'])}
        if particle_info['nSpots'] < 100:
            continue

        detections = []
        for detection in particle.findall('./detection'):
            detection_count += 1
            detection_info = {
                't': int(detection.attrib['t']),
                'x': float(detection.attrib['x']),
                'y': float(detection.attrib['y']),
                'z': float(detection.attrib['z']),
                'speed': math.sqrt(float(detection.attrib['x']) ** 2 + float(detection.attrib['y']) ** 2)
            }
            detections.append(detection_info)
        particle_info['detections'] = detections
        particle_data.append(particle_info)

    tracks_info['particles'] = particle_data
    return tracks_info
    
def detect_lighter_circles(image_path, par1, par2, lawn_count):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Preprocessing
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=2, minDist=100,
                               param1=par1, param2=par2, minRadius=10,
                               maxRadius=100)

    circle_data = []
    x_cords = {}
    y_cords = {}
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        if len(circles) == lawn_count:
            for (x, y, r) in circles:
                circle_coordinates = []
                for i in range(x - r, x + r + 1):
                    for j in range(y - r, y + r + 1):
                        if (i - x) ** 2 + (j - y) ** 2 <= r ** 2:
                            circle_coordinates.append((i, j))
                            x_cords[i] = 1
                            y_cords[j] = 1
                circle_data.append({
                    'center_x': x,
                    'center_y': y,
                    #'radius': r,
                    'coordinates': circle_coordinates
                })
        else:
            x_cords = 'fail'
            y_cords = 'fail'
    return x_cords,y_cords

def configure_circle(img,lawn_count):
    flag = False
    for param1 in range(10, 55):
        if flag:
            break
        for param2 in range(10, 55):
            x_cords, y_cords = detect_lighter_circles(img, param1, param2,lawn_count) 
            print(x_cords)
            if x_cords != 'fail':
                flag = True
                break  
    return x_cords,y_cords

def create_file(input_file,lawn_count, img):
    x_cords, y_cords = configure_circle(img,lawn_count)
    tracks_info = read_xml_file(input_file)
    particle_count = 0
    detection_count = 0

    part_df = pd.DataFrame()
    for i in tracks_info['particles']:
        detection_count = 0
        particle_count += 1
        for j in i['detections']:
            detection_count += 1
            if (int(j['x'] + 1) in x_cords or int(j['x'] - 1) in x_cords) and (int(j['y'] + 1) in y_cords or int(j['y'] - 1) in y_cords):
                part_df.at[detection_count,f'obs_{particle_count}_in_lawn'] = True
            else:
                part_df.at[detection_count,f'obs_{particle_count}_in_lawn'] = False
            part_df.at[detection_count,f'obs_{particle_count}_x'] = j['x']
            part_df.at[detection_count,f'obs_{particle_count}_y'] = j['y']
            part_df.at[detection_count,f'obs_{particle_count}_t'] = j['t']
            part_df.at[detection_count,f'obs_{particle_count}_z'] = j['z']
            part_df.at[detection_count,f'obs_{particle_count}_speed'] = j['speed']
    print(part_df)
    return part_df

@app.route('/image', methods=['POST'])
def upload_image_and_number():
    if 'image_file' not in request.files:
        return jsonify({"error": "No image file part in the request"}), 400
    
    if 'number' not in request.form:
        return jsonify({"error": "No number part in the request"}), 400

    if 'xml_file' not in request.files:
        return jsonify({"error": "No XML file part in the request"}), 400

    image_file = request.files['image_file']
    number = request.form['number']
    xml_file = request.files['xml_file']
    print(xml_file)

    if image_file.filename == '' or xml_file.filename == '':
        return jsonify({"error": "No selected file for either image or XML"}), 400

    if not (image_file and image_file.filename.endswith(('.jpg', '.jpeg', '.png'))):
        return jsonify({"error": "Image file type not allowed, please upload an image file"}), 400

    try:
        number = int(number)
    except ValueError:
        return jsonify({"error": "Number is not valid"}), 400

    # Save image file
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
    image_file.save(image_path)

    # Handle XML file
    try:
        print('starting df')
        df = create_file(xml_file, number, image_path)
        print(df.columns)
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results.csv')

        df.to_csv('result.csv', index=False)
        return send_file('result.csv', as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='127.0.0.1', port=8080, debug=True)
