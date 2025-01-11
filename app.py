import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'


# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    courses = load_courses()
    return render_template('course_catalog.html', courses=courses)


@app.route('/course/<code>')
def course_details(code):
    courses = load_courses()
    course = next((course for course in courses if course['code'] == code), None)
    if not course:
        flash(f"No course found with code '{code}'.", "error")
        return redirect(url_for('course_catalog'))
    return render_template('course_details.html', course=course)

@app.route('/form')
def forming():
    return render_template("form.html")
@app.route('/submit_detail',methods=["POST","GET"])
def submitting():
    code=request.form["code"]
    name=request.form["name"]
    instructor=request.form["instructor"]
    semester=request.form["semester"]
    schedule=request.form["schedule"]
    classroom=request.form["classroom"]
    prerequisites=request.form["prerequisites"]
    grading=request.form["grading"]
    description=request.form["description"]
    course={"code":code,"name":name,"instructor":instructor,"semester":semester,"schedule":schedule,"classroom":classroom,
            "prerequisites":prerequisites,"grading":grading,"description":description}
    save_courses(course) 
    flash(f"Course '{name}' has been successfully added!", "success")
    return redirect(url_for('course_catalog'))
   
if __name__ == '__main__':
    app.run(debug=True)
