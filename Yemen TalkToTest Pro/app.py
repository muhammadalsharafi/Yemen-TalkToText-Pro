import os
import shutil
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import bcrypt
from bson.objectid import ObjectId
import threading
import uuid

# Import core components from your project
from core.database_manager import DatabaseManager
from core.message_system import MessageSystem, MessageCode
from main import MainPipeline
import config

# --- App Initialization and Configuration ---

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management

# --- Environment Variable Validation ---

MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not MONGO_CONNECTION_STRING or not OPENAI_API_KEY:
    MessageSystem.log_error(
        MessageCode.OPERATION_FAILED,
        error="FATAL: Missing 'MONGO_CONNECTION_STRING' or 'OPENAI_API_KEY' in .env file."
    )
    exit(1)

# --- Service Initialization ---

try:
    db_manager = DatabaseManager(connection_string=MONGO_CONNECTION_STRING)
    project_root = os.getcwd()
    ffmpeg_exe_path = os.path.join(project_root, "bin", "ffmpeg.exe")
    ffprobe_exe_path = os.path.join(project_root, "bin", "ffprobe.exe")

    # Initialize the main processing pipeline with a default quality
    pipeline = MainPipeline(
        api_key=OPENAI_API_KEY,
        audio_quality=config.SELECTED_AUDIO_QUALITY, # Default quality
        ffmpeg_path=ffmpeg_exe_path,
        ffprobe_path=ffprobe_exe_path,
        db_manager=db_manager
    )
except Exception as e:
    MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Failed to initialize core services: {e}")
    exit(1)

# --- Global dictionary to store job results ---
job_results = {}

# --- User Authentication Routes ---

@app.route("/")
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            data = request.get_json()
            fullname = data.get("fullname", "")
            first_name, last_name = (fullname.split(" ", 1) + [""])[:2]
            email = data.get("email")
            password = data.get("password")

            if not all([first_name, email, password]):
                return jsonify({"success": False, "error": "Please fill all required fields."}), 400

            if db_manager.get_user_by_email(email):
                return jsonify({"success": False, "error": "Email address already registered."}), 409

            db_manager.create_user(first_name, last_name, email, password)
            return jsonify({"success": True, "message": "Signup successful! Please login."})

        except Exception as e:
            MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Signup failed: {e}")
            return jsonify({"success": False, "error": "An internal error occurred."}), 500
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json()
            email, password = data.get("email"), data.get("password")
            if not email or not password:
                return jsonify({"success": False, "error": "Please provide both email and password."}), 400
            user = db_manager.get_user_by_email(email)
            if user and bcrypt.checkpw(password.encode('utf-8'), user['passwordHash']):
                session['user_id'] = str(user['_id'])
                session['user_name'] = user['firstName']
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "error": "Invalid email or password."}), 401
        except Exception as e:
            MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Login failed: {e}")
            return jsonify({"success": False, "error": "An internal server error occurred."}), 500
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Main Application Routes ---

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", user_name=session.get('user_name'))

def run_pipeline_in_background(job_id, input_path, user_id, audio_quality, target_language, is_url=False, original_filepath=None):
    """
    Function to run the pipeline and store its result.
    Crucially, it ensures immediate cleanup of all associated files in a finally block.
    """
    temp_dir_path = f"temp_{job_id}"
    try:
        final_results = pipeline.run(
            input_path_or_url=input_path, 
            user_id=user_id,
            audio_quality=audio_quality,
            target_language_name=target_language,
            job_id_for_temp_dir=job_id # Pass job_id to create the correct temp dir
        )
        job_results[job_id] = {"status": "completed", "data": final_results}
    except Exception as e:
        job_results[job_id] = {"status": "failed", "error": str(e)}
    finally:
        # --- IMMEDIATE AND ROBUST CLEANUP ---
        # 1. Clean up the temporary directory for this job
        if os.path.exists(temp_dir_path):
            try:
                shutil.rmtree(temp_dir_path)
                MessageSystem.log_success(MessageCode.PIPELINE_CLEANUP, temp_dir=temp_dir_path)
            except OSError as e:
                MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Error cleaning up temp directory {temp_dir_path}: {e}")
        
        # 2. Clean up the original uploaded file (if it was a file upload)
        if original_filepath and os.path.exists(original_filepath):
            try:
                os.remove(original_filepath)
                MessageSystem.log_info(MessageCode.OPERATION_FAILED, error=f"Cleaned up uploaded file: {original_filepath}") # Re-using a generic code for logging
            except OSError as e:
                MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Error cleaning up uploaded file {original_filepath}: {e}")


