# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import matplotlib.pyplot as plt

# --------------------------------------------------------------------
#   ✅ Load Supabase keys from Streamlit Secrets (Cloud Deployment)
# --------------------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# --------------------------------------------------------------------
#   ❗ No dotenv, no os.getenv(), no duplication
# --------------------------------------------------------------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------------------------------------
#   Validate keys
# --------------------------------------------------------------------
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase keys missing.")
    st.stop()

# --------------------------------------------------------------------
#   Your actual app code continues below this...
# --------------------------------------------------------------------
st.title("Expense Tracker App")

# ... your expense tracker UI and functions ...


# ---------- Helpers ----------

def signup(email: str, password: str):
    return supabase.auth.sign_up({"email": email, "password": password})

def signin(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def signout():
    supabase.auth.sign_out()
    st.session_state.clear()

def fetch_expenses_for_user(user_id: str):
    resp = supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    return resp.data if resp.data else []

def fetch_all_expenses():
    resp = supabase.table("expenses").select("*").order("date", desc=True).execute()
    return resp.data if resp.data else []

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
    resp = supabase.table("admins").select("user_id").eq("user_id", user_id).execute()
    return len(resp.data) > 0   # Correct check for new SDK

# ---------- UI ----------

st.set_page_config(page_title="Expense Tracker", layout="centered")
st.title("Expense Tracker — Supabase (Multi-user)")

if "user" not in st.session_state:
    st.session_state["user"] = None

# ---------- LOGIN UI ----------
if not st.session_state["user"]:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Login")
        email_l = st.text_input("Email")
        pwd_l = st.text_input("Password", type="password")

        if st.button("Login"):
            res = signin(email_l, pwd_l)
            if hasattr(res, "user") and res.user:
                st.session_state["user"] = res.user
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Login failed")

    with c2:
        st.subheader("Sign Up")
        email_s = st.text_input("New Email")
        pwd_s = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            res = signup(email_s, pwd_s)
            if hasattr(res, "user") and res.user:
                st.success("Signup successful – Now login")
            else:
                st.error("Signup failed")

    st.stop()

# ---------- MAIN APP ----------
user = st.session_state["user"]
user_id = user.id

col1, col2 = st.columns([3, 1])
with col2:
    st.write(f"Signed in as: {user.email}")
    if st.button("Logout"):
        signout()
        st.rerun()

is_admin_user = is_admin(user_id)

if is_admin_user:
    st.success("Admin Access Granted")

# Sidebar menu
page = st.sidebar.radio(
    "Menu", 
    ["Dashboard", "Add Expense", "View & Filter", "Edit / Delete"] +
    (["Admin Panel"] if is_admin_user else [])
)

# ------------------- Dashboard -------------------
if page == "Dashboard":
    st.header("Dashboard")
    data = fetch_all_expenses() if is_admin_user else fetch_expenses_for_user(user_id)

    if not data:
        st.info("No expenses found.")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        st.metric("Total Entries", len(df))
        st.metric("Total Spent", f"₹{df['amount'].sum():.2f}")

        try:
            df_monthly = df.set_index("date").resample("M")["amount"].sum()
            st.line_chart(df_monthly.tail(12))
        except:
            pass

        st.dataframe(df)

# ------------------- Add Expense -------------------
elif page == "Add Expense":
    st.header("Add Expense")
    with st.form("add"):
        amount = st.number_input("Amount", min_value=0.0)
        category = st.text_input("Category")
        date = st.date_input("Date")
        note = st.text_area("Note")
        submit = st.form_submit_button("Add Expense")

    if submit:
        insert_expense(user_id, amount, category, str(date), note)
        st.success("Added")
        st.rerun()

# ------------------- View Filter -------------------
elif page == "View & Filter":
    st.header("View & Filter")
    data = fetch_all_expenses() if is_admin_user else fetch_expenses_for_user(user_id)

    if not data:
        st.info("No data")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        cat = st.selectbox("Category", ["All"] + list(df["category"].unique()))
        start = st.date_input("Start", df["date"].min())
        end = st.date_input("End", df["date"].max())

        f = df
        if cat != "All":
            f = f[f["category"] == cat]
        f = f[(f["date"].dt.date >= start) & (f["date"].dt.date <= end)]

        st.dataframe(f)

# ------------------- Edit/Delete -------------------
elif page == "Edit / Delete":
    st.header("Edit / Delete")
    data = fetch_all_expenses() if is_admin_user else fetch_expenses_for_user(user_id)

    if not data:
        st.info("No records")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        rid = st.selectbox("Select ID", df["id"])
        row = df[df["id"] == rid].iloc[0]

        with st.form("edit"):
            amount = st.number_input("Amount", value=float(row["amount"]))
            category = st.text_input("Category", value=row["category"])
            date = st.date_input("Date", row["date"].date())
            note = st.text_input("Note", value=row["note"])

            if st.form_submit_button("Save"):
                update_expense(rid, amount, category, str(date), note)
                st.success("Updated")
                st.rerun()

            if st.form_submit_button("Delete"):
                delete_expense(rid)
                st.success("Deleted")
                st.rerun()

# ------------------- Admin Panel -------------------
elif page == "Admin Panel":
    st.header("Admin — All Expenses")
    data = fetch_all_expenses()
    st.dataframe(data)

