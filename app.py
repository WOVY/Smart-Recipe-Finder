from flask import Flask, render_template, request, redirect, url_for, session, flash
import database as db
import config

app = Flask(__name__)
app.config.from_object(config)

@app.route('/')
def index():
    if 'user_id' in session:
        favorites = db.get_my_favorites(session['user_id'])
        my_recipes = db.get_my_recipes(session['user_id'])
        my_comments = db.get_my_comments(session['user_id'])
        
        top_favorites = db.get_top5_favorites()
        top_comments = db.get_top5_comments()

        return render_template('index.html',
                               favorites=favorites,
                               my_recipes=my_recipes,
                               my_comments=my_comments,
                               top_favorites=top_favorites,
                               top_comments=top_comments)
    return redirect(url_for('login'))

# 내 즐겨찾기 목록
@app.route('/my/favorites')
def my_favorites():
    if 'user_id' not in session: return redirect(url_for('login'))
    favorites = db.get_my_favorites(session['user_id'])
    return render_template('my_favorites.html', favorites=favorites)

# 내 레시피 목록
@app.route('/my/recipes')
def my_recipes():
    if 'user_id' not in session: return redirect(url_for('login'))
    my_recipes = db.get_my_recipes(session['user_id'])
    return render_template('my_recipes.html', my_recipes=my_recipes)

# 내 댓글 목록
@app.route('/my/comments')
def my_comments():
    if 'user_id' not in session: return redirect(url_for('login'))
    my_comments = db.get_my_comments(session['user_id'])
    return render_template('my_comments.html', my_comments=my_comments)

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

# 레시피 작성
@app.route('/recipe/write', methods=['GET', 'POST'])
def write_recipe():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        way_name = request.form.get('recipe_way')
        type_name = request.form.get('recipe_type')
        
        way_id = db.get_id_by_name('RECIPE_WAY', 'RECIPE_WAY_ID', 'WAY_NAME', way_name)
        type_id = db.get_id_by_name('RECIPE_TYPE', 'RECIPE_TYPE_ID', 'TYPE_NAME', type_name)
        
        # 영양정보
        def get_float(val): return float(val) if val and val.strip() else None
        
        cal = get_float(request.form.get('calories'))
        carbo = get_float(request.form.get('carbohydrate'))
        prot = get_float(request.form.get('protein'))
        fat = get_float(request.form.get('fat'))
        na = get_float(request.form.get('natrium'))
        
        # 재료 목록
        ing_names = request.form.getlist('ing_name[]')
        ing_amounts = request.form.getlist('ing_amount[]')
        ingredients = []
        for n, a in zip(ing_names, ing_amounts):
            if n.strip():
                ingredients.append({'name': n, 'amount': a})
                
        # 조리 단계
        steps = request.form.getlist('step[]')
        steps = [s for s in steps if s.strip()]
        
        if not way_id or not type_id:
            flash('조리 방법 또는 종류를 정확히 선택해주세요.', 'error')
            return redirect(url_for('write_recipe'))

        new_id = db.create_recipe(session['user_id'], title, description, 
                                  type_id, way_id, cal, carbo, prot, fat, na, 
                                  ingredients, steps)
        
        if new_id:
            flash('레시피가 등록되었습니다!', 'success')
            return redirect(url_for('recipe_detail', recipe_id=new_id))
        else:
            flash('레시피 등록 실패', 'error')
            
    return render_template('write_recipe.html')

# 레시피 수정
@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # 기존 레시피 정보 조회 (get_recipe_detail 재사용)
    recipe = db.get_recipe_detail(recipe_id)
    if not recipe:
        flash('레시피를 찾을 수 없습니다.', 'error')
        return redirect(url_for('my_recipes'))
    
    # 작성자 권한 확인
    if recipe['info']['author_id'] != session['user_id']:
        flash('수정 권한이 없습니다.', 'error')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        way_name = request.form.get('recipe_way')
        type_name = request.form.get('recipe_type')
        
        way_id = db.get_id_by_name('RECIPE_WAY', 'RECIPE_WAY_ID', 'WAY_NAME', way_name)
        type_id = db.get_id_by_name('RECIPE_TYPE', 'RECIPE_TYPE_ID', 'TYPE_NAME', type_name)
        
        # 영양정보
        def get_float(val): return float(val) if val and val.strip() else None
        
        cal = get_float(request.form.get('calories'))
        carbo = get_float(request.form.get('carbohydrate'))
        prot = get_float(request.form.get('protein'))
        fat = get_float(request.form.get('fat'))
        na = get_float(request.form.get('natrium'))
        
        # 재료 목록
        ing_names = request.form.getlist('ing_name[]')
        ing_amounts = request.form.getlist('ing_amount[]')
        ingredients = []
        for n, a in zip(ing_names, ing_amounts):
            if n.strip():
                ingredients.append({'name': n, 'amount': a})
                
        # 조리 단계
        steps = request.form.getlist('step[]')
        steps = [s for s in steps if s.strip()]
        
        if not way_id or not type_id:
            flash('조리 방법 또는 종류를 정확히 선택해주세요.', 'error')
            return redirect(url_for('edit_recipe', recipe_id=recipe_id))

        if db.update_recipe(recipe_id, title, description, 
                           type_id, way_id, cal, carbo, prot, fat, na, 
                           ingredients, steps):
            flash('레시피가 수정되었습니다!', 'success')
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))
        else:
            flash('레시피 수정 실패', 'error')
            
    return render_template('edit_recipe.html', recipe=recipe)

