import os
import sqlite3
from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
import time  # Import time module for checking file upload status
from google import genai # Modified import

app = Flask(__name__)

DATA_DIR = "C:/Users/Vignesh Anburose/.screenpipe"  # IMPORTANT: Double check this path is correct
GENAI_API_KEY = "AIzaSyCcBtT49pUm9Qp5PbBNW8emQD2zKFfwt_4"

if not GENAI_API_KEY or GENAI_API_KEY == "YOUR_API_KEY_HERE":
    raise EnvironmentError("GOOGLE_API_KEY environment variable not set or placeholder used. Please set your Gemini API key in app.py.")

client = genai.Client(api_key=GENAI_API_KEY) # Initialize Client

global_ocr_context = ""

def get_latest_video_chunk_path():
    """
    Finds the path to the most recently created video chunk file.
    """
    video_dir = os.path.join(DATA_DIR, 'data')
    if not os.path.exists(video_dir):
        print(f"Error: Video data directory not found: {video_dir}")
        return None

    video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4') and 'monitor_' in f]
    if not video_files:
        print("Warning: No video chunk files found.")
        return None

    video_files.sort(key=lambda f: os.path.getmtime(os.path.join(video_dir, f)), reverse=True)
    latest_video_file = video_files[0]
    latest_video_path = os.path.join(video_dir, latest_video_file)
    print(f"Using latest video chunk: {latest_video_path}")
    return latest_video_path

def upload_latest_video_chunk():
    """
    Uploads the latest video chunk using the File API and returns the file reference.
    Replaced with documentation code and added error checks and extensive logging.
    """
    video_path = get_latest_video_chunk_path()
    if not video_path:
        print("upload_latest_video_chunk: No video path found, cannot proceed with upload.")
        return None

    print(f"Video path to upload: {video_path}") # Added logging

    if not os.path.exists(video_path):
        print(f"Error: Video file not found at path: {video_path}")
        return None
    if not os.access(video_path, os.R_OK):
        print(f"Error: Video file not readable at path: {video_path}")
        return None

    print("Uploading video file...")
    try:
        video_file = client.files.upload(
            file=video_path
        )
        print(f"Completed initial upload: {video_file.uri}, State: {video_file.state.name}") # Log initial state

        # Verify file upload and check state
        while video_file.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(1)
            try:
                video_file = client.files.get(name=video_file.name)
                print(f"State during processing: {video_file.state.name}") # Log state during processing
            except Exception as e_get_file:
                print(f"Error getting file status during processing: {e_get_file}")
                print(f"Exception details during get file status: {e_get_file}")
                if hasattr(e_get_file, 'response'):
                    print(f"API Response during get file status: {e_get_file.response}")
                return None # Exit if we can't get file status

        if video_file.state.name == "FAILED":
            print(f"File upload failed. Final State: {video_file.state.name}") # Log final state
            return None

        if video_file.state.name == "ACTIVE":
            print('Video file ACTIVE and ready for inference.')
            return video_file
        else:
            print(f"Unexpected video file state after upload: {video_file.state.name}") # Log unexpected state
            return None


    except Exception as e:
        print(f"Error uploading video file using File API: {e}")
        print(f"Exception details: {e}")
        if hasattr(e, 'response'):
            print(f"API Response: {e.response}")
        return None


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask_gemini', methods=['POST'])
def ask_gemini():
    user_question = request.form['user_question']
    video_file = upload_latest_video_chunk() # Get file reference by uploading

    if not video_file:
        return jsonify({'response': "No video recording available or error uploading video. Please make sure Screenpipe is running and recording video, and check server logs."}) # More informative message

    try:
        prompt_content = [
            "You are a chatbot that can analyze video content from the user's screen recording.",
            "Answer user questions based on what is visually present in the video.",
            "Focus on describing visual elements, actions, and objects visible in the video to answer the question.",
            "If the question is not answerable from the video content, respond with: 'I am sorry, but I cannot answer this question based on the current video content.'",
            video_file, # Pass the video file reference directly
            f"User Question: {user_question}"
        ]

        response = client.models.generate_content( # Use client.models.generate_content
            model="gemini-2.0-flash", # Keeping the model as requested, but you can change to "gemini-1.5-pro" if needed.
            contents=prompt_content) # Use 'contents'
        gemini_response = response.text
    except Exception as e:
        print(f"Gemini Vision API error during content generation: {e}")
        print(f"Exception details during content generation: {e}") # More details for content gen
        if hasattr(e, 'response'):
            print(f"API Response during content generation: {e.response}")
        gemini_response = "Error generating response from Gemini Vision. Please check the server logs."

    return jsonify({'response': gemini_response})


if __name__ == '__main__':
    app.run(debug=True, port=5000)