# Project: Skill Swap Platform 

## Problem Statement
Develop a Skill Swap Platform — a mini application that enables users to list their skills and
request others in return


## Team Members

| S.No | Name                   | Email                        |
|------|------------------------|------------------------------|
| 1    | Rachit Yadav           | rachit4yadav40@gmail.com     |
| 2    | Saurav Anand Jha       | x09tecozac@gmail.com         |
| 3    | Aditya Vikram Singh    | adityavs674@gmail.com        |
| 4    | Ishaan Jayaram Shetty  | shettyishaan49@gmail.com     |


## Features

- *Basic info:* Name, location (optional), profile photo (optional)
- *List of skills offered*
- *List of skills wanted*
- *Availability (e.g., weekends, evenings)*
- *User can make their profile public or private*
- *Users can browse or search others by skill (e.g., "Photoshop" or "Excel")*
- *Request & Accept Swaps:*
  - Accept or reject swap offers
  - Show current and pending swap requests
- *Ratings or feedback after a swap*
- *The user is also able to delete the swap request if it is not accepted*


## Admin Role Features

- Reject inappropriate or spammy skill descriptions.
- Ban users who violate platform policies.
- Monitor pending, accepted, or cancelled swaps.
- Send platform-wide messages (e.g., feature updates, downtime alerts).
- Download reports of user activity, feedback logs, and swap stats.


```markdown
# Skill Swap Platform

A simple web application built with Flask (Python) for the backend and React (JavaScript) for the frontend, allowing users to connect, offer, and request skills. It includes user authentication, profile management with image uploads, skill browsing, and a swap request system.

## ✨ Features

* **User Authentication:** Secure signup and login functionality.

* **User Profiles:**

    * Create and manage personal profiles.

    * Specify skills offered and skills wanted.

    * Set availability and location.

    * **Profile Photo Upload:** Upload a profile picture directly from your device or link to an external URL.

    * Choose a preferred theme (Indigo, Purple, Green).

    * Option to make profile public or private.

* **Browse Skills:** Discover other public users and the skills they offer or want.

* **Swap Requests:** Send and manage requests to swap skills with other users.

    * View pending, accepted, and rejected requests.

    * Accept or reject incoming requests.

* **Feedback System:** Provide feedback (rating and comment) after a swap request is accepted.

* **Admin Panel:** (Accessible only to admin users)

    * Manage user accounts (view, ban/unban).

    * Monitor all swap requests.

    * View feedback logs.

    * Send platform-wide announcements.

    * Download various reports (User Activity, Feedback Logs, Swap Statistics).

## 🚀 Technologies Used

**Backend:**
* **Flask:** A lightweight Python web framework.
* **SQLite3:** A file-based SQL database for data storage.
* **Flask-CORS:** For handling Cross-Origin Resource Sharing.
* **Werkzeug:** For secure password hashing.
* **`os` & `uuid`:** Python standard libraries for file system operations and unique ID generation.

**Frontend:**
* **React:** A JavaScript library for building user interfaces (used via CDN for simplicity).
* **Tailwind CSS:** A utility-first CSS framework for rapid styling (used via CDN).
* **HTML5 & CSS3:** Standard web technologies.

## 🛠️ Setup Instructions

Follow these steps to get the Skill Swap Platform up and running on your local machine.

### Prerequisites

* **Python 3.x:** Make sure you have Python installed.
* **`pip`:** Python's package installer (usually comes with Python).

### 1. Project Structure

Ensure your project directory is structured as follows:

```

skill\_swap\_platform/
├── app.py
├── skill\_swap.db (will be created automatically)
├── uploads/ (will be created automatically, for profile photos)
└── html\_templates/
└── index.html

````

### 2. Backend Setup (`app.py`)

1.  **Navigate to the project directory:**
    ```bash
    cd skill_swap_platform
    ```

2.  **Create a Python Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    * **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install Required Python Packages:**
    ```bash
    pip install Flask Flask-Cors Werkzeug
    ```

5.  **Initialize the Database:**
    * The `app.py` script automatically initializes an SQLite database named `skill_swap.db` and creates necessary tables (users, swap_requests, feedback, platform_messages) on its first run.
    * **IMPORTANT:** If you have an existing `skill_swap.db` from a previous version and encounter issues (especially with profile photos or new features), **delete the `skill_swap.db` file** before running `app.py` again. This ensures a fresh database with the correct schema.
    * A default admin user with username `admin` and password `adminpass` will be created if it doesn't already exist.

