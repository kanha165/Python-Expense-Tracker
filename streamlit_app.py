# streamlit_app_supabase.py
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

# Load .env if present (local dev)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("SUPABASE_URL or SUPABASE_ANON_KEY not set. Set them in environment/secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- Helpers ----------
def signup(email: str, password: str):
    res = supabase.auth.sign_up({"email": email, "password": password})
    return res

def signin(email: str, password: str):
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return res

def signout():
    supabase.auth.sign_out()
    st.session_state.pop("user", None)
    st.session_state.pop("token", None)

def get_current_user():
    # supabase.auth.get_user() returns current user if session exists
    try:
        data = supabase.auth.get_user()
        return data.user if data and hasattr(data, "user") else None
    except Exception:
        return None

def fetch_expenses_for_user(user_id: str):
    # If user is admin (in admins table), we will fetch all on frontend (admin UID permitted by RLS)
    resp = supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    if resp.error:
        return []
    return resp.data

def fetch_all_expenses():
    resp = supabase.table("expenses").select("*").order("date", desc=True).execute()
    if resp.error:
        return []
    return resp.data

def insert_expense(user_id, amount, category, date, note):
    payload = {
        "user_id": user_id,
        "amount": float(amount),
        "category": category,
        "date": date,
        "note": note
    }
    resp = supabase.table("expenses").insert(payload).execute()
    return resp

def update_expense(row_id, user_id, amount, category, date, note):
    payload = {
        "amount": float(amount),
        "category": category,
        "date": date,
        "note": note
    }
    resp = supabase.table("expenses").update(payload).eq("id", row_id).execute()
    return resp

def delete_expense(row_id):
    resp = supabase.table("expenses").delete().eq("id", row_id).execute()
    return resp

def is_admin(user_id):
    # checks admins table
    resp = supabase.table("admins").select("user_id").eq("user_id", user_id).execute()
    if resp.error:
        return False
    return len(resp.data) > 0

# ---------- UI & Flow ----------
st.set_page_config(page_title="Expense Tracker (Supabase)", layout="centered")
st.title("Expense Tracker — Supabase (Multi-user)")

# session
if "user" not in st.session_state:
    st.session_state["user"] = None

# Auth area
if not st.session_state["user"]:
    # Show auth forms: Sign In / Sign Up
    cols = st.columns(2)
    with cols[0]:
        st.subheader("Login")
        email_l = st.text_input("Email (login)", key="login_email")
        pwd_l = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Login"):
            res = signin(email_l, pwd_l)
            if res and res.user:
                st.success("Login successful")
                st.session_state["user"] = res.user
                st.experimental_rerun()
            else:
                # supabase returns session or error; check
                if hasattr(res, "error") and res.error:
                    st.error(res.error.message if res.error.message else "Login failed")
                else:
                    st.error("Login failed")
    with cols[1]:
        st.subheader("Sign up")
        email_s = st.text_input("Email (signup)", key="signup_email")
        pwd_s = st.text_input("Password (signup)", type="password", key="signup_pwd")
        if st.button("Sign up"):
            res = signup(email_s, pwd_s)
            # sign_up may return user + confirmation info or error
            if hasattr(res, "error") and res.error:
                st.error(res.error.message if res.error.message else "Signup failed")
            else:
                st.success("Signup successful — check email for confirmation if required")
                # do not auto-login; user may confirm email depending on Supabase settings

    st.markdown("---")
    st.info("Use the Sign Up form to create a new account. Then login using the Login form.")
    st.stop()

# If logged in:
user = st.session_state["user"]
user_id = user["id"] if isinstance(user, dict) else getattr(user, "id", None)

# Show main app
col1, col2 = st.columns([3,1])
with col2:
    st.write(f"Signed in as: {user['email'] if isinstance(user, dict) else user.email}")
    if st.button("Logout"):
        signout()
        st.experimental_rerun()

is_admin_user = is_admin(user_id)

