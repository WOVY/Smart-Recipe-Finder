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