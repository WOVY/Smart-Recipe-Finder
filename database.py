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