if is_admin_user:
    st.success("You are an ADMIN — you can view & manage all users' expenses")

# Tabs / navigation
page = st.sidebar.radio("Menu", ["Dashboard", "Add Expense", "View & Filter", "Edit / Delete", "Admin Panel" if is_admin_user else None], index=0)

# Dashboard
if page == "Dashboard":
    st.header("Dashboard")
    if is_admin_user:
        data = fetch_all_expenses()
    else:
        data = fetch_expenses_for_user(user_id)

    if not data:
        st.info("No expenses found.")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        st.metric("Total entries", len(df))
        st.metric("Total spending", f"₹{df['amount'].sum():.2f}")
        # monthly
        try:
            df_monthly = df.set_index("date").resample("M")["amount"].sum()
            st.line_chart(df_monthly.tail(12))
        except Exception:
            pass
        st.dataframe(df, use_container_width=True)

# Add Expense
elif page == "Add Expense":
    st.header("Add Expense")
    with st.form("add_form"):
        amt = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
        cat = st.text_input("Category", value="Food")
        date = st.date_input("Date", value=datetime.today())
        note = st.text_area("Note (optional)")
        submitted = st.form_submit_button("Add")

    if submitted:
        resp = insert_expense(user_id, amt, cat, date.isoformat(), note)
        if resp.error:
            st.error("Failed to add expense: " + str(resp.error))
        else:
            st.success("Expense added")
            st.experimental_rerun()

# View & Filter
elif page == "View & Filter":
    st.header("View & Filter")
    if is_admin_user:
        data = fetch_all_expenses()
    else:
        data = fetch_expenses_for_user(user_id)

    if not data:
        st.info("No records")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
        sel_cat = st.selectbox("Category", cats)
        start = st.date_input("Start", value=df["date"].min().date())
        end = st.date_input("End", value=df["date"].max().date())
        filtered = df
        if sel_cat != "All":
            filtered = filtered[filtered["category"] == sel_cat]
        filtered = filtered[(filtered["date"].dt.date >= start) & (filtered["date"].dt.date <= end)]
        st.dataframe(filtered, use_container_width=True)

# Edit / Delete
elif page == "Edit / Delete":
    st.header("Edit / Delete")
    if is_admin_user:
        data = fetch_all_expenses()
    else:
        data = fetch_expenses_for_user(user_id)
    if not data:
        st.info("No records")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        ids = df["id"].tolist()
        sel = st.selectbox("Select ID to edit/delete", ids)
        row = df[df["id"] == sel].iloc[0]
        with st.form("edit_form"):
            amt = st.number_input("Amount", value=float(row["amount"]))
            cat = st.text_input("Category", value=row["category"])
            date = st.date_input("Date", value=row["date"].date())
            note = st.text_area("Note", value=row["note"])
            if st.form_submit_button("Save changes"):
                r = update_expense(sel, user_id, amt, cat, date.isoformat(), note)
                if r.error:
                    st.error("Update failed: " + str(r.error))
                else:
                    st.success("Updated")
                    st.experimental_rerun()
            if st.form_submit_button("Delete"):
                d = delete_expense(sel)
                if d.error:
                    st.error("Delete failed: " + str(d.error))
                else:
                    st.success("Deleted")
                    st.experimental_rerun()

# Admin panel
elif page == "Admin Panel" and is_admin_user:
    st.header("Admin Panel — All users' expenses")
    data = fetch_all_expenses()
    if not data:
        st.info("No records")
    else:
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        st.dataframe(df, use_container_width=True)
        st.markdown("You can delete any record by entering ID below.")
        rid = st.text_input("ID to delete (admin)")
        if st.button("Delete record (admin)"):
            try:
                r = delete_expense(int(rid))
                if r.error:
                    st.error("Delete failed")
                else:
                    st.success("Deleted record")
                    st.experimental_rerun()
            except Exception as e:
                st.error("Enter a valid ID")