6.  **Ensure `uploads` Folder Exists:**
    * The `app.py` script will attempt to create an `uploads` directory. Verify that an empty folder named `uploads` exists in your `skill_swap_platform` directory. This is where uploaded profile pictures will be stored.

### 3. Frontend Setup (`index.html`)

The frontend is a single `index.html` file that uses React and Tailwind CSS via CDN links, so no `npm install` or build step is required.

1.  Place the `index.html` file inside the `html_templates` directory.

### 4. Running the Application

1.  **Start the Backend Server:**
    * In your terminal (with the virtual environment activated), run:
        ```bash
        python app.py
        ```
    * You should see output indicating the Flask server is running, typically on `http://127.0.0.1:5000/`. Keep this terminal window open.

2.  **Access the Frontend:**
    * Open your web browser and navigate to:
        ```
        [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
        ```
    * **Important for updates/changes:** If you make changes to `index.html` or `app.py`, always perform a **hard refresh** in your browser to ensure the latest frontend code is loaded:
        * **Windows/Linux:** `Ctrl + Shift + R` or `Ctrl + F5`
        * **macOS:** `Cmd + Shift + R`

## 👨‍💻 Usage

1.  **Sign Up:** Create a new user account. You can specify your name, password, location, skills offered, skills wanted, availability, and whether your profile is public.
2.  **Login:** Use your registered username and password to log in.
3.  **My Profile:**
    * Update your profile details.
    * **Upload a profile picture:** Use the "Upload Photo from Device" option to select an image file. The image will be saved to the `uploads` folder on the server.
    * You can also paste a direct image URL in the "Or Paste Photo URL" field.
    * Change your theme.
4.  **Browse Skills:** Explore public profiles of other users. You can search for users by name or skills.
5.  **Swap Requests:**
    * Click "Request Swap" on another user's card to send a request.
    * Go to the "Swap Requests" tab to view your pending, accepted, and rejected requests.
    * If you receive a request, you can accept or reject it.
6.  **Admin Panel:**
    * Log in as the `admin` user (password: `adminpass`).
    * Access the "Admin" tab in the navigation.
    * Manage users, monitor all swap requests, view feedback, send platform-wide messages, and download reports.

## 📁 File Structure

* `app.py`: The Flask backend application, handling API routes, database interactions, and serving static files.
* `html_templates/`: Contains the `index.html` file for the frontend.
* `uploads/`: Stores user-uploaded profile pictures.
* `skill_swap.db`: The SQLite database file (created automatically on first run).

## ⚠️ Troubleshooting

* **"No Photo Upload Option" / Old Frontend:** Perform a **hard refresh** in your browser (`Ctrl+Shift+R` or `Cmd+Shift+R`). Browser caching is a common culprit.
* **"Swap Request Count Always Zero" / Data Issues:**
    * **Delete `skill_swap.db`** and restart `app.py`. This ensures a clean database schema.
    * Check the terminal where `app.py` is running for any error messages or debug prints (e.g., "Fetched X swap requests...").
* **"Network Error" / "Failed to fetch":**
    * Ensure your Flask backend (`app.py`) is running in a terminal.
    * Verify that the `BASE_URL` in `index.html` (`http://127.0.0.1:5000`) matches the address where your Flask app is running.
* **"User not found" / Login Issues:**
    * Make sure you are using the correct username and password.
    * If you deleted `skill_swap.db`, the admin user (`admin`/`adminpass`) will be recreated. Other users will need to sign up again.
* **Uploaded images not appearing:**
    * Check if the `uploads` folder exists in your project directory.
    * Verify that the image files are actually being saved into the `uploads` folder.
    * Ensure the `uploaded_file` route in `app.py` is correctly serving files from the `uploads` directory.

## 💡 Future Enhancements

* **User Search Improvements:** More advanced filtering and sorting options.
* **Real-time Notifications:** Use WebSockets for instant notifications on new swap requests or status updates.
* **Messaging System:** Allow users to directly message each other after a swap is accepted.
* **Skill Categories:** Organize skills into categories for easier browsing.
* **User Ratings/Reviews:** Expand the feedback system to include public ratings and reviews on user profiles.
* **More Robust Authentication:** Implement JWTs or OAuth for better security.
* **Deployment:** Prepare the application for deployment to a cloud platform (e.g., Heroku, AWS, Google Cloud).
````
 
