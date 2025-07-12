import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='html_templates')
CORS(app) # Enable CORS for all routes

DATABASE = 'skill_swap.db'
UPLOAD_FOLDER = 'uploads' # Folder to store uploaded profile pictures
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            location TEXT,
            skills_offered TEXT,
            skills_wanted TEXT,
            availability TEXT,
            is_public INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            profile_photo TEXT, -- New column for profile photo URL/path
            theme TEXT DEFAULT 'indigo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # Create swap_requests table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS swap_requests (
            id TEXT PRIMARY KEY,
            sender_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            receiver_name TEXT NOT NULL,
            skill_offered TEXT NOT NULL,
            skill_wanted TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, accepted, rejected
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        );
    ''')
    # Create feedback table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            swap_request_id TEXT NOT NULL,
            giver_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (swap_request_id) REFERENCES swap_requests (id),
            FOREIGN KEY (giver_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        );
    ''')
    # Create platform_messages table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS platform_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Add default admin user if not exists
    cursor = conn.execute("SELECT * FROM users WHERE name = 'admin'")
    admin_exists = cursor.fetchone()
    if not admin_exists:
        admin_id = str(uuid.uuid4())
        admin_password_hash = generate_password_hash("adminpass")
        conn.execute(
            "INSERT INTO users (id, name, password_hash, is_admin, is_public) VALUES (?, ?, ?, ?, ?)",
            (admin_id, 'admin', admin_password_hash, 1, 0) # Admin profile is not public by default
        )
        conn.commit()
        print("Default admin user created with ID:", admin_id)
    conn.close()

# Initialize database on app startup
with app.app_context():
    init_db()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve static files from the 'html_templates' directory
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Serve uploaded profile pictures
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# User authentication and profile management
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')
    location = data.get('location', '')
    skills_offered = ','.join(data.get('skillsOffered', []))
    skills_wanted = ','.join(data.get('skillsWanted', []))
    availability = data.get('availability', '')
    is_public = data.get('isPublic', True) # Default to public

    if not name or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already exists"}), 409

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)

    try:
        cursor.execute(
            "INSERT INTO users (id, name, password_hash, location, skills_offered, skills_wanted, availability, is_public) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, password_hash, location, skills_offered, skills_wanted, availability, 1 if is_public else 0)
        )
        conn.commit()
        # Fetch the newly created profile to return
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_profile_data = cursor.fetchone()
        user_profile = dict(user_profile_data) if user_profile_data else None
        if user_profile:
            user_profile['skills_offered'] = user_profile['skills_offered'].split(',') if user_profile['skills_offered'] else []
            user_profile['skills_wanted'] = user_profile['skills_wanted'].split(',') if user_profile['skills_wanted'] else []

        print(f"User signed up: {name}, ID: {user_id}") # Debug print
        return jsonify({"message": "User registered successfully", "userId": user_id, "userProfile": user_profile}), 201
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error during signup: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        user_profile = dict(user)
        user_profile['skills_offered'] = user_profile['skills_offered'].split(',') if user_profile['skills_offered'] else []
        user_profile['skills_wanted'] = user_profile['skills_wanted'].split(',') if user_profile['skills_wanted'] else []
        print(f"User logged in: {name}, ID: {user['id']}") # Debug print
        return jsonify({"message": "Login successful", "userId": user['id'], "userProfile": user_profile}), 200
    else:
        print(f"Failed login attempt for user: {name}") # Debug print
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_profile = dict(user)
        user_profile['skills_offered'] = user_profile['skills_offered'].split(',') if user_profile['skills_offered'] else []
        user_profile['skills_wanted'] = user_profile['skills_wanted'].split(',') if user_profile['skills_wanted'] else []
        print(f"Fetched profile for user ID: {user_id}") # Debug print
        return jsonify(user_profile), 200
    else:
        print(f"Profile not found for user ID: {user_id}") # Debug print
        return jsonify({"error": "User not found"}), 404

