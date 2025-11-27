from flask import Flask, render_template, request, redirect, url_for, session, flash
import database as db
import config

app = Flask(__name__)
app.config.from_object(config)

@app.route('/')
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        # DB에서 데이터 가져오기
        my_recipes = db.get_my_recipes(user_id)
        my_comments = db.get_my_comments(user_id)
        my_favorites = db.get_my_favorites(user_id)
        
        # HTML에 데이터 전달
        return render_template('index.html', 
                             my_recipes=my_recipes, 
                             my_comments=my_comments, 
                             my_favorites=my_favorites)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        nickname = request.form.get('nickname')
        if db.register_user(user_id, password, nickname):
            flash('회원가입 성공! 로그인해주세요.', 'success')
            return redirect(url_for('login'))
        else:
            flash('회원가입 실패. 이미 존재하는 아이디입니다.', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        user = db.login_user(user_id, password)
        if user:
            session['user_id'] = user['user_id']
            session['nickname'] = user['nickname']
            return redirect(url_for('index'))
        else:
            flash('아이디 또는 비밀번호가 일치하지 않습니다.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
    