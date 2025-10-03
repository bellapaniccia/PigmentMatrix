import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

# Flask setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pigments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "2446"

# Upload folder
app.config['UPLOAD_FOLDER'] = os.path.join("static", "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Many-to-many table for saved pigments
saved_pigments = db.Table(
    'saved_pigments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('pigment_id', db.Integer, db.ForeignKey('pigment.id'), primary_key=True)
)

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    saved_pigments = db.relationship(
        'Pigment',
        secondary=saved_pigments,
        backref=db.backref('users_who_saved', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Pigment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kremer_id = db.Column(db.String(50), nullable=True)
    pigment_name = db.Column(db.String(100), nullable=False)
    fcir = db.Column(db.String(100), nullable=False)
    cir = db.Column(db.String(100), nullable=False)
    image_truecolor = db.Column(db.String(100), nullable=True)
    image_fcir = db.Column(db.String(100), nullable=True)
    image_cir = db.Column(db.String(100), nullable=True)
    position = db.Column(db.Integer, default=0)

# Admin decorator
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for('register'))

        if User.query.filter((User.username==username)|(User.email==email)).first():
            flash("Username or email already exists")
            return redirect(url_for('register'))

        user = User(username=username, email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('view'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('login')  # username or email
        password = request.form.get('password')

        user = User.query.filter((User.username==login_input)|(User.email==login_input)).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('view'))

        flash("Invalid username/email or password")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/view')
def view():
    pigments = Pigment.query.order_by(Pigment.position).all()
    saved_ids = []
    if current_user.is_authenticated:
        saved_ids = [p.id for p in current_user.saved_pigments]
    return render_template('view.html', pigments=pigments, saved_ids=saved_ids)

@app.route('/view/<int:pid>')
def view_one(pid):
    pigments = Pigment.query.order_by(Pigment.position).all()
    pigment = Pigment.query.get_or_404(pid)

    # Find index and neighbors
    index = pigments.index(pigment)
    prev_id = pigments[index - 1].id if index > 0 else pigments[-1].id
    next_id = pigments[index + 1].id if index < len(pigments) - 1 else pigments[0].id

    # Build saved_ids robustly (works whether relationship is dynamic or not)
    saved_ids = []
    if current_user.is_authenticated:
        saved_rel = current_user.saved_pigments
        # if dynamic -> .all() exists, else saved_rel is a list
        saved_list = saved_rel.all() if hasattr(saved_rel, "all") else saved_rel
        saved_ids = [p.id for p in saved_list]

    return render_template(
        'view_one.html',
        pigment=pigment,
        prev_id=prev_id,
        next_id=next_id,
        saved_ids=saved_ids
    )

@app.route('/save/<int:pid>', methods=['POST'])
@login_required
def save_pigment(pid):
    pigment = Pigment.query.get_or_404(pid)

    # Works for both dynamic and normal relationships:
    is_saved = False
    saved_rel = current_user.saved_pigments
    if hasattr(saved_rel, "filter_by"):
        # dynamic relationship
        is_saved = True if saved_rel.filter_by(id=pid).first() else False
    else:
        # list-like relationship
        is_saved = pigment in saved_rel

    if is_saved:
        # remove (unsave)
        try:
            current_user.saved_pigments.remove(pigment)
        except Exception:
            # fallback: delete from association table directly
            db.session.execute(
                saved_pigments.delete().where(
                    (saved_pigments.c.user_id == current_user.id) &
                    (saved_pigments.c.pigment_id == pid)
                )
            )
    else:
        # add (save)
        try:
            current_user.saved_pigments.append(pigment)
        except Exception:
            # fallback: insert into association table directly
            db.session.execute(
                saved_pigments.insert().values(user_id=current_user.id, pigment_id=pid)
            )

    db.session.commit()
    return redirect(request.referrer or url_for('view'))

@app.route('/profile')
@login_required
def profile():
    pigments = current_user.saved_pigments.all()  # dynamic relationships need .all()
    return render_template('profile.html', pigments=pigments)

# Admin CRUD
@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    if request.method == 'POST':
        kremer_id = request.form.get('kremer_id')
        pigment_name = request.form.get('pigment_name')
        fcir = request.form.get('fcir', '')
        cir = request.form.get('cir', '')

        def save_image(field_name):
            file = request.files.get(field_name)
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return filename
            return None

        new_pigment = Pigment(
            kremer_id=kremer_id,
            pigment_name=pigment_name,
            fcir=fcir,
            cir=cir,
            image_truecolor=save_image('image_truecolor'),
            image_fcir=save_image('image_fcir'),
            image_cir=save_image('image_cir')
        )
        db.session.add(new_pigment)
        db.session.commit()
        return redirect(url_for('view'))

    return render_template('index.html')

@app.route('/edit/<int:pigment_id>', methods=['GET', 'POST'])
@admin_required
def edit(pigment_id):
    pigment = Pigment.query.get_or_404(pigment_id)
    if request.method == 'POST':
        pigment.kremer_id = request.form.get('kremer_id')
        pigment.pigment_name = request.form.get('pigment_name')
        pigment.fcir = request.form.get('fcir')
        pigment.cir = request.form.get('cir')

        def save_image(field_name, current_value):
            file = request.files.get(field_name)
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return filename
            return current_value

        pigment.image_truecolor = save_image('image_truecolor', pigment.image_truecolor)
        pigment.image_fcir = save_image('image_fcir', pigment.image_fcir)
        pigment.image_cir = save_image('image_cir', pigment.image_cir)

        db.session.commit()
        return redirect(url_for('view'))

    return render_template('edit.html', pigment=pigment)

@app.route('/delete/<int:pigment_id>', methods=['POST'])
@admin_required
def delete_pigment(pigment_id):
    pigment = Pigment.query.get_or_404(pigment_id)
    db.session.delete(pigment)
    db.session.commit()
    return redirect(url_for('view'))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.username).all()
    return render_template('admin_users.html', users=users)

@app.cli.command("create-admin")
def create_admin():
    import getpass
    username = input("Admin username: ")
    email = input("Admin email: ")
    first_name = input("First name: ")
    last_name = input("Last name: ")
    password = getpass.getpass("Password: ")

    if User.query.filter((User.username==username)|(User.email==email)).first():
        print("User with that username or email already exists.")
        return

    user = User(username=username, email=email, first_name=first_name, last_name=last_name, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Admin user '{username}' created successfully!")

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('password')
        confirm = request.form.get('confirm')

        if new_password != confirm:
            flash("Passwords do not match")
            return redirect(url_for('reset_password'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("No user found with that username")
            return redirect(url_for('reset_password'))

        user.set_password(new_password)
        db.session.commit()
        flash("Password updated successfully!")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# Init database
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
