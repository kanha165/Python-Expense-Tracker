# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import matplotlib.pyplot as plt
from typing import Any

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
#   Helpers to normalize SDK responses (works for object or dict)
# --------------------------------------------------------------------
def _resp_data(resp: Any):
    """Return the .data or ['data'] value, or None."""
    if resp is None:
        return None
    if hasattr(resp, "data"):
        return getattr(resp, "data")
    if isinstance(resp, dict):
        return resp.get("data")
    return None

def _resp_user(resp: Any):
    """Return the user object from response, works for different SDK shapes."""
    if resp is None:
        return None
    if hasattr(resp, "user"):
        return getattr(resp, "user")
    if isinstance(resp, dict):
        # some responses nest user inside 'user' or 'data' -> 'user'
        if "user" in resp and resp["user"]:
            return resp["user"]
        d = resp.get("data")
        if isinstance(d, dict) and "user" in d:
            return d["user"]
    return None

def _resp_error(resp: Any):
    """Try to extract error info for debugging messages."""
    if resp is None:
        return None
    if hasattr(resp, "error") and getattr(resp, "error"):
        return getattr(resp, "error")
    if isinstance(resp, dict):
        return resp.get("error")
    return None

# --------------------------------------------------------------------
#   Auth + DB helper functions (Supabase Python v2 style)
# --------------------------------------------------------------------
def signup(email: str, password: str):
    try:
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        user = _resp_user(resp)
        err = _resp_error(resp)
        return {"user": user, "error": err}
    except Exception as e:
        return {"user": None, "error": str(e)}


def signin(email: str, password: str):
    try:
        resp = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        user = _resp_user(resp)
        err = _resp_error(resp)
        return {"user": user, "raw": resp, "error": err}
    except Exception as e:
        return {"user": None, "raw": None, "error": str(e)}


def signout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    # clear streamlit session state
    for k in list(st.session_state.keys()):
        st.session_state.pop(k, None)

def fetch_expenses_for_user(user_id: str):
    resp = supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    return _resp_data(resp) or []

def fetch_all_expenses():
    resp = supabase.table("expenses").select("*").order("date", desc=True).execute()
    return _resp_data(resp) or []

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

def update_expense(row_id, amount, category, date, note):
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
    resp = supabase.table("admins").select("user_id").eq("user_id", user_id).execute()
    data = _resp_data(resp)
    return bool(data and len(data) > 0)

# --------------------------------------------------------------------
#   Streamlit UI
# --------------------------------------------------------------------
st.set_page_config(page_title="Expense Tracker", layout="centered")
st.title("Expense Tracker — Supabase (Multi-user)")

if "user" not in st.session_state:
    st.session_state["user"] = None

# ---------- LOGIN UI ----------
if not st.session_state["user"]:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Login")
        email_l = st.text_input("Email", key="login_email")
        pwd_l = st.text_input("Password", type="password", key="login_pwd")

        if st.button("Login"):
            out = signin(email_l, pwd_l)
            if out.get("error"):
                st.error(f"Login failed: {out.get('error')}")
            else:
                user = out.get("user")
                if user:
                    # store minimal user info in session
                    st.session_state["user"] = user
                    st.success("Login successful")
                    st.rerun()

                else:
                    # debugging: show raw resp briefly
                    st.error("Login failed (no user returned). Check credentials or email confirmation.")
                    # st.write(out.get("raw"))

    with c2:
        st.subheader("Sign Up")
        email_s = st.text_input("New Email", key="signup_email")
        pwd_s = st.text_input("New Password", type="password", key="signup_pwd")

        if st.button("Create Account"):
            out = signup(email_s, pwd_s)
            if out.get("error"):
                st.error(f"Signup failed: {out.get('error')}")
            else:
                if out.get("user"):
                    st.success("Signup successful — please login (or check email for confirmation if required).")
                else:
                    st.info("Signup initiated. Check your email for confirmation link if required.")

    st.stop()

# ---------- MAIN APP ----------
user = st.session_state["user"]
# user could be dict-like or object; try to extract id/email robustly
if isinstance(user, dict):
    user_id = user.get("id") or user.get("user_metadata", {}).get("id")
    user_email = user.get("email")
