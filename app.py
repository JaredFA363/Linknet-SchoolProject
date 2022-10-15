from flask import *
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from saltingalgo import salt_password
from data import Articles
import sqlite3
import re
from flask_bcrypt import Bcrypt
from flask_socketio import *
from flask_login import LoginManager,UserMixin, login_user, login_required,logout_user,current_user
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand


app = Flask(__name__)
app.secret_key = "@KyMEss12!4" 
app.permanent_session_lifetime = timedelta(minutes = 7) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app)

logins = LoginManager()
logins.init_app(app)
logins.login_view = 'login'

db = SQLAlchemy(app)
db.init_app(app)

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

bcrypt = Bcrypt(app)

Friends = db.Table('Friends',
     db.Column('sent_req',db.Integer, db.ForeignKey('users.id')),
     db.Column('accept_req',db.Integer, db.ForeignKey('users.id'))
) 

RoomMembers= db.Table('RoomMembers',
    db.Column('users_id',db.Integer, db.ForeignKey('users.id')),
    db.Column('room_id',db.Integer, db.ForeignKey('room.id'))
)

class users(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(60), nullable = False, unique = True)
    password = db.Column(db.String(255), nullable=False)
    datecreated = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post',backref='users', lazy = True)
    liked_posts = db.relationship("PostLike", foreign_keys='PostLike.user_id', backref="user",lazy="dynamic")
    disliked_posts = db.relationship("PostDislike", foreign_keys='PostDislike.user_id', backref="user",lazy="dynamic")
    liked_comments = db.relationship("CommentLike", foreign_keys='CommentLike.user_id', backref="user",lazy="dynamic")
    disliked_comments = db.relationship("CommentDislike", foreign_keys='CommentDislike.user_id', backref="user",lazy="dynamic")
    friended = db.relationship('users', secondary=Friends,
                                primaryjoin=(Friends.c.sent_req == id), 
                                secondaryjoin=(Friends.c.accept_req == id), 
                                backref=db.backref('Friends', lazy='dynamic'),
                                lazy='dynamic')
    roommember = db.relationship('Room', secondary = RoomMembers, backref = db.backref('members', lazy = 'dynamic'))


    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

    @property
    def is_authenticated(self):
        return True

    def friend(self, user):
        if not self.is_friending(user):
            self.friended.append(user)
            return self

    def unfriend(self, user):
        if self.is_friending(user):
            self.friended.remove(user)
            return self

    def is_friending(self, user):
        return self.friended.filter(Friends.c.accept_req == user.id).count() > 0

    def followed_posts(self):
        return Post.query.join(Friends, (Friends.c.accept_req == Post.user_id)).filter(Friends.c.sent_req == self.id).order_by(Post.create_date.desc())

    def like_post(self, post):
        if not self.has_liked_post(post):
            like = PostLike(user_id = self.id, post_id=post.id)
            db.session.add(like)

    def unlike_post(self, post):
        if self.has_liked_post(post):
            PostLike.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()

    def has_liked_post(self, post):
        return PostLike.query.filter(
            PostLike.user_id == self.id,
            PostLike.post_id == post.id).count()>0

    def dislike_post(self, post):
        if not self.has_disliked_post(post):
            dislike = PostDislike(user_id = self.id, post_id=post.id)
            db.session.add(dislike)

    def undislike_post(self, post):
        if self.has_disliked_post(post):
            PostDislike.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()

    def has_disliked_post(self, post):
        return PostDislike.query.filter(
            PostDislike.user_id == self.id,
            PostDislike.post_id == post.id).count()>0

    def like_comment(self, comment):
        if not self.has_liked_comment(comment):
            like = CommentLike(user_id = self.id, comment_id=comment.id)
            db.session.add(like)

    def unlike_comment(self, comment):
        if self.has_liked_comment(comment):
            CommentLike.query.filter_by(
                user_id=self.id,
                comment_id=comment.id).delete()

    def has_liked_comment(self, comment):
        return CommentLike.query.filter(
            CommentLike.user_id == self.id,
            CommentLike.comment_id == comment.id).count()>0

    def dislike_comment(self, comment):
        if not self.has_disliked_comment(comment):
            dislike = CommentDislike(user_id = self.id, comment_id=comment.id)
            db.session.add(dislike)

    def undislike_comment(self, comment):
        if self.has_disliked_comment(comment):
            CommentDislike.query.filter_by(
                user_id=self.id,
                comment_id=comment.id).delete()

    def has_disliked_comment(self, comment):
        return CommentDislike.query.filter(
            CommentDislike.user_id == self.id,
            CommentDislike.comment_id == comment.id).count()>0


