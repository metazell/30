import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm
from models import db, connect_db, User, Message

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///warbler')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
app.config['DEBUG'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# Disable the versions panel
app.config['DEBUG_TB_PANELS'] = [
    'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
    'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
    'flask_debugtoolbar.panels.template.TemplateDebugPanel',
    'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
    'flask_debugtoolbar.panels.logger.LoggingPanel',
    'flask_debugtoolbar.panels.timer.TimerDebugPanel',
    'flask_debugtoolbar.panels.route_list.RouteListDebugPanel',
]

toolbar = DebugToolbarExtension(app)
connect_db(app)

# Your routes and other configurations here...

if __name__ == "__main__":
    app.run(debug=True)


##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    g.user = User.query.get(session[CURR_USER_KEY]) if CURR_USER_KEY in session else None

def do_login(user):
    """Log in user."""
    session[CURR_USER_KEY] = user.id

def do_logout():
    """Logout user."""
    session.pop(CURR_USER_KEY, None)

@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup."""
    if CURR_USER_KEY in session:
        do_logout()

    form = UserAddForm()
    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()
            do_login(user)
            return redirect("/")
        except IntegrityError:
            flash("Username already taken", 'danger')
            db.session.rollback()

    return render_template('users/signup.html', form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)
        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")
        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)

@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    flash("You have successfully logged out.", 'success')
    return redirect("/login")

##############################################################################
# General user routes

@app.route('/users')
def list_users():
    """Page with listing of users."""
    search = request.args.get('q')
    users = User.query.filter(User.username.like(f"%{search}%")).all() if search else User.query.all()
    return render_template('users/index.html', users=users)

@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""
    user = User.query.get_or_404(user_id)
    messages = (Message.query.filter(Message.user_id == user_id).order_by(Message.timestamp.desc()).limit(100).all())
    likes = [message.id for message in user.likes]
    return render_template('users/show.html', user=user, messages=messages, likes=likes)

@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)

@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)

@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()
    return redirect(f"/users/{g.user.id}/following")

@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()
    return redirect(f"/users/{g.user.id}/following")

@app.route('/users/<int:user_id>/likes', methods=["GET"])
def show_likes(user_id):
    """Show list of messages liked by the user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)

@app.route('/messages/<int:message_id>/like', methods=['POST'])
def add_like(message_id):
    """Toggle a liked message for the currently-logged-in user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    liked_message = Message.query.get_or_404(message_id)
    if liked_message.user_id == g.user.id:
        return abort(403)
    if liked_message in g.user.likes:
        g.user.likes.remove(liked_message)
    else:
        g.user.likes.append(liked_message)
    db.session.commit()
    return redirect("/")

@app.route('/users/profile', methods=["GET", "POST"])
def edit_profile():
    """Update profile for current user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = g.user
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            user.bio = form.bio.data
            db.session.commit()
            return redirect(f"/users/{user.id}")
        flash("Wrong password, please try again.", 'danger')
    return render_template('users/edit.html', form=form, user_id=user.id)

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    do_logout()
    db.session.delete(g.user)
    db.session.commit()
    return redirect("/signup")

##############################################################################
# Messages routes

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()
        return redirect(f"/users/{g.user.id}")
    return render_template('messages/new.html', form=form)

@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""
    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)

@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    msg = Message.query.get_or_404(message_id)
    if msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    db.session.delete(msg)
    db.session.commit()
    return redirect(f"/users/{g.user.id}")

##############################################################################
# Homepage and error pages

@app.route('/')
def homepage():
    """Show homepage."""
    if g.user:
        following_ids = [f.id for f in g.user.following] + [g.user.id]
        messages = (Message.query.filter(Message.user_id.in_(following_ids))
                    .order_by(Message.timestamp.desc()).limit(100).all())
        liked_msg_ids = [msg.id for msg in g.user.likes]
        return render_template('home.html', messages=messages, likes=liked_msg_ids)
    return render_template('home-anon.html')

@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""
    return render_template('404.html'), 404

##############################################################################
# Turn off all caching in Flask
# (useful for dev; in production, this kind of stuff is typically handled elsewhere)
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""
    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
