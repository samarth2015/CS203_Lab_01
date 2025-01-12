import json
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from logging.handlers import RotatingFileHandler
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.otlp import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
# Set up the trace provider
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: "course-catalog-service"})
    )
)


otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = SimpleSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)


# Instrument Flask with OpenTelemetry
FlaskInstrumentor().instrument_app(app)
LoggingInstrumentor().instrument()

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
        return []  
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  
    courses.append(data) 
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)

# Routes
@app.route('/')
def index():
    with trace.get_tracer("course-catalog").start_as_current_span("index_page"):
        return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    with trace.get_tracer("course-catalog").start_as_current_span("view_course_catalog") as span:
        span.set_attribute("user.ip", request.remote_addr)
        courses = load_courses()
        return render_template('course_catalog.html', courses=courses)

@app.route('/course/<code>')
def course_details(code):
    with trace.get_tracer("course-catalog").start_as_current_span("view_course_details") as span:
        span.set_attribute("user.ip", request.remote_addr)
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            flash(f"No course found with code '{code}'.", "error")
            return redirect(url_for('course_catalog'))
        return render_template('course_details.html', course=course)

@app.route('/form')
def forming():
    with trace.get_tracer("course-catalog").start_as_current_span("render_course_form"):
        return render_template("form.html")

@app.route('/submit_detail', methods=["POST", "GET"])
def submitting():
    with trace.get_tracer("course-catalog").start_as_current_span("submit_course_form") as span:
        span.set_attribute("user.ip", request.remote_addr)
        code = request.form["code"]
        name = request.form["name"]
        instructor = request.form["instructor"]
        semester = request.form["semester"]
        schedule = request.form["schedule"]
        classroom = request.form["classroom"]
        prerequisites = request.form["prerequisites"]
        grading = request.form["grading"]
        description = request.form["description"]

        if code == "" or name == "" or instructor == "" or semester == "":
            logger.error("Please fill in all the required fields")
            flash("Some fields were missing. Course not added", "error")
        else:
            course = {
                "code": code,
                "name": name,
                "instructor": instructor,
                "semester": semester,
                "schedule": schedule,
                "classroom": classroom,
                "prerequisites": prerequisites,
                "grading": grading,
                "description": description
            }
            save_courses(course)
            flash(f"Course '{name}' has been successfully added!", "success")
        return redirect(url_for('course_catalog'))

if __name__ == '__main__':
    app.run(debug=True)
