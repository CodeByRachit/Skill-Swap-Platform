import sqlite3
import uuid
import time
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash # For password hashing

app = Flask(__name__, static_folder='html_templates') # Serve from html_templates
CORS(app) # Enable CORS for all routes

DATABASE = 'skill_swap.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Check if users table exists and if password_hash column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'users' not in columns: # If table doesn't exist, create it with password_hash
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE, -- Name must be unique for login
                    password_hash TEXT NOT NULL, -- Store hashed passwords
                    location TEXT,
                    profile_photo TEXT,
                    skills_offered TEXT,
                    skills_wanted TEXT,
                    availability TEXT,
                    is_public INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    theme TEXT DEFAULT 'indigo',
                    created_at INTEGER
                )
            ''')
        elif 'password_hash' not in columns: # If table exists but no password_hash, add it
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            # For existing users, you might want to set a default or prompt for password update
            # For simplicity, existing users without password_hash might need manual update or re-signup
            print("Added 'password_hash' column to users table.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS swap_requests (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                receiver_name TEXT NOT NULL,
                skill_offered TEXT NOT NULL,
                skill_wanted TEXT NOT NULL,
                status TEXT DEFAULT 'pending', -- pending, accepted, rejected
                created_at INTEGER,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                swap_request_id TEXT NOT NULL,
                giver_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                rating INTEGER NOT NULL, -- 1 to 5
                comment TEXT,
                created_at INTEGER,
                FOREIGN KEY (swap_request_id) REFERENCES swap_requests (id),
                FOREIGN KEY (giver_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        db.commit()

        # Add a default admin user if one doesn't exist and a password is not set
        cursor.execute("SELECT id, password_hash FROM users WHERE is_admin = 1 LIMIT 1")
        admin_user = cursor.fetchone()
        if not admin_user or not admin_user['password_hash']:
            admin_id = str(uuid.uuid4())
            # Default password for admin - CHANGE THIS IN PRODUCTION!
            default_admin_password_hash = generate_password_hash("adminpassword") 
            if not admin_user:
                 cursor.execute(
                    "INSERT INTO users (id, name, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                    (admin_id, "Admin User", default_admin_password_hash, 1, int(time.time()))
                )
                 print(f"Default admin user created with ID: {admin_id} and default password 'adminpassword'")
            else:
                # If admin exists but no password_hash, update it
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (default_admin_password_hash, admin_user['id'])
                )
                print(f"Admin user {admin_user['id']} updated with default password 'adminpassword'")
            db.commit()


# --- API Endpoints ---

@app.route('/')
def index():
    # Serve the React app's HTML from the static_folder
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/auth/signup', methods=['POST'])
def sign_up():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')
    location = data.get('location', '')
    skills_offered = ','.join(data.get('skillsOffered', []))
    skills_wanted = ','.join(data.get('skillsWanted', []))
    availability = data.get('availability', '')
    is_public = int(data.get('isPublic', True))

    if not name or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
    if cursor.fetchone():
        return jsonify({"error": "Username already exists"}), 409

    hashed_password = generate_password_hash(password)
    new_user_id = str(uuid.uuid4())
    timestamp = int(time.time())

    try:
        cursor.execute(
            '''INSERT INTO users (id, name, password_hash, location, profile_photo,
               skills_offered, skills_wanted, availability, is_public, is_admin, is_banned, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (new_user_id, name, hashed_password, location, '', # profile_photo default empty
             skills_offered, skills_wanted, availability, is_public, 0, 0, timestamp)
        )
        db.commit()
        
        # Fetch the newly created user's profile for response
        cursor.execute("SELECT * FROM users WHERE id = ?", (new_user_id,))
        new_user = cursor.fetchone()
        new_user_profile = dict(new_user)
        new_user_profile['skills_offered'] = new_user_profile['skills_offered'].split(',') if new_user_profile['skills_offered'] else []
        new_user_profile['skills_wanted'] = new_user_profile['skills_wanted'].split(',') if new_user_profile['skills_wanted'] else []
        new_user_profile.pop('password_hash', None) # Don't send hash to frontend

        return jsonify({"userId": new_user_id, "message": "User registered successfully", "userProfile": new_user_profile}), 201
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"error": f"Database error during signup: {str(e)}"}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    if not name or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password_hash'], password):
        user_profile = dict(user)
        user_profile['skills_offered'] = user_profile['skills_offered'].split(',') if user_profile['skills_offered'] else []
        user_profile['skills_wanted'] = user_profile['skills_wanted'].split(',') if user_profile['skills_wanted'] else []
        user_profile.pop('password_hash', None) # Don't send hash to frontend
        return jsonify({"userId": user['id'], "message": "Logged in successfully", "userProfile": user_profile}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/profile/<user_id>', methods=['GET', 'PUT'])
def user_profile(user_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            user_dict = dict(user)
            user_dict['skills_offered'] = user_dict['skills_offered'].split(',') if user_dict['skills_offered'] else []
            user_dict['skills_wanted'] = user_dict['skills_wanted'].split(',') if user_dict['skills_wanted'] else []
            user_dict.pop('password_hash', None) # Don't send hash to frontend
            return jsonify(user_dict), 200
        return jsonify({"error": "User not found"}), 404

    elif request.method == 'PUT':
        data = request.get_json()
        name = data.get('name')
        location = data.get('location')
        profile_photo = data.get('profilePhoto')
        skills_offered = ','.join(data.get('skillsOffered', []))
        skills_wanted = ','.join(data.get('skillsWanted', []))
        availability = data.get('availability')
        is_public = int(data.get('isPublic', True)) # Convert boolean to integer
        theme = data.get('theme', 'indigo')

        # Check if the new name conflicts with an existing user (excluding self)
        cursor.execute("SELECT id FROM users WHERE name = ? AND id != ?", (name, user_id))
        if cursor.fetchone():
            return jsonify({"error": "Username already taken"}), 409

        cursor.execute(
            '''UPDATE users SET name = ?, location = ?, profile_photo = ?,
               skills_offered = ?, skills_wanted = ?, availability = ?,
               is_public = ?, theme = ? WHERE id = ?''',
            (name, location, profile_photo, skills_offered, skills_wanted,
             availability, is_public, theme, user_id)
        )
        db.commit()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = cursor.fetchone()
        updated_user_dict = dict(updated_user)
        updated_user_dict['skills_offered'] = updated_user_dict['skills_offered'].split(',') if updated_user_dict['skills_offered'] else []
        updated_user_dict['skills_wanted'] = updated_user_dict['skills_wanted'].split(',') if updated_user_dict['skills_wanted'] else []
        updated_user_dict.pop('password_hash', None) # Don't send hash to frontend

        return jsonify(updated_user_dict), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    db = get_db()
    cursor = db.cursor()
    search_term = request.args.get('searchTerm', '').lower()

    query = "SELECT * FROM users WHERE is_public = 1 AND is_banned = 0"
    params = []

    if search_term:
        query += " AND (LOWER(name) LIKE ? OR LOWER(skills_offered) LIKE ? OR LOWER(skills_wanted) LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])

    cursor.execute(query, params)
    users = cursor.fetchall()
    
    users_list = []
    for user in users:
        user_dict = dict(user)
        user_dict['skills_offered'] = user_dict['skills_offered'].split(',') if user_dict['skills_offered'] else []
        user_dict['skills_wanted'] = user_dict['skills_wanted'].split(',') if user_dict['skills_wanted'] else []
        user_dict.pop('password_hash', None) # Don't send hash to frontend
        users_list.append(user_dict)
    
    return jsonify(users_list), 200

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
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    cursor = db.cursor()
    request_id = str(uuid.uuid4())
    timestamp = int(time.time())

    cursor.execute(
        '''INSERT INTO swap_requests (id, sender_id, sender_name, receiver_id,
           receiver_name, skill_offered, skill_wanted, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (request_id, sender_id, sender_name, receiver_id, receiver_name,
         skill_offered, skill_wanted, 'pending', timestamp)
    )
    db.commit()
    return jsonify({"message": "Swap request created", "requestId": request_id}), 201

@app.route('/api/swap_requests/<user_id>', methods=['GET'])
def get_user_swap_requests(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM swap_requests WHERE sender_id = ? OR receiver_id = ?",
        (user_id, user_id)
    )
    requests = cursor.fetchall()
    return jsonify([dict(req) for req in requests]), 200

@app.route('/api/swap_requests/<request_id>', methods=['PUT', 'DELETE'])
def manage_swap_request(request_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'PUT':
        data = request.get_json()
        status = data.get('status')
        if status not in ['accepted', 'rejected']:
            return jsonify({"error": "Invalid status"}), 400
        
        cursor.execute("UPDATE swap_requests SET status = ? WHERE id = ?", (status, request_id))
        db.commit()
        return jsonify({"message": f"Swap request {status}"}), 200

    elif request.method == 'DELETE':
        cursor.execute("DELETE FROM swap_requests WHERE id = ?", (request_id,))
        db.commit()
        return jsonify({"message": "Swap request deleted"}), 200

@app.route('/api/feedback', methods=['POST', 'GET'])
def handle_feedback():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        data = request.get_json()
        swap_request_id = data.get('swapRequestId')
        giver_id = data.get('giverId')
        receiver_id = data.get('receiverId')
        rating = data.get('rating')
        comment = data.get('comment')

        if not all([swap_request_id, giver_id, receiver_id, rating]):
            return jsonify({"error": "Missing required feedback fields"}), 400
        
        feedback_id = str(uuid.uuid4())
        timestamp = int(time.time())

        cursor.execute(
            '''INSERT INTO feedback (id, swap_request_id, giver_id, receiver_id, rating, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (feedback_id, swap_request_id, giver_id, receiver_id, rating, comment, timestamp)
        )
        db.commit()
        return jsonify({"message": "Feedback submitted successfully", "feedbackId": feedback_id}), 201
    
    elif request.method == 'GET':
        # Admin or public view of feedback (adjust as needed for security)
        cursor.execute("SELECT * FROM feedback")
        feedback_logs = cursor.fetchall()
        return jsonify([dict(log) for log in feedback_logs]), 200

# --- Admin Endpoints ---
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    # In a real app, you'd add authentication/authorization here to ensure
    # only admins can access this. For this example, we assume access.
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, location, skills_offered, skills_wanted, is_public, is_admin, is_banned, created_at FROM users")
    users = cursor.fetchall()
    users_list = []
    for user in users:
        user_dict = dict(user)
        user_dict['skills_offered'] = user_dict['skills_offered'].split(',') if user_dict['skills_offered'] else []
        user_dict['skills_wanted'] = user_dict['skills_wanted'].split(',') if user_dict['skills_wanted'] else []
        users_list.append(user_dict)
    return jsonify(users_list), 200

@app.route('/api/admin/users/<user_id>/ban', methods=['PUT'])
def admin_ban_user(user_id):
    # Again, add admin authentication/authorization
    data = request.get_json()
    is_banned = int(data.get('isBanned')) # 0 for unban, 1 for ban
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_banned = ? WHERE id = ?", (is_banned, user_id))
    db.commit()
    status_message = "banned" if is_banned else "unbanned"
    return jsonify({"message": f"User {user_id} {status_message} successfully"}), 200

@app.route('/api/admin/swap_requests', methods=['GET'])
def admin_get_all_swap_requests():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM swap_requests")
    requests = cursor.fetchall()
    return jsonify([dict(req) for req in requests]), 200

@app.route('/api/admin/platform_message', methods=['GET', 'POST'])
def platform_message():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message')
        if not message:
            return jsonify({"error": "Message content is required"}), 400
        
        # Clear existing messages and add new one, or update a single entry
        cursor.execute("DELETE FROM platform_messages") # Simplistic: only one message at a time
        cursor.execute("INSERT INTO platform_messages (message) VALUES (?)", (message,))
        db.commit()
        return jsonify({"message": "Platform message updated successfully"}), 200
    
    elif request.method == 'GET':
        cursor.execute("SELECT message FROM platform_messages ORDER BY created_at DESC LIMIT 1")
        message = cursor.fetchone()
        if message:
            return jsonify({"message": message['message']}), 200
        return jsonify({"message": ""}), 200 # Return empty if no message

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
