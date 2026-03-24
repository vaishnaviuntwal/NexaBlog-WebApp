from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import secrets
from PIL import Image
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Association tables
likes = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

follows = db.Table('follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_image = db.Column(db.String(200), default='default.png')
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100), nullable=True)
    
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    liked = db.relationship('Post', secondary=likes, backref=db.backref('liked_by', lazy='dynamic'))
    following = db.relationship('User', secondary=follows,
        primaryjoin=(follows.c.follower_id == id),
        secondaryjoin=(follows.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def is_following(self, user):
        return self.following.filter(follows.c.followed_id == user.id).count() > 0

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def save_picture(form_picture, folder='profile_pics'):
    if form_picture and form_picture.filename:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_picture.filename)
        if f_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
            return None
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(current_app.root_path, 'static', folder, picture_fn)
        
        os.makedirs(os.path.dirname(picture_path), exist_ok=True)
        
        output_size = (200, 200) if folder == 'profile_pics' else (800, 400)
        try:
            img = Image.open(form_picture)
            img.thumbnail(output_size, Image.Resampling.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            img.save(picture_path, optimize=True, quality=85)
            return picture_fn
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    return None

# Routes
@app.route('/')
def index():
    filter_type = request.args.get('filter', 'all')
    page = request.args.get('page', 1, type=int)
    
    if filter_type == 'yesterday':
        yesterday = datetime.utcnow() - timedelta(days=1)
        posts_query = Post.query.filter(Post.timestamp >= yesterday)
    elif filter_type == 'week':
        week_ago = datetime.utcnow() - timedelta(days=7)
        posts_query = Post.query.filter(Post.timestamp >= week_ago)
    else:
        posts_query = Post.query
    
    posts = posts_query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('index.html', posts=posts, filter_type=filter_type)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return render_template("register.html")
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return render_template("register.html")
        
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash("Invalid username or password", "danger")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image_file')

        if not title or not content:
            flash('Title and content are required!', 'danger')
            return render_template('create_post.html')

        image_filename = None
        if image and image.filename != '':
            image_filename = save_picture(image, folder='post_pics')
            if not image_filename:
                flash('Invalid image file! Please upload JPG, PNG, or GIF.', 'warning')

        new_post = Post(title=title, content=content, image_file=image_filename, author=current_user)
        db.session.add(new_post)
        db.session.commit()

        flash('Post created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('create_post.html')

@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).paginate(page=page, per_page=5, error_out=False)
    
    is_following = current_user.is_authenticated and current_user.is_following(user)
    
    return render_template('profile.html', user=user, posts=posts, is_following=is_following)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        new_bio = request.form.get('bio', '').strip()
        
        # Check if username is taken by another user
        if new_username != current_user.username:
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                flash('Username already taken!', 'danger')
                return render_template('edit_profile.html')
        
        # Check if email is taken by another user
        if new_email != current_user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email:
                flash('Email already registered!', 'danger')
                return render_template('edit_profile.html')
        
        current_user.username = new_username
        current_user.email = new_email
        current_user.bio = new_bio
        
        picture = request.files.get('picture')
        if picture and picture.filename:
            picture_file = save_picture(picture)
            if picture_file:
                # Delete old profile picture if it's not the default
                if current_user.profile_image != 'default.png':
                    old_picture_path = os.path.join(current_app.root_path, 'static', 'profile_pics', current_user.profile_image)
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                current_user.profile_image = picture_file
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile', user_id=current_user.id))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
            print(f"Database error: {e}")
    
    return render_template('edit_profile.html')

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user not in post.liked_by:
        current_user.liked.append(post)
        db.session.commit()
        return jsonify({'status': 'liked', 'likes_count': post.liked_by.count()})
    return jsonify({'status': 'already_liked', 'likes_count': post.liked_by.count()})

@app.route('/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user in post.liked_by:
        current_user.liked.remove(post)
        db.session.commit()
        return jsonify({'status': 'unliked', 'likes_count': post.liked_by.count()})
    return jsonify({'status': 'not_liked', 'likes_count': post.liked_by.count()})

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()
    
    if not content:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Comment cannot be empty'}), 400
        flash('Comment cannot be empty!', 'danger')
        return redirect(url_for('index'))
    
    if len(content) > 250:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Comment too long'}), 400
        flash('Comment too long! Maximum 250 characters.', 'danger')
        return redirect(url_for('index'))
    
    new_comment = Comment(content=content, author=current_user, post=post)
    db.session.add(new_comment)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'username': current_user.username,
            'profile_image': url_for('static', filename='profile_pics/' + current_user.profile_image),
            'content': content,
            'timestamp': 'Just now'
        })
    
    flash('Comment added!', 'success')
    return redirect(url_for('index'))

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        return jsonify({'error': 'You cannot follow yourself!'}), 400
    
    if not current_user.is_following(user):
        current_user.following.append(user)
        db.session.commit()
        return jsonify({'status': 'following', 'followers_count': user.followers.count()})
    
    return jsonify({'error': 'Already following!'}), 400

@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.is_following(user):
        current_user.following.remove(user)
        db.session.commit()
        return jsonify({'status': 'unfollowed', 'followers_count': user.followers.count()})
    
    return jsonify({'error': 'Not following!'}), 400

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(
        (Post.title.ilike(f'%{query}%')) | 
        (Post.content.ilike(f'%{query}%'))
    ).order_by(Post.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('search_results.html', posts=posts, query=query)

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        
        image = request.files.get('image')
        if image and image.filename:
            new_image = save_picture(image, folder='post_pics')
            if new_image:
                if post.image_file:
                    old_image_path = os.path.join(current_app.root_path, 'static', 'post_pics', post.image_file)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                post.image_file = new_image
        
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    
    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    if post.image_file:
        image_path = os.path.join(current_app.root_path, 'static', 'post_pics', post.image_file)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('profile', user_id=current_user.id))

# Password Reset Routes (Simple version without email)
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        user = User.query.filter_by(username=username, email=email).first()
        
        if user:
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
            elif len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
            else:
                user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
                db.session.commit()
                flash('Password has been reset successfully! You can now log in.', 'success')
                return redirect(url_for('login'))
        else:
            flash('No user found with that username and email combination.', 'danger')
        
        return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('File too large! Maximum size is 16MB.', 'danger')
    return redirect(request.url)

if __name__ == '__main__':
    with app.app_context():
        # Create all tables
        db.create_all()
        # Create upload directories if they don't exist
        os.makedirs(os.path.join(app.root_path, 'static', 'profile_pics'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'static', 'post_pics'), exist_ok=True)
        
        # Create default avatar if it doesn't exist
        default_avatar_path = os.path.join(app.root_path, 'static', 'profile_pics', 'default.png')
        if not os.path.exists(default_avatar_path):
            print("⚠️  Default avatar not found. Please run create_favicon.py to create one.")
        
        print("✅ Database and directories initialized!")
    
    app.run(debug=True)