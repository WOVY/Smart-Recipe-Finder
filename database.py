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

        # --- 마이페이지 관련 (My Page DAO) ---

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