# Hearing Assistance and Transcription Webapp

## Overview
This project is a web application designed to assist users with hearing impairments and provide transcription services. It leverages sign language recognition, video/image processing, and real-time transcription to enhance accessibility and communication.

## Features
- Sign language recognition using deep learning models
- Real-time video/image processing
- Audio transcription and subtitle generation
- User authentication and dashboard
- Upload and manage media files
- Accessible and user-friendly interface

## Project Structure
- `application.py`: Main entry point for the web application
- `THAT/`: Core application code (features, models, routes, forms, etc.)
- `images/`: Contains marked and skeleton images for sign language recognition
- `uploads/`: Stores uploaded media files
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JS, images, fonts, etc.)
- `requirements.txt`: Python dependencies

## Setup Instructions

1. **Install Python 3**
   - Download and install Python 3 from [python.org](https://www.python.org/downloads/).

2. **Add Python to Environment Variables**
   - Ensure Python is added to your system's PATH.

3. **Create a Virtual Environment**
   - Open a terminal and run:
     ```
     virtualenv THAT_env
     ```

4. **Activate the Virtual Environment**
   - For Windows:
     ```
     .\THAT_env\Scripts\activate
     ```
   - For Ubuntu/Linux:
     ```
     source THAT_env/bin/activate
     ```

5. **Install Dependencies**
   - Run:
     ```
     pip install -r requirements.txt
     ```

6. **Run the Application**
   - Start the web server:
     ```
     python application.py
     ```

7. **Access the Webapp**
   - Open the localhost link generated in your browser after running the previous command.

## Demo Video

https://drive.google.com/file/d/1OFtn2Bizd_lJIN35wB-0SGQne4BpAa8N/view?usp=sharing
