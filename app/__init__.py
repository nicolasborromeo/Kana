import os
from flask import Flask, render_template, request, session, redirect, jsonify, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_login import LoginManager
from .models import db, User
from .api.user_routes import user_routes
from .api.auth_routes import auth_routes
from .api.avatar_routes import avatar_routes
from .api.parts_routes import parts_routes
from .api.habit_routes import habit_routes
from .api.todos_routes import todos_routes
from .api.daily_routes import daily_routes
from .api.inventory_routes import inventory_routes
from .api.rewards_routes import rewards_routes
from .api.tag_routes import tag_routes
from .seeds import seed_commands
from .config import Config

app = Flask(__name__, static_folder='../react-vite/dist', static_url_path='/')

# Setup login manager
login = LoginManager(app)
login.login_view = 'auth.unauthorized'


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# Tell flask about our seed commands
app.cli.add_command(seed_commands)

app.config.from_object(Config)
app.register_blueprint(user_routes, url_prefix='/api/users')
app.register_blueprint(auth_routes, url_prefix='/api/auth')
app.register_blueprint(avatar_routes, url_prefix='/api/avatars')

app.register_blueprint(parts_routes,url_prefix='/api/')

app.register_blueprint(habit_routes,url_prefix='/api/habits')
app.register_blueprint(todos_routes,url_prefix='/api/todos')
app.register_blueprint(daily_routes, url_prefix='/api/dailies')
app.register_blueprint(inventory_routes,url_prefix='/api/inventory')
app.register_blueprint(rewards_routes,url_prefix='/api/rewards')
app.register_blueprint(tag_routes, url_prefix="/api/tags")

db.init_app(app)
Migrate(app, db)

# Application Security
CORS(app)


# Since we are deploying with Docker and Flask,
# we won't be using a buildpack when we deploy to Heroku.
# Therefore, we need to make sure that in production any
# request made over http is redirected to https.
# Well.........
@app.before_request
def https_redirect():
    if os.environ.get('FLASK_ENV') == 'production':
        if request.headers.get('X-Forwarded-Proto') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            code = 301
            return redirect(url, code=code)


@app.after_request
def inject_csrf_token(response):
    response.set_cookie(
        'csrf_token',
        generate_csrf(),
        secure=True if os.environ.get('FLASK_ENV') == 'production' else False,
        samesite='Strict' if os.environ.get(
            'FLASK_ENV') == 'production' else None,
        httponly=True)
    return response

@app.route("/api/csrf/restore", methods=["GET"])
def restore_csrf():
    if os.environ.get("FLASK_ENV") != "production":
        csrf_token = generate_csrf()  # Generate a new CSRF Token
        response = make_response(jsonify({"XSRF-Token": csrf_token}))
        #Set the CSRF Token as a cookie
        response.set_cookie(
            "XSRF-TOKEN",
            csrf_token,
            samesite="Strict" if os.environ.get("FLASK_ENV") == "production" else None
        )
        return response


@app.route("/api/docs")
def api_help():
    """
    Returns all API routes and their doc strings
    """
    acceptable_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
    route_list = { rule.rule: [[ method for method in rule.methods if method in acceptable_methods ],
                    app.view_functions[rule.endpoint].__doc__ ]
                    for rule in app.url_map.iter_rules() if rule.endpoint != 'static' }
    return route_list


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def react_root(path):
    """
    This route will direct to the public directory in our
    react builds in the production environment for favicon
    or index.html requests
    """
    if path == 'favicon.ico':
        return app.send_from_directory('public', 'favicon.ico')
    return app.send_static_file('index.html')


@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')