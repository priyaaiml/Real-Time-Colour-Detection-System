# 🎨 Real-Time Colour Detection and Analysis System

A Python-based web application that detects and analyses colours in real time using a webcam. Built using Flask, OpenCV, NumPy, HTML, CSS and JavaScript.

## 📌 About the Project

The Real-Time Colour Detection and Analysis System identifies different colours from a live webcam feed and analyses the colour distribution in the captured image.

The system uses computer vision techniques to identify colour regions, display their colour values and provide information about how much of the image each detected colour occupies.

It provides a simple, interactive web interface where users can view live detection results and capture images for colour analysis.

## 🎯 Problem Statement

Identifying and analysing colours in images manually can be time-consuming, especially when an image contains multiple colours.

This project provides an automated solution that detects colours, identifies their values and analyses their distribution in an image.

## ✨ Key Features

- **Real-Time Colour Detection:** Detects colours from a live webcam feed.
- **Multiple Colour Recognition:** Supports red, green, blue, yellow, orange, purple, black and white.
- **Bounding Boxes:** Highlights detected colour regions in the camera feed.
- **Colour Information:** Displays colour names and HEX, RGB and HSV values.
- **Dominant Colour Analysis:** Identifies the most prominent detected colour.
- **Colour Distribution Statistics:** Displays the percentage of image pixels classified under different colours.
- **Image Capture:** Captures the current webcam frame with detection results.
- **Interactive Colour Selection:** Allows users to select a colour and view its detection information.
- **Download Option:** Allows users to download the captured detection image.

## ⚙️ How It Works

1. The webcam captures a live video stream.
2. OpenCV processes the video frames.
3. The image is converted from RGB/BGR colour representation into HSV colour space.
4. Colour thresholds are applied to identify different colour regions.
5. Morphological operations help reduce noise in the detected regions.
6. Contour detection identifies the boundaries of colour regions.
7. Bounding boxes and colour information are displayed.
8. The system analyses the colour distribution and displays statistics.
9. Users can capture and download the processed image.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Flask | Web application backend |
| OpenCV | Image and video processing |
| NumPy | Numerical and array operations |
| HTML | Web page structure |
| CSS | User interface design |
| JavaScript | Frontend interaction |

## 📂 Project Structure

```text
Real-Time-Colour-Detection-System/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
└── screenshots/
    ├── dashboard.png
    ├── detection.png
    └── analysis.png
```

## 🚀 Installation and Execution

### 1. Clone the repository

```bash
git clone https://github.com/priyaaiml/Real-Time-Colour-Detection-System.git
```

### 2. Navigate into the project directory

```bash
cd Real-Time-Colour-Detection-System
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open the application

Visit:

http://127.0.0.1:5000

Allow webcam access and click the Start Camera option.

## 📸 Screenshots

### Application Dashboard

![Application Dashboard](screenshots/dashboard.png)

### Real-Time Colour Detection

![Real-Time Colour Detection](screenshots/detection.png)

### Colour Analysis and Statistics

![Colour Analysis](screenshots/analysis.png)

## 💡 Applications

- Basic image and video analysis
- Colour-based object identification
- Educational computer vision demonstrations
- Visual inspection and colour analysis
- Understanding colour distribution in images

## 🔮 Future Enhancements

- Support for more colour categories.
- Improved detection under different lighting conditions.
- Image upload for offline colour analysis.
- Colour comparison between multiple images.
- Export colour analysis reports.

## 👩‍💻 Developed By

**Priyamani M**

BE – Artificial Intelligence and Machine Learning

GitHub: [priyaaiml](https://github.com/priyaaiml)

---

*Real-Time Colour Detection and Analysis System using Python and OpenCV.*
