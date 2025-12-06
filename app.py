from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()
import config


app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# Supabase client
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
        port=config.MYSQL_PORT
    )

# Home page
@app.route('/')
def home():
    return render_template('home.html')

# Register
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",  (username, email, password))
            db.commit()
            cursor.close()
        except Exception as e:
             return "DULPICATE ENTRY. Email already registered. OR An error occurred.PLS try again."    
        db.close()
        return redirect('/login')

    return render_template('register.html')

# Login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
    
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect('/upload')

        return "Invalid credentials"

    return render_template('login.html')

# Upload page
@app.route('/upload', methods=['GET','POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_path = f"{session['user_id']}/{file.filename}"

            # Read file content as bytes
            file_bytes = file.read()

            # Upload to Supabase
            supabase.storage.from_(config.BUCKET_NAME).upload(file_path, file_bytes)

            file_url = f"{config.SUPABASE_URL}/storage/v1/object/public/{config.BUCKET_NAME}/{file_path}"

            # Save file info in MySQL
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("INSERT INTO files (user_id,file_name,file_url) VALUES (%s,%s,%s)",
                        (session['user_id'], file.filename, file_url))
            db.commit()
            return f"thank you and File uploaded successfully: <a href='{"/upload"}'>click here</a>"


    return render_template('upload.html')

@app.route('/logout')
def logout():
    session.clear()  # removes all session data
    return redirect('/')
if __name__ == "__main__":
    app.run(debug=True)
