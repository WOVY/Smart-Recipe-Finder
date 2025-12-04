import oracledb
import config
import re

# oracledb 초기화 (Thin 모드 사용)
try:
    oracledb.init_oracle_client()
except Exception:
    pass

oracledb.defaults.fetch_lobs = False

def get_db_conn():
    """Oracle DB 연결 객체 반환"""
    try:
        conn = oracledb.connect(
            user=config.ORACLE_USER,
            password=config.ORACLE_PASSWORD,
            dsn=config.ORACLE_DSN
        )
        return conn
    except oracledb.Error as e:
        print(f"DB 연결 실패: {e}")
        return None
    
def register_user(user_id, password, nickname):
    conn = get_db_conn()
    if not conn: return False

    cursor = conn.cursor()
    try:
        sql = "INSERT INTO USER_T (user_id, password, nickname) VALUES (:1, :2, :3)"
        cursor.execute(sql, (user_id, password, nickname))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"회원가입 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def login_user(user_id, password):
    conn = get_db_conn()
    if not conn: return None
    
    cursor = conn.cursor()
    try:
        sql = "SELECT nickname FROM USER_T WHERE user_id = :1 AND password = :2"
        cursor.execute(sql, (user_id, password))
        result = cursor.fetchone()
        if result:
            return {'user_id': user_id, 'nickname': result[0]}
        return None
    except oracledb.Error as e:
        print(f"로그인 오류: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def add_ingredient(user_id, name, quantity):
    conn = get_db_conn()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        # 재료 ID 찾기 (없으면 INGREDIENT에 먼저 추가)
        cursor.execute("SELECT ingredient_id FROM INGREDIENT WHERE name = :1", (name,))
        res = cursor.fetchone()
        
        if res:
            ing_id = res[0]
        else:
            # 새 재료 추가 및 ID 반환
            ing_id_var = cursor.var(int)
            cursor.execute("INSERT INTO INGREDIENT (name) VALUES (:1) RETURNING ingredient_id INTO :2", [name, ing_id_var])
            ing_id = ing_id_var.getvalue()[0]
        # 2. 내 냉장고에 존재 여부 확인 후 UPDATE 또는 INSERT
        check_sql = "SELECT 1 FROM USER_INGREDIENT WHERE user_id = :1 AND ingredient_id = :2"
        cursor.execute(check_sql, (user_id, ing_id))
        exists = cursor.fetchone() is not None

        if exists:
            update_sql = "UPDATE USER_INGREDIENT SET quantity = :1 WHERE user_id = :2 AND ingredient_id = :3"
            cursor.execute(update_sql, (quantity, user_id, ing_id))
        else:
            insert_sql = "INSERT INTO USER_INGREDIENT (user_id, ingredient_id, quantity) VALUES (:1, :2, :3)"
            cursor.execute(insert_sql, (user_id, ing_id, quantity))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"재료 추가 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def delete_ingredient(user_id, user_ing_id):
    conn = get_db_conn()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM USER_INGREDIENT WHERE user_ingredient_id = :1 AND user_id = :2", (user_ing_id, user_id))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"재료 삭제 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_user_ingredients(user_id):
    conn = get_db_conn()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        sql = """
            SELECT ui.user_ingredient_id, i.name AS ingredientname, ui.quantity 
            FROM USER_INGREDIENT ui 
            JOIN INGREDIENT i ON ui.ingredient_id = i.ingredient_id 
            WHERE ui.user_id = :1
        """
        cursor.execute(sql, (user_id,))
        
        # 결과를 딕셔너리 리스트로 변환
        if cursor.description:
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    except oracledb.Error as e:
        print(f"냉장고 조회 오류: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_my_recipes(user_id):
    """내가 작성한 레시피 목록"""
    conn = get_db_conn()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        sql = """
            SELECT recipe_id, title, info_calories, created_date 
            FROM RECIPE 
            WHERE author_id = :1 
            ORDER BY created_date DESC
        """
        cursor.execute(sql, (user_id,))
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"내 레시피 조회 오류: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_my_comments(user_id):
    """내가 쓴 댓글과 해당 레시피 제목"""
    conn = get_db_conn()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        sql = """
            SELECT C.content, C.created_date, R.recipe_id, R.title 
            FROM COMMENT_T C
            JOIN RECIPE R ON C.recipe_id = R.recipe_id
            WHERE C.user_id = :1 
            ORDER BY C.created_date DESC
        """
        cursor.execute(sql, (user_id,))
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"내 댓글 조회 오류: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_my_favorites(user_id):
    """내가 즐겨찾기한 레시피 목록"""
    conn = get_db_conn()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        # FAVORITE 테이블이 있다고 가정
        sql = """
            SELECT R.recipe_id, R.title, U.nickname, R.info_calories
            FROM FAVORITE F
            JOIN RECIPE R ON F.recipe_id = R.recipe_id
            JOIN USER_T U ON R.author_id = U.user_id
            WHERE F.user_id = :1
        """
        cursor.execute(sql, (user_id,))
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        # 테이블이 없거나 오류 발생 시 빈 리스트 반환
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# mypage: 사용자 정보 불러오기, 닉네임 수정, 비밀번호 수정, 회원 탈퇴
def get_user_info(user_id):
    conn = get_db_conn()
    if not conn: return None
    
    cursor = conn.cursor()
    try:
        sql = "SELECT user_id, nickname FROM USER_T WHERE user_id = :1"
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()
        if result:
            return {'user_id': result[0], 'nickname': result[1]}
        return None
    except oracledb.Error as e:
        print(f"사용자 정보 조회 오류: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_nickname(user_id, new_nickname):
    conn = get_db_conn()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        sql = "UPDATE USER_T SET nickname = :1 WHERE user_id = :2"
        cursor.execute(sql, (new_nickname, user_id))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"닉네임 수정 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_password(user_id, new_password):
    conn = get_db_conn()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        sql = "UPDATE USER_T SET password = :1 WHERE user_id = :2"
        cursor.execute(sql, (new_password, user_id))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"비밀번호 수정 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def delete_user(user_id):
    conn = get_db_conn()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        # 현재 회원의 정보만 삭제. 연관된 데이터 삭제 (예: 댓글, 레시피 등)는 정책에 따라 추가 필요.
        cursor.execute("DELETE FROM USER_T WHERE user_id = :1", (user_id,))
        conn.commit()
        return True
    except oracledb.Error as e:
        print(f"회원 탈퇴 실패: {e}")
        conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def search_recipes(keyword=None, author=None, recipe_way=None, recipe_type=None,
                   calories_min=None, calories_max=None,
                   carbohydrate_min=None, carbohydrate_max=None,
                   protein_min=None, protein_max=None,
                   fat_min=None, fat_max=None,
                   natrium_min=None, natrium_max=None,
                   include_ingredient=None, exclude_ingredient=None):
    """
    레시피 검색 함수
    
    기본 검색:
    - keyword: 레시피 제목 검색
    - author: 작성자 닉네임 검색
    - recipe_way: 조리 방법 (예: '끓이기', '볶기' 등)
    - recipe_type: 요리 종류 (예: '밥', '국&찌개' 등)
    
    세부 검색 (영양 정보 범위):
    - calories_min, calories_max: 칼로리 범위
    - carbohydrate_min, carbohydrate_max: 탄수화물 범위
    - protein_min, protein_max: 단백질 범위
    - fat_min, fat_max: 지방 범위
    - natrium_min, natrium_max: 나트륨 범위
    
    재료 필터:
    - include_ingredient: 포함해야 할 재료
    - exclude_ingredient: 제외할 재료
    """
    conn = get_db_conn()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        sql = """
            SELECT R.recipe_id, R.title, U.nickname, RW.way_name, RT.type_name, 
                   R.info_calories, R.info_carbohydrate, R.info_protein, 
                   R.info_fat, R.info_natrium
            FROM RECIPE R 
            JOIN USER_T U ON R.author_id = U.user_id 
            JOIN RECIPE_WAY RW ON R.recipe_way_id = RW.recipe_way_id 
            JOIN RECIPE_TYPE RT ON R.recipe_type_id = RT.recipe_type_id
            WHERE 1=1
        """
        params = []
        param_idx = 1
        
        # 기본 검색 조건
        if keyword:
            sql += f" AND R.title LIKE :{param_idx}"
            params.append(f"%{keyword}%")
            param_idx += 1
            
        if author:
            sql += f" AND U.nickname LIKE :{param_idx}"
            params.append(f"%{author}%")
            param_idx += 1
            
        if recipe_way:
            sql += f" AND RW.way_name = :{param_idx}"
            params.append(recipe_way)
            param_idx += 1
            
        if recipe_type:
            sql += f" AND RT.type_name = :{param_idx}"
            params.append(recipe_type)
            param_idx += 1
        
        # 세부 검색 조건 (영양 정보 범위)
        if calories_min is not None:
            sql += f" AND R.info_calories >= :{param_idx}"
            params.append(calories_min)
            param_idx += 1
            
        if calories_max is not None:
            sql += f" AND R.info_calories <= :{param_idx}"
            params.append(calories_max)
            param_idx += 1
            
        if carbohydrate_min is not None:
            sql += f" AND R.info_carbohydrate >= :{param_idx}"
            params.append(carbohydrate_min)
            param_idx += 1
            
        if carbohydrate_max is not None:
            sql += f" AND R.info_carbohydrate <= :{param_idx}"
            params.append(carbohydrate_max)
            param_idx += 1
            
        if protein_min is not None:
            sql += f" AND R.info_protein >= :{param_idx}"
            params.append(protein_min)
            param_idx += 1
            
        if protein_max is not None:
            sql += f" AND R.info_protein <= :{param_idx}"
            params.append(protein_max)
            param_idx += 1
            
        if fat_min is not None:
            sql += f" AND R.info_fat >= :{param_idx}"
            params.append(fat_min)
            param_idx += 1
            
        if fat_max is not None:
            sql += f" AND R.info_fat <= :{param_idx}"
            params.append(fat_max)
            param_idx += 1
            
        if natrium_min is not None:
            sql += f" AND R.info_natrium >= :{param_idx}"
            params.append(natrium_min)
            param_idx += 1
            
        if natrium_max is not None:
            sql += f" AND R.info_natrium <= :{param_idx}"
            params.append(natrium_max)
            param_idx += 1
        
        # 재료 포함 조건
        if include_ingredient:
            sql += f""" AND EXISTS (
                SELECT 1 FROM RECIPE_INGREDIENT RI
                JOIN INGREDIENT I ON RI.ingredient_id = I.ingredient_id
                WHERE RI.recipe_id = R.recipe_id AND I.name = :{param_idx}
            )"""
            params.append(include_ingredient)
            param_idx += 1
        
        # 재료 제외 조건
        if exclude_ingredient:
            sql += f""" AND NOT EXISTS (
                SELECT 1 FROM RECIPE_INGREDIENT RI
                JOIN INGREDIENT I ON RI.ingredient_id = I.ingredient_id
                WHERE RI.recipe_id = R.recipe_id AND I.name = :{param_idx}
            )"""
            params.append(exclude_ingredient)
            param_idx += 1
        
        cursor.execute(sql, params)
        
        if cursor.description:
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    except oracledb.Error as e:
        print(f"레시피 검색 오류: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_recipe_detail(recipe_id):
    conn = get_db_conn()
    if not conn: return None
    
    cursor = conn.cursor()
    data = {}
    try:
        # 기본 정보
        cursor.execute("""
            SELECT R.*, U.nickname, RW.way_name, RT.type_name 
            FROM RECIPE R 
            JOIN USER_T U ON R.author_id = U.user_id 
            JOIN RECIPE_WAY RW ON R.recipe_way_id = RW.recipe_way_id 
            JOIN RECIPE_TYPE RT ON R.recipe_type_id = RT.recipe_type_id 
            WHERE R.recipe_id = :1
        """, (recipe_id,))
        
        row = cursor.fetchone()
        if not row: return None
        
        col_basic = [col[0].lower() for col in cursor.description]
        data['info'] = dict(zip(col_basic, row))

        # 재료
        cursor.execute("""
            SELECT I.name, RI.amount 
            FROM RECIPE_INGREDIENT RI
            JOIN INGREDIENT I ON RI.ingredient_id = I.ingredient_id
            WHERE RI.recipe_id = :1
        """, (recipe_id,))
        
        if cursor.description:
            col_ing = [col[0].lower() for col in cursor.description]
            data['ingredients'] = [dict(zip(col_ing, r)) for r in cursor.fetchall()]
        else:
            data['ingredients'] = []

        # 조리 단계
        cursor.execute("SELECT step_number, instruction FROM COOKING_STEP WHERE recipe_id = :1 ORDER BY step_number", (recipe_id,))
        if cursor.description:
            col_steps = [col[0].lower() for col in cursor.description]
            steps_raw = cursor.fetchall()
            
            cleaned_steps = []
            for r in steps_raw:
                step_dict = dict(zip(col_steps, r))
                step_dict['instruction'] = re.sub(r'^\d+\.\s*', '', step_dict['instruction'])
                cleaned_steps.append(step_dict)
                
            data['steps'] = cleaned_steps
        else:
            data['steps'] = []

        # 댓글
        cursor.execute("""
            SELECT C.comment_id, C.user_id, C.content, C.created_date, U.nickname 
            FROM COMMENT_T C 
            JOIN USER_T U ON C.user_id = U.user_id 
            WHERE C.recipe_id = :1 ORDER BY C.created_date DESC
        """, (recipe_id,))
        if cursor.description:
            col_comments = [col[0].lower() for col in cursor.description]
            data['comments'] = [dict(zip(col_comments, r)) for r in cursor.fetchall()]
        else:
            data['comments'] = []

        return data
    except oracledb.Error as e:
        print(f"레시피 상세 오류: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# TOP 5 조회
def get_top5_favorites():
    conn = get_db_conn()
    if not conn: return []
    cursor = conn.cursor()
    try:
        sql = """
            SELECT * FROM (
                SELECT R.recipe_id, R.title, COUNT(F.user_id) as cnt, RT.type_name
                FROM RECIPE R
                JOIN RECIPE_TYPE RT ON R.recipe_type_id = RT.recipe_type_id
                LEFT JOIN FAVORITE F ON R.recipe_id = F.recipe_id
                GROUP BY R.recipe_id, R.title, RT.type_name
                ORDER BY cnt DESC, R.recipe_id DESC
            ) WHERE ROWNUM <= 5
        """
        cursor.execute(sql)
        if cursor.description:
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    finally:
        cursor.close()
        conn.close()

def get_top5_comments():
    conn = get_db_conn()
    if not conn: return []
    cursor = conn.cursor()
    try:
        sql = """
            SELECT * FROM (
                SELECT R.recipe_id, R.title, COUNT(C.comment_id) as cnt, RT.type_name
                FROM RECIPE R
                JOIN RECIPE_TYPE RT ON R.recipe_type_id = RT.recipe_type_id
                LEFT JOIN COMMENT_T C ON R.recipe_id = C.recipe_id
                GROUP BY R.recipe_id, R.title, RT.type_name
                ORDER BY cnt DESC, R.recipe_id DESC
            ) WHERE ROWNUM <= 5
        """
        cursor.execute(sql)
        if cursor.description:
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    finally:
        cursor.close()
        conn.close()