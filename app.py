import json
import os
import time
from turtle import tracer
from flask import Flask, render_template, request, redirect, url_for, flash, g
import logging
from logging.handlers import RotatingFileHandler
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'
TELEMETRY_FILE = 'telemetry_data.json'

# Telemetry Data Storage
telemetry_data = {
    "route_requests": {},
    "route_processing_time": {},
    "errors": {}
}
tracer = trace.get_tracer(__name__)
# OpenTelemetry Configuration
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
FlaskInstrumentor().instrument_app(app)

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
    



# File logging with rotation
file_handler = RotatingFileHandler('application.log', maxBytes=5 * 1024 * 1024, backupCount=2)
file_handler.setFormatter(JsonFormatter())


logging.basicConfig(level=logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger('JsonLogger')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(handler)

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        return []  # Return an empty list if the file doesn't exist
    with tracer.start_as_current_span("Load Courses") as span:
        with open(COURSE_FILE, 'r') as file:
            courses = json.load(file)
            span.set_attribute("course.count", len(courses))
            return courses

def save_courses(data):
    """Save new course data to the JSON file."""
    with tracer.start_as_current_span("Save Courses") as span:
        span.set_attribute("course.name", data["name"])
        span.set_attribute("course.code", data["code"])
        courses = load_courses()
        courses.append(data)
        with open(COURSE_FILE, 'w') as file:
            json.dump(courses, file, indent=4)
    logger.info(f"Course added: {data['name']} (Code: {data['code']})")

def save_telemetry():
    """Save telemetry data to the JSON file."""
    with open(TELEMETRY_FILE, 'w') as file:
        json.dump(telemetry_data, file, indent=4)

# Telemetry Tracking
@app.before_request
def before_request():
    g.start_time = time.time()
    route = request.endpoint
    telemetry_data["route_requests"].setdefault(route, 0)
    telemetry_data["route_requests"][route] += 1
    logger.info(f"Processing request for route: {route}")

@app.after_request
def after_request(response):
    route = request.endpoint
    processing_time = time.time() - g.start_time
    telemetry_data["route_processing_time"].setdefault(route, 0)
    telemetry_data["route_processing_time"][route] += processing_time
    logger.info(f"Route '{route}' processed in {processing_time:.4f} seconds")
    save_telemetry()
    return response

def log_error(error_message):
    telemetry_data["errors"].setdefault(error_message, 0)
    telemetry_data["errors"][error_message] += 1
    logger.error(error_message)
    save_telemetry()

# Routes
@app.route('/')
def index():
    with tracer.start_as_current_span("Render Index") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("client.ip", request.remote_addr)
    logger.info("Rendering index page")
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    with tracer.start_as_current_span("Render Course Catalog") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("client.ip", request.remote_addr)
        courses = load_courses()
        span.set_attribute("course.count", len(courses))
    logger.info("Rendering course catalog page")
    return render_template('course_catalog.html', courses=courses)

@app.route('/course/<code>')
def course_details(code):
    with tracer.start_as_current_span("View Course Details") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("client.ip", request.remote_addr)
        span.set_attribute("course.code", code)
        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
    if not course:
        error_message = f"No course found with code '{code}'."
        span.set_attribute("error.message", error_message)
        span.set_attribute("course.exists", False)
        log_error(error_message)
        flash(error_message, "error")
        return redirect(url_for('course_catalog'))
    logger.info(f"Rendering details for course: {course['name']} (Code: {course['code']})")
    span.set_attribute("course.exists", True)
    span.set_attribute("course.name", course["name"])
    return render_template('course_details.html', course=course)

@app.route('/form')
def forming():
    # Start a span for the "Render Form" operation
    with tracer.start_as_current_span("Render Form") as span:
        # Add trace attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("client.ip", request.remote_addr)
        span.set_attribute("form.name", "Course Submission Form")
        
        # Log the rendering of the form
        logger.info("Rendering course addition form")
        
        # Render the form template
        return render_template("form.html")

@app.route('/submit_detail', methods=["POST", "GET"])
def submitting():
    with tracer.start_as_current_span("Submit Course Details") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("client.ip", request.remote_addr)

        code = request.form.get("code")
        name = request.form.get("name")
        instructor = request.form.get("instructor")
        semester = request.form.get("semester")
        schedule = request.form.get("schedule")
        classroom = request.form.get("classroom")
        prerequisites = request.form.get("prerequisites")
        grading = request.form.get("grading")
        description = request.form.get("description")

    if not all([code, name, instructor, semester]):
        error_message = "Some fields were missing. Course Not Added."
        span.set_attribute("error.message", error_message)
        log_error(error_message)
        flash(error_message, "error")
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
        span.set_attribute("course.name", name)
        span.set_attribute("course.code", code)
        flash(f"Course '{name}' has been successfully added!", "success")
    return redirect(url_for('course_catalog'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
