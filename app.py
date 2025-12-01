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

@app.route('/fridge', methods=['GET', 'POST'])
def fridge():
    if 'user_id' not in session: return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        qty = request.form.get('quantity')
        if name:
            if db.add_ingredient(session['user_id'], name, qty):
                flash(f"'{name}' 추가 완료", 'success')
            else:
                flash('재료 추가 실패', 'error')
        return redirect(url_for('fridge'))
    
    ingredients = db.get_user_ingredients(session['user_id'])

    return render_template('fridge.html', ingredients=ingredients)

# mypage: 사용자 정보 불러오기, 닉네임 수정, 비밀번호 수정, 회원 탈퇴
@app.route('/mypage')
def mypage():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    user_info = db.get_user_info(session['user_id'])
    return render_template('mypage.html', user_info=user_info)

@app.route('/mypage/update_nickname', methods=['POST'])
def update_nickname():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    new_nickname = request.form.get('nickname')
    if new_nickname:
        if db.update_nickname(session['user_id'], new_nickname):
            session['nickname'] = new_nickname
            flash('닉네임이 변경되었습니다.', 'success')
        else:
            flash('닉네임 변경에 실패했습니다.', 'error')
    return redirect(url_for('mypage'))

@app.route('/mypage/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 현재 비밀번호 확인
    user = db.login_user(session['user_id'], current_password)
    if not user:
        flash('현재 비밀번호가 일치하지 않습니다.', 'error')
        return redirect(url_for('mypage'))
    
    # 새 비밀번호 확인
    if new_password != confirm_password:
        flash('새 비밀번호가 일치하지 않습니다.', 'error')
        return redirect(url_for('mypage'))
    
    if db.update_password(session['user_id'], new_password):
        flash('비밀번호가 변경되었습니다.', 'success')
    else:
        flash('비밀번호 변경에 실패했습니다.', 'error')
    
    return redirect(url_for('mypage'))

@app.route('/mypage/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    password = request.form.get('password')
    
    # 비밀번호 확인
    user = db.login_user(session['user_id'], password)
    if not user:
        flash('비밀번호가 일치하지 않습니다.', 'error')
        return redirect(url_for('mypage'))
    
    if db.delete_user(session['user_id']):
        session.clear()
        flash('회원 탈퇴가 완료되었습니다.', 'success')
        return redirect(url_for('login'))
    else:
        flash('회원 탈퇴에 실패했습니다.', 'error')
        return redirect(url_for('mypage'))

if __name__ == '__main__':
    app.run(debug=True)
    