@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not authenticated."}), 401

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part in the request."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected."}), 400

    try:
        audio_quality = request.form.get('accuracy', 'medium').lower()
        target_language = request.form.get('language', 'auto').capitalize()
        user_id = ObjectId(session['user_id'])

        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        unique_filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        job_id = str(uuid.uuid4())
        job_results[job_id] = {"status": "processing"}

        thread = threading.Thread(target=run_pipeline_in_background, args=(
            job_id, filepath, user_id, audio_quality, target_language, False, filepath # Pass filepath for cleanup
        ))
        thread.start()

        return jsonify({"success": True, "message": "Processing started.", "job_id": job_id})

    except Exception as e:
        MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"File upload failed: {e}")
        return jsonify({"success": False, "error": "An internal server error occurred during file upload."}), 500

@app.route("/upload_url", methods=["POST"])
def upload_url():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not authenticated."}), 401
    
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"success": False, "error": "URL is missing."}), 400

        audio_quality = data.get('accuracy', 'medium').lower()
        target_language = data.get('language', 'auto').capitalize()
        user_id = ObjectId(session['user_id'])
        
        job_id = str(uuid.uuid4())
        job_results[job_id] = {"status": "processing"}

        thread = threading.Thread(target=run_pipeline_in_background, args=(
            job_id, url, user_id, audio_quality, target_language, True, None # No original file to cleanup
        ))
        thread.start()

        return jsonify({"success": True, "message": "Processing started.", "job_id": job_id})

    except Exception as e:
        MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"URL submission failed: {e}")
        return jsonify({"success": False, "error": "An internal server error occurred during URL processing."}), 500

@app.route("/job_status/<job_id>", methods=["GET"])
def get_job_status(job_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not authenticated."}), 401
    
    result = job_results.get(job_id)
    if not result:
        return jsonify({"success": False, "error": "Job not found."}), 404
        
    return jsonify({"success": True, "status": result.get("status"), "data": result.get("data"), "error": result.get("error")})

@app.route("/history", methods=["GET"])
def get_history():
    if 'user_id' not in session:
        return jsonify([]), 401
    
    try:
        user_id = ObjectId(session['user_id'])
        jobs = db_manager.get_user_jobs(user_id)
        
        history_list = []
        for job in jobs:
            preview = "Processing..."
            if job.get("status") == "completed":
                processing_data = job.get("processing", {})
                transcription_data = processing_data.get("transcription", {})
                preview_text = transcription_data.get("cleanedTranscript", "No preview available.")
                preview = (preview_text[:75] + '...') if len(preview_text) > 75 else preview_text

            history_list.append({
                "id": str(job["_id"]),
                "name": job["source"]["value"].split('/')[-1],
                "date": job["createdAt"].isoformat(),
                "preview": preview,
                "status": job["status"],
                "formats": job.get("processing", {})
            })
            
        return jsonify(history_list)

    except Exception as e:
        MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Failed to fetch history: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

# --- START: NEW DELETE ROUTES ---
@app.route("/history/delete/<job_id>", methods=["DELETE"])
def delete_history_item(job_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not authenticated."}), 401
    
    try:
        user_id = ObjectId(session['user_id'])
        success = db_manager.soft_delete_job(ObjectId(job_id), user_id)
        if success:
            return jsonify({"success": True, "message": "Item hidden successfully."})
        else:
            return jsonify({"success": False, "error": "Item not found or user not authorized."}), 404
    except Exception as e:
        MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Failed to delete history item: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500

@app.route("/history/clear_all", methods=["POST"])
def clear_all_history():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "User not authenticated."}), 401
    
    try:
        user_id = ObjectId(session['user_id'])
        deleted_count = db_manager.soft_delete_all_user_jobs(user_id)
        return jsonify({"success": True, "message": f"{deleted_count} items hidden."})
    except Exception as e:
        MessageSystem.log_error(MessageCode.UNEXPECTED_ERROR, error=f"Failed to clear history: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500
# --- END: NEW DELETE ROUTES ---


# --- Application Runner ---

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)