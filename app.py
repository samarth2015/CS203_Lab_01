import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Configuration
FlaskInstrumentor().instrument_app(app)

# Tracing Configuration
trace.set_tracer_provider(TracerProvider())
console_exporter = ConsoleSpanExporter()
span_processor = BatchSpanProcessor(console_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Logging Configuration
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Log to a file in JSON format
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger_name': record.name,
            'path': record.pathname,
            'line': record.lineno,
        }
        return json.dumps(log_record)

logging.basicConfig(level=logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger('JsonLogger')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

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
    if code == "" or name == "" or instructor == "" or semester == "":
        logger.error("Please fill in all the required fields")
        flash("Some field were missing. Course Not Added", "error")
    else:
        course={"code":code,"name":name,"instructor":instructor,"semester":semester,"schedule":schedule,"classroom":classroom,
                "prerequisites":prerequisites,"grading":grading,"description":description}
        save_courses(course) 
        flash(f"Course '{name}' has been successfully added!", "success")
    return redirect(url_for('course_catalog'))
   
if __name__ == '__main__':
    app.run(debug=True)