@logins.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

@app.before_request
def before_request():
    if current_user.is_authenticated:
        g.user = current_user
    


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False, unique=True)
    body = db.Column(db.Text, nullable= False)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    post_author = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    comments = db.relationship('Comment', backref = 'Post', lazy = True )
    likes = db.relationship('PostLike', backref='post', lazy = 'dynamic')
    dislikes = db.relationship('PostDislike', backref='post', lazy = 'dynamic')

    def __init__(self, title, body, post_author, user_id):
        self.title = title
        self.body = body
        self.post_author = post_author
        self.user_id = user_id

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<Post %r>' % self.id 


class Comment(db.Model):
   id = db.Column(db.Integer, primary_key = True)
   text = db.Column(db.String(140))
   timestamp = db.Column(db.DateTime(), default=datetime.utcnow, index=True)
   comment_author = db.Column(db.String(30))
   post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
   user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
   likes = db.relationship('CommentLike', backref='comment', lazy = 'dynamic')
   dislikes = db.relationship('CommentDislike', backref='comment', lazy = 'dynamic')   

   def __init__(self, text, comment_author, user_id, post_id):
       self.text = text
       self.comment_author = comment_author
       self.user_id = user_id
       self.post_id = post_id

   def __repr__(self):
      return '<Comment %r>' % self.id


class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<PostLike %r>' % self.id

class PostDislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<PostDislike %r>' % self.id

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<CommentLike %r>' % self.id

class CommentDislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<CommentDislike %r>' % self.id

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique = True)


db.create_all()


Articles = Articles()
@app.route('/', methods = ['GET','POST'])
def index():
    if "user" in session:
        posts = g.user.followed_posts().all()
    else:
        posts = Post.query.order_by(Post.create_date).all()
    return render_template('index.html', articles = Articles, login = login(), posts = posts)


@app.route('/signup', methods =['GET', 'POST'])
def signup():
    if request.method == 'POST':
        session.permanent = True
        _username = request.form['username']
        _email = request.form['email']
        _password = request.form['password']
        _confirm_password = request.form['confirm-password']
        
        if len(_password) < 8:
            flash("Make sure your password is at least 8 letters")
            return redirect('/signup')
        elif re.search('[0-9]',_password) is None:
            flash("Make sure your password has a number in it")
            return redirect('/signup')
        elif re.search('[A-Z]',_password) is None: 
            flash("Make sure your password has a capital letter in it")
            return redirect('/signup')
        else:
            print("Your password seems fine")

        if _password != _confirm_password:
            flash("Passwords do not match")
            return redirect('/signup')
        else:
            session["_password"] = _password
            session["_username"] = _username
            session["_email"] = _email


            hashed_pass = bcrypt.generate_password_hash(_password).decode('utf-8')

            found_user = users.query.filter_by(username=_username,email=_email).first()
            if found_user :
                flash("you already have an account")
                return render_template('login/login.html')

            else:
                newuser= users(_username, _email, hashed_pass)
                db.session.add(newuser)
                db.session.commit()
                user = users.query.filter_by(username=_username,email=_email).first()
                db.session.add(user.friend(user))
                db.session.commit()
                return redirect('/login')

            return redirect('/')
    else:    
        return render_template('registration/reg.html') 


