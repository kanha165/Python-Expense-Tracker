import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# ------------------ SUPABASE CONNECTION ------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase keys missing in Streamlit Secrets")
    st.stop()

# ------------------ AUTH FUNCTIONS ------------------

def signup(email, password):
    try:
        resp = supabase.auth.sign_up({"email": email, "password": password})
        user = resp.user if hasattr(resp, "user") else None
        return user, None
    except Exception as e:
        return None, str(e)

def signin(email, password):
    try:
        resp = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        user = resp.user if hasattr(resp, "user") else None

        # ✅ ATTACH SESSION TOKEN FOR RLS
        if hasattr(resp, "session") and resp.session:
            supabase.postgrest.auth(resp.session.access_token)

        return user, None
    except Exception as e:
        return None, str(e)

def signout():
    try:
        supabase.auth.sign_out()
    except:
        pass
    st.session_state.clear()
    st.rerun()

# ------------------ DATABASE FUNCTIONS ------------------

def fetch_user_expenses(user_id):
    return supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True).execute().data

def fetch_all_expenses():
    return supabase.table("expenses").select("*").order("date", desc=True).execute().data

def insert_expense(user_id, amount, category, date, note):
    payload = {
        "user_id": user_id,
        "amount": float(amount),
        "category": category,
        "date": date,
        "note": note
    }
    return supabase.table("expenses").insert(payload).execute()

def update_expense(row_id, amount, category, date, note):
    payload = {
        "amount": float(amount),
        "category": category,
        "date": date,
        "note": note
    }
    return supabase.table("expenses").update(payload).eq("id", row_id).execute()

def delete_expense(row_id):
    return supabase.table("expenses").delete().eq("id", row_id).execute()

def is_admin(user_id):
    data = supabase.table("admins").select("user_id").eq("user_id", user_id).execute().data
    return bool(data)

# ------------------ UI ------------------

st.set_page_config(page_title="Expense Tracker", layout="centered")
st.title("Expense Tracker")

# INIT SESSION
if "user" not in st.session_state:
    st.session_state["user"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# ------------------ LOGIN / SIGNUP ------------------
if not st.session_state["user"]:

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Login")
        email_l = st.text_input("Email")
        pwd_l = st.text_input("Password", type="password")

        if st.button("Login"):
            user, err = signin(email_l, pwd_l)
            if err:
                st.error(f"Login failed: {err}")
            elif user:
                st.session_state["user"] = user
                st.session_state["user_id"] = user.id
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with col2:
        st.subheader("Sign Up")
        email_s = st.text_input("New Email")
        pwd_s = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            user, err = signup(email_s, pwd_s)
            if err:
                st.error(f"Signup failed: {err}")
            else:
                st.success("Signup successful! Now login.")

    st.stop()

# ------------------ MAIN APP ------------------

user_id = st.session_state["user_id"]
user_email = st.session_state["user"].email

col1, col2 = st.columns([3, 1])
with col2:
    st.write(f"Signed in as: {user_email}")
    if st.button("Logout"):
        signout()

admin = is_admin(user_id)
if admin:
    st.success("Admin Access Enabled")

menu = ["Dashboard", "Add Expense", "View & Filter", "Edit / Delete"]
if admin:
    menu.append("Admin Panel")

page = st.sidebar.radio("Menu", menu)

# ------------------ DASHBOARD ------------------
if page == "Dashboard":
    data = fetch_all_expenses() if admin else fetch_user_expenses(user_id)

    if not data:
        st.info("No data found")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        st.metric("Total Entries", len(df))
        st.metric("Total Spent", f"₹{df['amount'].sum():.2f}")

        st.dataframe(df)

# ------------------ ADD EXPENSE ------------------
elif page == "Add Expense":
    with st.form("add"):
        amount = st.number_input("Amount", min_value=0.0)
        category = st.text_input("Category")
        date = st.date_input("Date")
        note = st.text_area("Note")
        submit = st.form_submit_button("Add")

    if submit:
        insert_expense(user_id, amount, category, str(date), note)
        st.success("Expense added")
        st.rerun()

# ------------------ VIEW FILTER ------------------
elif page == "View & Filter":
    data = fetch_all_expenses() if admin else fetch_user_expenses(user_id)
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    categories = ["All"] + df["category"].unique().tolist()
    cat = st.selectbox("Category", categories)

    if cat != "All":
        df = df[df["category"] == cat]

    st.dataframe(df)

# ------------------ EDIT / DELETE ------------------
elif page == "Edit / Delete":
    data = fetch_user_expenses(user_id)
    df = pd.DataFrame(data)

    if df.empty:
        st.info("No records")
    else:
        rid = st.selectbox("Select ID", df["id"])
        row = df[df["id"] == rid].iloc[0]

        with st.form("edit"):
            amount = st.number_input("Amount", value=float(row["amount"]))
            category = st.text_input("Category", row["category"])
            date = st.date_input("Date", datetime.fromisoformat(row["date"]).date())
            note = st.text_input("Note", row["note"])
            save = st.form_submit_button("Save")
            delete = st.form_submit_button("Delete")

        if save:
            update_expense(rid, amount, category, str(date), note)
            st.success("Updated")
            st.rerun()

        if delete:
            delete_expense(rid)
            st.success("Deleted")
            st.rerun()

# ------------------ ADMIN PANEL ------------------
elif page == "Admin Panel":
    data = fetch_all_expenses()
    st.dataframe(pd.DataFrame(data))