# 레시피 삭제
@app.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
def delete_recipe(recipe_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # 레시피 정보 조회
    recipe = db.get_recipe_detail(recipe_id)
    if not recipe:
        flash('레시피를 찾을 수 없습니다.', 'error')
        return redirect(url_for('my_recipes'))
    
    # 작성자 권한 확인
    if recipe['info']['author_id'] != session['user_id']:
        flash('삭제 권한이 없습니다.', 'error')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    
    if db.delete_recipe(recipe_id):
        flash('레시피가 삭제되었습니다.', 'success')
        return redirect(url_for('my_recipes'))
    else:
        flash('레시피 삭제에 실패했습니다.', 'error')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))

# 냉장고 재료 삭제
@app.route('/fridge/delete/<int:id>')
def delete_ingredient(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db.delete_ingredient(session['user_id'], id)
    flash('재료가 삭제되었습니다.', 'success')
    return redirect(url_for('fridge'))

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

@app.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    mode = request.args.get('mode')
    recipes = []
    title = "전체 레시피"
    
    if mode == 'fridge':
        recipes = db.find_recipes_by_fridge(session['user_id'])
        title = "냉장고 파먹기 결과"
    else:
        # 검색 파라미터 수집
        keyword = request.args.get('keyword')
        author = request.args.get('author')
        recipe_way = request.args.get('recipe_way')
        recipe_type = request.args.get('recipe_type')
        
        # 세부 검색 파라미터
        calories_min = request.args.get('calories_min', type=int)
        calories_max = request.args.get('calories_max', type=int)
        carbohydrate_min = request.args.get('carbohydrate_min', type=int)
        carbohydrate_max = request.args.get('carbohydrate_max', type=int)
        protein_min = request.args.get('protein_min', type=int)
        protein_max = request.args.get('protein_max', type=int)
        fat_min = request.args.get('fat_min', type=int)
        fat_max = request.args.get('fat_max', type=int)
        natrium_min = request.args.get('natrium_min', type=int)
        natrium_max = request.args.get('natrium_max', type=int)
        
        # 재료 필터
        include_ingredient = request.args.get('include_ingredient')
        exclude_ingredient = request.args.get('exclude_ingredient')
        
        # 레시피 검색 실행
        recipes = db.search_recipes(
            keyword=keyword,
            author=author,
            recipe_way=recipe_way,
            recipe_type=recipe_type,
            calories_min=calories_min,
            calories_max=calories_max,
            carbohydrate_min=carbohydrate_min,
            carbohydrate_max=carbohydrate_max,
            protein_min=protein_min,
            protein_max=protein_max,
            fat_min=fat_min,
            fat_max=fat_max,
            natrium_min=natrium_min,
            natrium_max=natrium_max,
            include_ingredient=include_ingredient,
            exclude_ingredient=exclude_ingredient
        )
        
        # 검색 조건이 있으면 타이틀 변경
        if any([keyword, author, recipe_way, recipe_type, calories_min, calories_max, 
                carbohydrate_min, carbohydrate_max, protein_min, protein_max, 
                fat_min, fat_max, natrium_min, natrium_max, include_ingredient, exclude_ingredient]):
            title = "검색 결과"
        
    return render_template('search.html', recipes=recipes, title=title)

# 레시피 상세 조회
@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    detail = db.get_recipe_detail(recipe_id)
    if not detail:
        flash('레시피를 찾을 수 없습니다.', 'error')
        return redirect(url_for('index'))
    
    is_favorite = db.is_favorited(recipe_id, session['user_id'])
    return render_template('recipe_detail.html', detail=detail, is_favorite=is_favorite)

# 즐겨찾기 등록 / 해제
@app.route('/recipe/<int:recipe_id>/favorite', methods=['POST'])
def toggle_favorite(recipe_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    action = db.toggle_favorite(recipe_id, session['user_id'])
    
    if action == 'added':
        flash('나의 즐겨찾기에 저장되었습니다.', 'success')
    elif action == 'removed':
        flash('즐겨찾기가 해제되었습니다.', 'info')
    else:
        flash('오류가 발생했습니다.', 'error')
    
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))

# 댓글 작성
@app.route('/recipe/<int:recipe_id>/comment', methods=['POST'])
def add_comment(recipe_id):
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    if content:
        success = db.add_comment(session['user_id'], recipe_id, content)
        if success:
            flash('댓글이 등록되었습니다.', 'success')
        else:
            flash('댓글 등록에 실패했습니다.', 'error')
    
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))

# 댓글 삭제 라우트
@app.route('/recipe/<int:recipe_id>/comment/delete/<int:comment_id>')
def delete_comment(recipe_id, comment_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if db.delete_comment(comment_id, session['user_id']):
        flash('댓글이 삭제되었습니다.', 'success')
    else:
        flash('삭제 권한이 없거나 실패했습니다.', 'error')
        
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))

if __name__ == '__main__':
    app.run(debug=True)
    