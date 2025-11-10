import psycopg2
import psycopg2.extras # <-- Import เพิ่ม
import datetime

# --- 1. การตั้งค่าพื้นฐาน (ใหม่!) ---

def create_connection(conn_string):
    """
    สร้างการเชื่อมต่อฐานข้อมูลไปยัง PostgreSQL (Supabase)
    รับ 'conn_string' (ที่อยู่) ที่เราคัดลอกมา
    """
    conn = None
    try:
        conn = psycopg2.connect(conn_string)
        # ตั้งค่าให้ commit อัตโนมัติ (ง่ายขึ้น)
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        print("Error connecting to database:", e)
    return conn

# (เราลบ create_tables() ทิ้ง เพราะเราสร้างบน Supabase แล้ว)

# --- 2. ฟังก์ชันเกี่ยวกับ Accounts (แก้ placeholder) ---

def get_user_accounts(conn, username):
    """ดึงบัญชีทั้งหมดของผู้ใช้ (username)"""
    # (ใช้ RealDictCursor เพื่อให้ผลลัพธ์เป็น dict)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # (เปลี่ยน ? เป็น %s)
        cur.execute("SELECT * FROM accounts WHERE owner_user = %s", (username,))
        rows = cur.fetchall()
        # แปลงเป็น dict {ชื่อบัญชี: ข้อมูล} เหมือนเดิม
        accounts = {row['account_name']: dict(row) for row in rows}
        return accounts

def add_account(conn, username, account_name, theme_color="#8A2BE2"):
    """เพิ่มบัญชีใหม่"""
    sql = '''INSERT INTO accounts(owner_user, account_name, theme_color)
             VALUES(%s, %s, %s)'''
    with conn.cursor() as cur:
        cur.execute(sql, (username, account_name, theme_color))
        # (ไม่ต้อง .commit() เพราะเราตั้ง autocommit=True)

def update_account_details(conn, account_id, balance, color):
    """อัปเดต ยอดเริ่มต้น และ สีธีม"""
    sql = '''UPDATE accounts
             SET starting_balance = %s, theme_color = %s
             WHERE id = %s'''
    with conn.cursor() as cur:
        cur.execute(sql, (balance, color, account_id))

def rename_account(conn, account_id, new_name):
    """เปลี่ยนชื่อบัญชี"""
    sql = '''UPDATE accounts SET account_name = %s WHERE id = %s'''
    with conn.cursor() as cur:
        cur.execute(sql, (new_name, account_id))

def delete_account(conn, account_id):
    """ลบบัญชี"""
    sql = 'DELETE FROM accounts WHERE id = %s'
    with conn.cursor() as cur:
        cur.execute(sql, (account_id,))

# --- 3. ฟังก์ชันเกี่ยวกับ Transactions (แก้ placeholder) ---

def get_transactions(conn, account_id):
    """ดึงรายการทั้งหมดของบัญชี (เรียงใหม่สุดอยู่บน)"""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM transactions WHERE account_id = %s ORDER BY tx_datetime DESC", (account_id,))
        rows = cur.fetchall()
        # แปลง datetime.date เป็น string ที่เข้ากันได้ (ถ้าจำเป็น)
        # แต่ psycopg2 มักจะคืนค่า datetime object ที่ถูกต้องอยู่แล้ว
        return [dict(row) for row in rows]

def add_transaction(conn, account_id, dt, name, tx_type, amount):
    """เพิ่มรายการใหม่"""
    sql = '''INSERT INTO transactions(account_id, tx_datetime, tx_name, tx_type, amount)
             VALUES(%s, %s, %s, %s, %s)'''
    with conn.cursor() as cur:
        cur.execute(sql, (account_id, dt, name, tx_type, amount))

def update_transaction(conn, tx_id, dt, name, tx_type, amount):
    """อัปเดต/แก้ไข รายการ"""
    sql = '''UPDATE transactions
             SET tx_datetime = %s, tx_name = %s, tx_type = %s, amount = %s
             WHERE id = %s'''
    with conn.cursor() as cur:
        cur.execute(sql, (dt, name, tx_type, amount, tx_id))

def delete_transaction(conn, tx_id):
    """ลบรายการ"""
    sql = 'DELETE FROM transactions WHERE id = %s'
    with conn.cursor() as cur:
        cur.execute(sql, (tx_id,))