@app.route('/api/profile/<user_id>', methods=['PUT'])
def update_user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        print(f"Attempted to update non-existent user ID: {user_id}") # Debug print
        return jsonify({"error": "User not found"}), 404

    profile_photo_path = user['profile_photo'] # Default to existing photo

    if 'profilePhoto' in request.files and request.files['profilePhoto'].filename != '':
        file = request.files['profilePhoto']
        if file and allowed_file(file.filename):
            filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            profile_photo_path = f"/uploads/{filename}" # Store relative URL
            print(f"File uploaded for user {user_id}: {filename}") # Debug print
        else:
            print(f"Invalid file type for profile photo upload for user {user_id}") # Debug print
            return jsonify({"error": "Invalid file type for profile photo"}), 400
    else:
        # If no new file uploaded, check if profilePhotoUrl was provided in form (if FormData) or JSON
        if request.is_json:
            data = request.get_json()
            profile_photo_path = data.get('profilePhotoUrl', user['profile_photo'])
            print(f"Using JSON profilePhotoUrl for user {user_id}: {profile_photo_path}") # Debug print
        else: # It's a FormData request without a file
            profile_photo_path = request.form.get('profilePhotoUrl', user['profile_photo'])
            print(f"Using FormData profilePhotoUrl for user {user_id}: {profile_photo_path}") # Debug print


    # Get other fields from request.form if it's a file upload, otherwise from request.get_json()
    if request.is_json:
        data = request.get_json()
        name = data.get('name', user['name'])
        location = data.get('location', user['location'])
        skills_offered = ','.join(data.get('skillsOffered', user['skills_offered'].split(',') if user['skills_offered'] else []))
        skills_wanted = ','.join(data.get('skillsWanted', user['skills_wanted'].split(',') if user['skills_wanted'] else []))
        availability = data.get('availability', user['availability'])
        is_public = data.get('isPublic', user['is_public']) # Already boolean from frontend
        theme = data.get('theme', user['theme'])
    else: # It's a FormData request
        name = request.form.get('name', user['name'])
        location = request.form.get('location', user['location'])
        # For skills, request.form.getlist is safer for comma-separated if sent as multiple fields,
        # but if it's a single string, .get() is fine. Assuming single string for simplicity.
        skills_offered_str = request.form.get('skillsOffered', user['skills_offered'])
        skills_offered = ','.join([s.strip() for s in skills_offered_str.split(',') if s.strip()])

        skills_wanted_str = request.form.get('skillsWanted', user['skills_wanted'])
        skills_wanted = ','.join([s.strip() for s in skills_wanted_str.split(',') if s.strip()])

        availability = request.form.get('availability', user['availability'])
        is_public = int(request.form.get('isPublic', user['is_public']))
        theme = request.form.get('theme', user['theme'])


    try:
        cursor.execute(
            "UPDATE users SET name = ?, location = ?, skills_offered = ?, skills_wanted = ?, availability = ?, is_public = ?, profile_photo = ?, theme = ? WHERE id = ?",
            (name, location, skills_offered, skills_wanted, availability, 1 if is_public else 0, profile_photo_path, theme, user_id)
        )
        conn.commit()
        # Fetch updated profile to return
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user_data = cursor.fetchone()
        updated_user_profile = dict(updated_user_data) if updated_user_data else None
        if updated_user_profile:
            updated_user_profile['skills_offered'] = updated_user_profile['skills_offered'].split(',') if updated_user_profile['skills_offered'] else []
            updated_user_profile['skills_wanted'] = updated_user_profile['skills_wanted'].split(',') if updated_user_profile['skills_wanted'] else []

        print(f"Profile updated successfully for user ID: {user_id}") # Debug print
        return jsonify(updated_user_profile), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error during profile update for user {user_id}: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = request.args.get('searchTerm', '')

    query = "SELECT id, name, location, skills_offered, skills_wanted, availability, is_public, profile_photo, theme FROM users WHERE is_public = 1 AND is_banned = 0"
    params = []

    if search_term:
        search_like = f"%{search_term}%"
        query += " AND (name LIKE ? OR skills_offered LIKE ? OR skills_wanted LIKE ?)"
        params.extend([search_like, search_like, search_like])

    cursor.execute(query, params)
    users = cursor.fetchall()
    conn.close()

    users_list = []
    for user in users:
        user_dict = dict(user)
        user_dict['skills_offered'] = user_dict['skills_offered'].split(',') if user_dict['skills_offered'] else []
        user_dict['skills_wanted'] = user_dict['skills_wanted'].split(',') if user_dict['skills_wanted'] else []
        users_list.append(user_dict)
    print(f"Fetched {len(users_list)} public users.") # Debug print
    return jsonify(users_list), 200

