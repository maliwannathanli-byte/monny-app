import streamlit as st
import pandas as pd
import datetime
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import copy  # <--- [สำคัญ!] Import copy สำหรับ deepcopy

# --- [ใหม่! & แก้ไข!] Import และเชื่อมต่อ Database (อ่านจาก Secrets) ---
import database as db

@st.cache_resource
def get_db_connection():
    """
    สร้างและ Cache การเชื่อมต่อฐานข้อมูล
    จะทำงานแค่ครั้งเดียว และครั้งต่อๆ ไปจะดึงจาก Cache
    """
    conn_str = st.secrets["SUPABASE_CONN_STRING"]
    conn = db.create_connection(conn_str)
    return conn

# เรียกใช้ฟังก์ชันที่ Cache ไว้
conn = get_db_connection()

# [แก้ไข!] ตรวจสอบ connection ทันที
if conn is None:
    st.error("ไม่สามารถเชื่อมต่อฐานข้อมูลได้! กรุณาตรวจสอบ 'SUPABASE_CONN_STRING' ใน Secrets")
    st.stop() # หยุดการทำงานทันที
# ------------------------------------


# --- 1. ตั้งค่าหน้าเว็บ (เหมือนเดิม) ---
st.set_page_config(
    page_title="บันทึกรายรับรายจ่าย",
    page_icon="💸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. [ใหม่!] ระบบล็อกอิน (อ่านจาก Secrets - แก้ไข RecursionError) ---

# 1. [สำคัญ!] "แปลงร่าง" st.secrets เป็น dict ธรรมดา
# เราต้องสร้าง dict ใหม่ทั้งหมด (Deep Copy) ด้วยมือ
# เพื่อ "ตัดขาด" จาก st.secrets (ที่ห้ามเขียน)
credentials_plain_dict = {
    "usernames": {
        # วนลูป user ทุกคนใน secrets
        username: {
            # วนลูป key/value (email, name, password) ของ user
            key: value
            for key, value in st.secrets["credentials"]["usernames"][username].items()
        }
        for username in st.secrets["credentials"]["usernames"]
    }
}

# 2. สร้าง "config" ที่เหลือ (cookies) ขึ้นมาเองในโค้ด
config = {
    'cookies': {
        'cookie_name': "monny_tracker_cookie",
        'cookie_key': "abcdef123456",  # (คีย์นี้ไม่สำคัญมาก)
        'cookie_expiry_days': 30
    },
    'credentials': credentials_plain_dict  # (ใส่ dict ธรรมดา)
}

# 3. [แก้!] คัดลอก credentials แบบ "Deep Copy"
# (ตอนนี้มันจะทำงานได้ เพราะ config['credentials'] เป็น dict ธรรมดาแล้ว)
credentials_copy = copy.deepcopy(config['credentials'])

authenticator = stauth.Authenticate(
    credentials_copy,  # <--- ส่ง "สำเนา" ที่แก้ไขได้เข้าไป
    config['cookies']['cookie_name'],
    config['cookies']['cookie_key'],
    config['cookies']['cookie_expiry_days']
)

# [ใหม่!] สร้างหน้าล็อกอิน
authenticator.login('main')

# [แก้!] ดึงค่าจาก st.session_state (API ใหม่ล่าสุด)
name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

# --- 3. [ใหม่!] ตรวจสอบการล็อกอิน ---
if authentication_status is False:
    st.error('Username/password ไม่ถูกต้อง')
elif authentication_status is None:
    st.warning('กรุณาใส่ username และ password')
elif authentication_status:
    # ========= [ แอปของคุณเริ่มต้นตรงนี้! ] =========

    # --- หัวข้อหลัก ---
    st.markdown("<h1 style='text-align: center; color: #8A2BE2;'>💸 บันทึกรายรับรายจ่าย 💸</h1>", unsafe_allow_html=True)

    # --- 4. [แก้!] ส่วนเลือกบัญชี (ดึงจาก DB) ---
    st.header("เลือกบัญชี 📂")

    user_accounts_dict = db.get_user_accounts(conn, username)
    account_names = list(user_accounts_dict.keys())

    if not account_names:
        st.warning("ไม่มีบัญชี กรุณาเพิ่มบัญชีใหม่ใน 'จัดการบัญชี' ด้านล่าง")
        st.session_state.selected_account = None
        current_account_data = None
        CURRENT_THEME_COLOR = "#8A2BE2"
    else:
        if 'selected_account' not in st.session_state or st.session_state.selected_account not in account_names:
            st.session_state.selected_account = account_names[0]

        selected = st.selectbox(
            "เลือกบัญชี:",
            options=account_names,
            index=account_names.index(st.session_state.selected_account),
            label_visibility="collapsed"
        )
        st.session_state.selected_account = selected

        current_account_data = user_accounts_dict[st.session_state.selected_account]
        CURRENT_THEME_COLOR = current_account_data['theme_color']
        CURRENT_ACCOUNT_ID = current_account_data['id']

        # --- 5. ฉีด CSS (เหมือนเดิม) ---
    st.markdown(
        f"""
        <style>
        .main-title {{ color: #8A2BE2; text-align: center; font-size: 2.5em; padding-bottom: 15px; }}
        .title {{ color: {CURRENT_THEME_COLOR}; text-align: center; border-bottom: 3px solid {CURRENT_THEME_COLOR}; padding-bottom: 10px; }}
        .summary-balance {{ color: {CURRENT_THEME_COLOR}; text-align: center; border-top: 2px solid #F3F0F9; padding-top: 15px; }}
        h2, h3 {{ color: {CURRENT_THEME_COLOR}; }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- 6. [แก้!] ส่วนรับข้อมูล (บันทึกลง DB) ---
    if current_account_data:
        with st.form(key="expense_form", clear_on_submit=True):
            st.markdown("**ประเภท:**")
            col1, col2 = st.columns(2)
            with col1:
                item_type = st.radio("ประเภท:", ["รายรับ 🔺", "รายจ่าย 🔻"], horizontal=True,
                                     label_visibility="collapsed")

            item_name = st.text_input("รายการ:", placeholder="เช่น ค่ากาแฟ, เงินเดือน")
            amount_str = st.text_input("จำนวนเงิน (บาท):", placeholder="0.00")
            submit_button = st.form_submit_button(label="บันทึกรายการ")

            if submit_button:
                item_datetime = datetime.datetime.now()
                if not amount_str: st.warning("กรุณากรอกจำนวนเงิน"); st.stop()
                try:
                    amount = float(amount_str)
                except ValueError:
                    st.error("กรุณากรอกจำนวนเงินเป็นตัวเลข"); st.stop()

                if amount <= 0:
                    st.warning("จำนวนเงินต้องมากกว่า 0")
                else:
                    final_amount = -amount if item_type == "รายจ่าย 🔻" else amount
                    db.add_transaction(conn, CURRENT_ACCOUNT_ID, item_datetime, item_name, item_type, final_amount)
                    st.success(f"บันทึก '{item_name}' แล้ว")

    # --- 7. [แก้!] ส่วนแสดงผล (ดึงจาก DB) ---
    if current_account_data:
        st.header(f"ประวัติรายการ ({st.session_state.selected_account}) 📜")

        transactions_list = db.get_transactions(conn, CURRENT_ACCOUNT_ID)

        if not transactions_list:
            st.info("ยังไม่มีรายการ...")
        else:
            df = pd.DataFrame(transactions_list)
            df_display = df.copy()
            df_display["tx_datetime"] = df_display["tx_datetime"].apply(lambda x: x.strftime("%d/%m/%Y %H:%M:%S"))

            df_display = df_display.rename(columns={
                "tx_datetime": "วันที่เวลา",
                "tx_name": "รายการ",
                "tx_type": "ประเภท",
                "amount": "จำนวนเงิน"
            })
            st.dataframe(df_display[["วันที่เวลา", "รายการ", "ประเภท", "จำนวนเงิน"]], use_container_width=True,
                         hide_index=True)

    # --- 8. [แก้!] ส่วนสรุปยอด และ แก้ไข/ลบ (ดึงจาก DB) ---
    if current_account_data:
        st.header(f"สรุปยอด ({st.session_state.selected_account}) 📊")

        if not transactions_list:
            df = pd.DataFrame(columns=["tx_type", "amount"])
        else:
            df = pd.DataFrame(transactions_list)

        df = df.rename(columns={"tx_type": "ประเภท", "amount": "จำนวนเงิน"})

        total_income = df[df["ประเภท"] == "รายรับ 🔺"]["จำนวนเงิน"].sum()
        total_expense = df[df["ประเภท"] == "รายจ่าย 🔻"]["จำนวนเงิน"].sum()

        starting_balance = float(current_account_data['starting_balance'])
        total_balance = starting_balance + total_income + total_expense

        st.metric("ยอดรับ 🔺", f"฿{total_income:,.2f}")
        st.metric("ยอดจ่าย 🔻", f"฿{total_expense:,.2f}")
        st.metric("ยอดเริ่มต้น", f"฿{starting_balance:,.2f}")
        st.markdown(f"<h2 class='summary-balance'>ยอดคงเหลือ (บัญชีนี้): ฿{total_balance:.2f}</h2>",
                    unsafe_allow_html=True)

        if transactions_list:
            st.subheader("แก้ไข / ลบ รายการ ✏️")
            with st.expander("คลิกเพื่อจัดการรายการที่มีอยู่"):

                options = []
                for tx in transactions_list:
                    options.append(
                        f"{tx['id']}: {tx['tx_datetime'].strftime('%d/%m %H:%M')} - {tx['tx_name']} ({float(tx['amount']):.2f} ฿)")

                selected_tx_str = st.selectbox("เลือกรายการที่จะจัดการ:", options)

                if selected_tx_str:
                    selected_id = int(selected_tx_str.split(':')[0])
                    tx_data = next(item for item in transactions_list if item["id"] == selected_id)
                    tx_datetime_obj = tx_data['tx_datetime']

                    st.markdown("---")
                    st.markdown(f"**กำลังแก้ไข:** {tx_data['tx_name']}")

                    with st.form(key=f"edit_form_{selected_id}"):
                        edit_date = st.date_input("วันที่:", value=tx_datetime_obj.date())
                        edit_time = st.time_input("เวลา:", value=tx_datetime_obj.time())
                        type_index = 0 if tx_data['tx_type'] == 'รายรับ 🔺' else 1
                        edit_type = st.radio("ประเภท:", ["รายรับ 🔺", "รายจ่าย 🔻"], index=type_index, horizontal=True)
                        edit_name = st.text_input("รายการ:", value=tx_data['tx_name'])
                        edit_amount_str = st.text_input("จำนวนเงิน:", value=f"{abs(float(tx_data['amount'])):.2f}")

                        save_button = st.form_submit_button("💾 บันทึกการแก้ไข")

                        if save_button:
                            try:
                                amount = float(edit_amount_str)
                            except ValueError:
                                st.error("จำนวนเงินไม่ถูกต้อง"); st.stop()
                            if amount <= 0:
                                st.error("จำนวนเงินต้องมากกว่า 0")
                            else:
                                updated_datetime = datetime.datetime.combine(edit_date, edit_time)
                                updated_amount = amount if edit_type == 'รายรับ 🔺' else -amount
                                db.update_transaction(conn, selected_id, updated_datetime, edit_name, edit_type,
                                                      updated_amount)
                                st.success("แก้ไขรายการเรียบร้อย!")

                    st.markdown("---")
                    st.error(f"ลบรายการนี้: {tx_data['tx_name']}")
                    with st.expander("คลิกเพื่อยืนยันการลบ"):
                        confirm_delete = st.checkbox(f"ยืนยันการลบรายการนี้", key=f"delete_check_{selected_id}")
                        delete_button = st.button("❌ ลบรายการนี้ถาวร", key=f"delete_btn_{selected_id}")

                        if delete_button:
                            if confirm_delete:
                                db.delete_transaction(conn, selected_id)
                                st.success("ลบรายการเรียบร้อย!")
                            else:
                                st.warning("กรุณากดยืนยันก่อนลบ")

    # --- 9. [แก้!] สรุปภาพรวม (ดึงจาก DB) ---
    st.markdown("---")
    st.markdown("<h2 style='color: #8A2BE2;'>✨ สรุปภาพรวมทุกบัญชี</h2>", unsafe_allow_html=True)

    overall_net_worth = 0.0
    all_balances = []

    for account_name, data in user_accounts_dict.items():
        tx_list = db.get_transactions(conn, data['id'])

        if not tx_list:
            df = pd.DataFrame(columns=["tx_type", "amount"])
        else:
            df = pd.DataFrame(tx_list)

        df = df.rename(columns={"tx_type": "ประเภท", "amount": "จำนวนเงิน"})

        inc = df[df["ประเภท"] == "รายรับ 🔺"]["จำนวนเงิน"].sum()
        exp = df[df["ประเภท"] == "รายจ่าย 🔻"]["จำนวนเงิน"].sum()
        account_balance = float(data['starting_balance']) + inc + exp

        all_balances.append({"บัญชี": account_name, "ยอดคงเหลือ": account_balance})
        overall_net_worth += account_balance

    st.dataframe(pd.DataFrame(all_balances), use_container_width=True, hide_index=True)
    st.markdown(
        f"<h2 style='text-align: center; color: #8A2BE2;'>...ยอดรวมสุทธิ (ทุกบัญชี): ฿{overall_net_worth:,.2f}</h2>",
        unsafe_allow_html=True)

    # --- 10. [แก้!] ส่วนจัดการบัญชี (ทำงานกับ DB) ---
    st.markdown("---")
    st.markdown(f"<h2 style='color: {CURRENT_THEME_COLOR};'>จัดการบัญชี ⚙️</h2>", unsafe_allow_html=True)

    st.subheader("เพิ่มบัญชีใหม่")
    with st.form("new_account_form", clear_on_submit=True):
        new_account_name = st.text_input("ชื่อบัญชีใหม่:")
        add_account_button = st.form_submit_button("➕ เพิ่มบัญชี")

        if add_account_button and new_account_name:
            if new_account_name in account_names:
                st.error("มีบัญชีชื่อนี้อยู่แล้ว")
            else:
                db.add_account(conn, username, new_account_name)
                st.success(f"เพิ่มบัญชี '{new_account_name}' แล้ว!")

    if current_account_data:
        st.subheader(f"แก้ไข: {st.session_state.selected_account}")

        current_start_balance = float(current_account_data['starting_balance'])
        start_balance_str = st.text_input(
            f"ยอดเริ่มต้น ({st.session_state.selected_account}):",
            placeholder="0.00",
            value=f"{current_start_balance:.2f}" if current_start_balance != 0.0 else ""
        )
        new_color = st.color_picker(
            "เลือกสีธีมสำหรับบัญชีนี้",
            value=CURRENT_THEME_COLOR,
            key=f"color_{st.session_state.selected_account}"
        )

        if st.button("บันทึกยอดเริ่มต้น/สี"):
            try:
                new_start_balance = float(start_balance_str) if start_balance_str else 0.0
                db.update_account_details(conn, CURRENT_ACCOUNT_ID, new_start_balance, new_color)
                st.success("อัปเดตยอดเริ่มต้น/สี เรียบร้อย")
            except ValueError:
                st.error("กรุณากรอกยอดเริ่มต้นเป็นตัวเลข")

        st.markdown("---")
        with st.form(f"rename_form_{st.session_state.selected_account}", clear_on_submit=True):
            st.markdown("เปลี่ยนชื่อบัญชีนี้")
            new_name = st.text_input("ชื่อบัญชีใหม่:", placeholder=st.session_state.selected_account)
            rename_button = st.form_submit_button("✏️ เปลี่ยนชื่อ")

            if rename_button and new_name:
                if new_name == st.session_state.selected_account:
                    st.warning("นี่คือชื่อเดิมอยู่แล้ว")
                elif new_name in account_names:
                    st.error("มีบัญชีชื่อนี้อยู่แล้ว")
                else:
                    db.rename_account(conn, CURRENT_ACCOUNT_ID, new_name)
                    st.session_state.selected_account = new_name
                    st.success(f"เปลี่ยนชื่อเป็น '{new_name}' เรียบร้อย")

        st.markdown("---")
        st.error(f"โซนอันตราย: ลบบัญชี {st.session_state.selected_account}")
        with st.expander("คลิกเพื่อยืนยันการลบ"):
            confirm_delete = st.checkbox(
                f"ฉันยืนยันที่จะลบบัญชี '{st.session_state.selected_account}' และข้อมูลทั้งหมด")
            delete_button = st.button("❌ ลบบัญชีนี้ถาวร")

            if delete_button:
                if confirm_delete:
                    db.delete_account(conn, CURRENT_ACCOUNT_ID)
                    st.session_state.selected_account = None
                    st.success("ลบบัญชีเรียบร้อยแล้ว")
                else:
                    st.warning("กรุณากดยืนยันก่อนลบ")

    # --- [ใหม่!] ย้ายมาไว้ล่างสุดของส่วน 'จัดการบัญชี' ---
    st.markdown("---")
    st.write(f'ล็อกอินในชื่อ: *{name}* ({username})')
    authenticator.logout('ออกจากระบบ', 'main')