else:
    user_id = getattr(user, "id", None)
    user_email = getattr(user, "email", None)

if not user_id:
    # fallback: try current user via supabase auth
    try:
        current = supabase.auth.get_user()
        cu = _resp_user(current)
        if cu:
            if isinstance(cu, dict):
                user_id = cu.get("id")
                user_email = cu.get("email")
            else:
                user_id = getattr(cu, "id", None)
                user_email = getattr(cu, "email", None)
            st.session_state["user"] = cu
    except Exception:
        pass

col1, col2 = st.columns([3, 1])
with col2:
    st.write(f"Signed in as: {user_email or 'Unknown'}")
    if st.button("Logout"):
        signout()
        st.experimental_rerun()

is_admin_user = is_admin(user_id) if user_id else False
if is_admin_user:
    st.success("Admin Access Granted")

# Sidebar menu
page_options = ["Dashboard", "Add Expense", "View & Filter", "Edit / Delete"]
if is_admin_user:
    page_options.append("Admin Panel")

page = st.sidebar.radio("Menu", page_options)

# ------------------- Dashboard -------------------
if page == "Dashboard":
    st.header("Dashboard")
    data = fetch_all_expenses() if is_admin_user else fetch_expenses_for_user(user_id)

    if not data:
        st.info("No expenses found.")
    else:
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        st.metric("Total Entries", len(df))
        st.metric("Total Spent", f"₹{df['amount'].sum():.2f}")

        try:
            if "date" in df.columns:
                df_monthly = df.set_index("date").resample("M")["amount"].sum()
                st.line_chart(df_monthly.tail(12))
        except Exception:
            pass

        st.dataframe(df)

# ------------------- Add Expense -------------------
elif page == "Add Expense":
    st.header("Add Expense")
    with st.form("add"):
        amount = st.number_input("Amount", min_value=0.0, format="%f")
        category = st.text_input("Category")
        date = st.date_input("Date", value=datetime.today())
        note = st.text_area("Note")
        submit = st.form_submit_button("Add Expense")

    if submit:
        resp = insert_expense(user_id, amount, category, str(date), note)
        err = _resp_error(resp)
        if err:
            st.error(f"Insert failed: {err}")
        else:
            st.success("Added")
            st.experimental_rerun()

# ------------------- View Filter -------------------
elif page == "View & Filter":
    st.header("View & Filter")
    data = fetch_all_expenses() if is_admin_user else fetch_expenses_for_user(user_id)

    if not data:
        st.info("No data")
    else:
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        categories = ["All"] + list(df["category"].dropna().unique())
        cat = st.selectbox("Category", categories)
        start = st.date_input("Start", df["date"].min().date() if not df["date"].isnull().all() else datetime.today())
        end = st.date_input("End", df["date"].max().date() if not df["date"].isnull().all() else datetime.today())

        f = df.copy()
        if cat != "All":
            f = f[f["category"] == cat]
        if "date" in f.columns:
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
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # ensure ids are unique and present
        if "id" not in df.columns:
            st.error("No ID column found in expenses table.")
        else:
            rid = st.selectbox("Select ID", df["id"])
            row = df[df["id"] == rid].iloc[0]

            with st.form("edit"):
                amount = st.number_input("Amount", value=float(row["amount"]))
                category = st.text_input("Category", value=row["category"])
                date = st.date_input("Date", value=row["date"].date() if not pd.isna(row["date"]) else datetime.today())
                note = st.text_input("Note", value=row.get("note", ""))
                save = st.form_submit_button("Save")
                delete = st.form_submit_button("Delete")

            if save:
                resp = update_expense(rid, amount, category, str(date), note)
                err = _resp_error(resp)
                if err:
                    st.error(f"Update failed: {err}")
                else:
                    st.success("Updated")
                    st.experimental_rerun()

            if delete:
                resp = delete_expense(rid)
                err = _resp_error(resp)
                if err:
                    st.error(f"Delete failed: {err}")
                else:
                    st.success("Deleted")
                    st.experimental_rerun()

# ------------------- Admin Panel -------------------
elif page == "Admin Panel":
    st.header("Admin — All Expenses")
    data = fetch_all_expenses()



    # redeploy trigger

    st.dataframe(pd.DataFrame(data))