# Swap Request Endpoints
@app.route('/api/swap_requests', methods=['POST'])
def create_swap_request():
    data = request.get_json()
    sender_id = data.get('senderId')
    sender_name = data.get('senderName')
    receiver_id = data.get('receiverId')
    receiver_name = data.get('receiverName')
    skill_offered = data.get('skillOffered')
    skill_wanted = data.get('skillWanted')

    if not all([sender_id, sender_name, receiver_id, receiver_name, skill_offered, skill_wanted]):
        print("Error: Missing required fields for swap request.") # Debug print
        return jsonify({"error": "Missing required fields"}), 400

    request_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO swap_requests (id, sender_id, sender_name, receiver_id, receiver_name, skill_offered, skill_wanted) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (request_id, sender_id, sender_name, receiver_id, receiver_name, skill_offered, skill_wanted)
        )
        conn.commit()
        print(f"Swap request created: ID={request_id}, Sender={sender_name}, Receiver={receiver_name}") # Debug print
        return jsonify({"message": "Swap request sent successfully", "requestId": request_id}), 201
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error creating swap request: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/swap_requests/<user_id>', methods=['GET'])
def get_user_swap_requests(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get requests where user is sender OR receiver
    cursor.execute(
        "SELECT * FROM swap_requests WHERE sender_id = ? OR receiver_id = ? ORDER BY created_at DESC",
        (user_id, user_id)
    )
    requests = cursor.fetchall()
    conn.close()
    print(f"Fetched {len(requests)} swap requests for user ID: {user_id}") # Debug print
    return jsonify([dict(req) for req in requests]), 200

@app.route('/api/swap_requests/<request_id>', methods=['PUT'])
def update_swap_request_status(request_id):
    data = request.get_json()
    new_status = data.get('status') # 'accepted' or 'rejected'

    if new_status not in ['accepted', 'rejected']:
        print(f"Invalid status update attempt for request {request_id}: {new_status}") # Debug print
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE swap_requests SET status = ? WHERE id = ?", (new_status, request_id))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Swap request {request_id} not found for status update.") # Debug print
            return jsonify({"error": "Swap request not found"}), 404
        status_message = "accepted" if new_status == 'accepted' else "rejected"
        print(f"Swap request {request_id} status updated to: {status_message}") # Debug print
        return jsonify({"message": f"Swap request {new_status} successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error updating swap request {request_id} status: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/swap_requests/<request_id>', methods=['DELETE'])
def delete_swap_request(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM swap_requests WHERE id = ?", (request_id,))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Swap request {request_id} not found for deletion.") # Debug print
            return jsonify({"error": "Swap request not found"}), 404
        print(f"Swap request {request_id} deleted successfully.") # Debug print
        return jsonify({"message": "Swap request deleted successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error deleting swap request {request_id}: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

# Feedback Endpoints
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    swap_request_id = data.get('swapRequestId')
    giver_id = data.get('giverId')
    receiver_id = data.get('receiverId')
    rating = data.get('rating')
    comment = data.get('comment')

    if not all([swap_request_id, giver_id, receiver_id, rating is not None]):
        print("Error: Missing required feedback fields.") # Debug print
        return jsonify({"error": "Missing required feedback fields"}), 400

    feedback_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO feedback (id, swap_request_id, giver_id, receiver_id, rating, comment) VALUES (?, ?, ?, ?, ?, ?)",
            (feedback_id, swap_request_id, giver_id, receiver_id, rating, comment)
        )
        conn.commit()
        print(f"Feedback submitted for swap {swap_request_id} by {giver_id}.") # Debug print
        return jsonify({"message": "Feedback submitted successfully", "feedbackId": feedback_id}), 201
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error submitting feedback: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/feedback', methods=['GET'])
def get_all_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
    feedback_logs = cursor.fetchall()
    conn.close()
    print(f"Fetched {len(feedback_logs)} feedback logs.") # Debug print
    return jsonify([dict(log) for log in feedback_logs]), 200

# Admin Endpoints
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    # In a real app, you'd add authentication/authorization for admin access here
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, location, skills_offered, skills_wanted, is_public, is_admin, is_banned, profile_photo, theme, created_at FROM users")
    users = cursor.fetchall()
    conn.close()
    users_list = []
    for user in users:
        user_dict = dict(user)
        user_dict['skills_offered'] = user_dict['skills_offered'].split(',') if user_dict['skills_offered'] else []
        user_dict['skills_wanted'] = user_dict['skills_wanted'].split(',') if user_dict['skills_wanted'] else []
        users_list.append(user_dict)
    print(f"Admin fetched {len(users_list)} users.") # Debug print
    return jsonify(users_list), 200

@app.route('/api/admin/users/<user_id>/ban', methods=['PUT'])
def admin_ban_user(user_id):
    # In a real app, you'd add authentication/authorization for admin access here
    data = request.get_json()
    is_banned = data.get('isBanned') # 0 for unban, 1 for ban

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_banned = ? WHERE id = ?", (is_banned, user_id))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Admin: User {user_id} not found for ban/unban.") # Debug print
            return jsonify({"error": "User not found"}), 404
        status_message = "banned" if is_banned else "unbanned"
        print(f"Admin: User {user_id} {status_message} successfully.") # Debug print
        return jsonify({"message": f"User {user_id} {status_message} successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Admin: Database error during ban/unban for user {user_id}: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/admin/platform_message', methods=['GET'])
def get_platform_message():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT message FROM platform_messages ORDER BY created_at DESC LIMIT 1")
    message = cursor.fetchone()
    conn.close()
    if message:
        print(f"Admin: Fetched platform message: {message['message']}") # Debug print
        return jsonify({"message": message['message']}), 200
    print("Admin: No platform message found.") # Debug print
    return jsonify({"message": ""}), 200 # No message set yet

@app.route('/api/admin/platform_message', methods=['POST'])
def set_platform_message():
    # In a real app, you'd add authentication/authorization for admin access here
    data = request.get_json()
    message = data.get('message')

    if message is None:
        print("Admin: Error - message content is required for platform message.") # Debug print
        return jsonify({"error": "Message content is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear previous messages or just add new one, for simplicity, we'll just add
        cursor.execute("INSERT INTO platform_messages (message) VALUES (?)", (message,))
        conn.commit()
        print(f"Admin: Platform message set to: {message}") # Debug print
        return jsonify({"message": "Platform message updated successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Admin: Database error setting platform message: {str(e)}") # Debug print
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/admin/swap_requests', methods=['GET'])
def admin_get_all_swap_requests():
    # In a real app, you'd add authentication/authorization for admin access here
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM swap_requests ORDER BY created_at DESC")
    requests = cursor.fetchall()
    conn.close()
    print(f"Admin: Fetched {len(requests)} total swap requests.") # Debug print
    return jsonify([dict(req) for req in requests]), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