@app.route('/login', methods =["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True 
        user = request.form["username"]
        password1 = request.form["password"]
        session['user'] = user
        session['password1'] = password1

        salted_password1 = salt_password(password1)

        found_user = users.query.filter_by(username=user).first()

        if found_user:
            if bcrypt.check_password_hash(found_user.password, password1):
                login_user(found_user)
                return redirect('/')
            else:
                flash(f"incorrect password")
                return redirect('/login')
        else:
            flash(f"incorrect username")
            return redirect('/login')

    return render_template('login/login.html')


@app.route("/user", methods = ["POST","GET"])
@login_required
def userpage():
    email = g.user.username
    user_name = g.user.email
    if "user" in session: 
        user = session["user"]

        if request.method == "POST":
            email = request.form["email"]
            session["email"] = email
            user_name = request.form['username']
            session['username'] = user_name
            found_user = users.query.filter_by(username=user).first()
            found_user.email = email
            found_user.username = user_name 
            db.session.commit()
            flash("Email was saved")
        elif "email" in session:
            email = session["email"]
            user_name = session["username"]


        return render_template('user/user.html', email = email,username = user_name, user = user)
    else:
        flash("You are not logged in")
        return redirect(url_for("login"))


@app.route("/profile/<username>")
@login_required
def profile(username):
    found_user = users.query.filter_by(username=username).first()
    if not found_user:
        flash("no user found")
        return redirect('/')
    return render_template('user/profiles.html', user = found_user)
    
    
@app.route("/logout")
def logout():
    flash(f"Successfully logged out ", "info")
    logout_user()
    session.pop("user", None) 
    session.pop("email",None)
    return redirect(url_for("login"))


@app.route("/database")
def database():
    return render_template("user/database.html", values=users.query.all()) 


@app.route('/friend/<username>')
@login_required
def friend(username):
    finding_user = users.query.filter_by(username=username).first()
    if finding_user is None:
        flash('User not found.')
        return redirect('/')
    elif finding_user == g.user:
        flash('You cannot friend yourself!')
        return redirect(url_for('profile', username=finding_user.username))
                
    friending_user = g.user.friend(finding_user)
    if friending_user is None:
        flash('Cannot friend ' + finding_user.username)
        return redirect(url_for('profile', username=finding_user.username))
    db.session.add(friending_user)
    db.session.commit()
    flash('You have friended ' + finding_user.username )
    return redirect(url_for('profile', username=finding_user.username))


@app.route('/unfriend/<username>')
@login_required
def unfriend(username):
    finding_user = users.query.filter_by(username=username).first()
    if finding_user is None:
        flash('User not found.')
        return redirect(url_for('/'))
    elif finding_user == g.user :
        flash('You cannot unfriend yourself!')
        return redirect(url_for('profile', username=username))

    other_user = g.user.unfriend(finding_user)
    if other_user is None:
        flash('Cannot unfriend ' + username)
        return redirect(url_for('profile', username=username))
    db.session.add(other_user)
    db.session.commit()
    flash('You have unfriended ' + username)
    return redirect(url_for('profile', username=username))


@app.route('/createpost', methods = ["POST","GET"])
@login_required
def createpost():
    if request.method == "POST":
        post_body = request.form['body']
        post_title = request.form['title']
        session["post_body"] = post_body
        session["post_title"] = post_title

        if len(post_body) < 1 or len(post_title) < 1:
            flash("Too short!", category = 'error')
            return redirect('/createpost')
        else:    
            newpost = Post(title = post_title,body= post_body, post_author = g.user.username, user_id = g.user.id)

            try:
                db.session.add(newpost)
                db.session.commit()
                flash('Posted!')
                return redirect('/')
            except:
                flash('There was an issue with your post')
                return redirect('/createpost')
    return render_template('user/createpost.html') 


@app.route('/post_like/<int:post_id>/<action>', methods =['POST','GET'] )
@login_required
def post_like(post_id, action):
    _post = Post.query.filter_by(id= post_id).first()

    if action == 'like':
        g.user.like_post(_post)
        db.session.commit()
    if action == 'unlike':
        g.user.unlike_post(_post)
        db.session.commit()
    return redirect('/')

@app.route('/post_dislike/<int:post_id>/<action>')
@login_required
def post_dislike(post_id, action):
    _post = Post.query.filter_by(id = post_id).first()

    if action == 'dislike':
        g.user.dislike_post(_post)
        db.session.commit()
    if action == 'undislike':
        g.user.undislike_post(_post)
        db.session.commit()      
    return redirect('/')

@app.route('/comment_like/<int:post_id>/<int:comment_id>/<action>')
@login_required
def comment_like(comment_id,post_id, action):
    _comment = Comment.query.filter_by(id= comment_id).first()
    _post = Post.query.filter_by(id = int(post_id)).first()

    if action == 'like':
        g.user.like_comment(_comment)
        db.session.commit()
    if action == 'unlike':
        g.user.unlike_comment(_comment)
        db.session.commit()
    return render_template('user/comment.html',post=_post)

@app.route('/comment_dislike/<int:post_id>/<int:comment_id>/<action>')
@login_required
def comment_dislike(comment_id,post_id, action):
    _comment = Comment.query.filter_by(id = comment_id).first()
    _post = Post.query.filter_by(id = int(post_id)).first()

    if action == 'dislike':
        g.user.dislike_comment(_comment)
        db.session.commit()
    if action == 'undislike':
        g.user.undislike_comment(_comment)
        db.session.commit()
    return render_template('user/comment.html',post=_post)      


@app.route('/post_comments/<int:post_id>', methods = ['GET', 'POST'])
@login_required
def post_comments(post_id):
    post = Post.query.get(post_id)
    _post = Post.query.filter_by(id = int(post_id)).first()
    if request.method == "POST":
        user_comment = request.form['comment']
        session['user_comment'] = user_comment

        if len(user_comment) < 1:
            flash("Too short!", category = 'error')
            return render_template('user/comment.html', post = _post)
        else:    
            newcomment = Comment(text = user_comment ,user_id = g.user.id, comment_author = g.user.username, post_id = int(post.id))

            try:
                db.session.add(newcomment)
                db.session.commit()
                flash('Comment Posted')
                return render_template('user/comment.html',post=_post)
            except:
                flash('There was an issue with your comment')
                return render_template('user/comment.html', post = _post)

    return render_template('user/comment.html', post = _post)

@app.route("/message", methods = ['GET', 'POST'])
@login_required
def message():
    if request.method == "POST":
        Create_room = request.form['CreateRoom']
        Add_User = request.form['AddUser']
        CreatingRoom = Room(name = Create_room)
        db.session.add(CreatingRoom)
        db.session.commit()
        Groups = Add_User.split(",")
        print(Groups)
        for name in Groups:
            recipient_user = users.query.filter_by(username=name).first()
            print(recipient_user)
            if not recipient_user:
                flash("no user found")
                return redirect('/message')
            newroom = Room.query.filter_by(name= Create_room).first()
            newroom.members.append(recipient_user)
        newroom.members.append(g.user)
        db.session.commit()

    Your_rooms =[]
    for item in range(len(g.user.roommember)):
        members_of_room =   Room.query.join(RoomMembers).join(users).filter(RoomMembers.c.users_id == g.user.id).all()
        room__id = members_of_room[item].id
        roomy = Room.query.filter_by(id = room__id).first()
        Your_rooms.append(str(roomy.name))
    return render_template('user/messages.html', username = g.user.username, rooms = Your_rooms)

@socketio.on('message')
def message(data):
    print(f"\n\n{data}\n\n")
    send({'msg': data['msg'], 'username':data['username'] }, room= data['room'])

@socketio.on('join')
def join(data):
    join_room(data['room'])
    send({'msg': data['username']+ "is now active"}, room= data['room'])

@socketio.on('leave')
def leave(data):
    leave_room(data['room'])
    send({'msg': data['username']+ "is no longer active"}, room= data['room'])


if __name__ == '__main__':
    socketio.run(debug=True)
    manager.run()