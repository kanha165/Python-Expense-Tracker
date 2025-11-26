# streamlit_app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import json

CSV_FILE = "storage.csv"
USERS_FILE = "users.json"  # create this in repo root to add users (username: password)

# ------------------------------- AUTH HELPERS ---------------------------------
def load_users():
    """Load users from users.json if present, else return a default admin user."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # expecting format: {"user1":"pass1", "user2":"pass2"}
                if isinstance(data, dict):
                    return data
        except Exception as e:
            st.error("Error reading users.json, using default admin user.")
    # default fallback
    return {"admin": "admin"}

def check_credentials(username, password, users):
    return username in users and users[username] == password

# ------------------------------- CSV INITIAL SETUP ---------------------------------
def init_csv():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["id", "amount", "category", "date", "note"])
        df.to_csv(CSV_FILE, index=False)

def load_data():
    df = pd.read_csv(CSV_FILE)
    if not df.empty:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def save_data(df):
    df_to_save = df.copy()
    df_to_save["date"] = df_to_save["date"].dt.strftime("%Y-%m-%d")
    df_to_save.to_csv(CSV_FILE, index=False)

def generate_new_id(df):
    return 1 if df.empty else int(df["id"].max()) + 1

# Initialize CSV and users
init_csv()
USERS = load_users()

# ------------------------------- SESSION STATE ---------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

# ------------------------------- AUTH UI ---------------------------------
def show_login():
    st.title("Expense Analyzer — Login")
    st.write("Enter your username and password to continue.")
    with st.form("login_form"):
        uname = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if check_credentials(uname.strip(), pwd, USERS):
                st.session_state.logged_in = True
                st.session_state.username = uname.strip()
                st.session_state.login_error = ""
                st.success("Login successful — welcome, " + st.session_state.username)
            else:
                st.session_state.login_error = "Invalid username or password."

    if st.session_state.login_error:
        st.error(st.session_state.login_error)

    st.markdown("---")
    st.info("To add users, create or edit a file named `users.json` in repository root with JSON like: `{\"alice\":\"pass1\",\"bob\":\"pass2\"}`")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None

# If not logged in, show login screen only
if not st.session_state.logged_in:
    show_login()
    st.stop()

# ------------------------------- STREAMLIT UI (protected) ---------------------------------
st.set_page_config(
    page_title="Expense Analyzer",
    layout="centered"
)

st.sidebar.title(f"Menu — {st.session_state.username}")
if st.sidebar.button("Logout"):
    logout()
    st.experimental_rerun()

st.title("Expense Analyzer (Streamlit)")
st.caption("A clean and centered interface for tracking your expenses")

# Sidebar Menu
st.sidebar.title("Menu")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Add Expense", "View & Filter", "Edit / Delete", "Reports", "Export/Import"]
)

# ------------------------------- DASHBOARD ---------------------------------
if page == "Dashboard":
    st.header("Dashboard Summary")
    df = load_data()

    if df.empty:
        st.info("No expenses yet. Add some from 'Add Expense'.")
    else:
        with st.container():
            total = df["amount"].sum()
            monthly = df.resample("M", on="date")["amount"].sum()
            top_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Spending", f"₹{total:.2f}")
            col2.metric("Total Entries", len(df))
            if not top_cat.empty:
                top_name = top_cat.index[0]
                col3.metric("Top Category", f"{top_name} (₹{top_cat.iloc[0]:.2f})")
            else:
                col3.metric("Top Category", "N/A")

        st.markdown("---")

        st.subheader("Monthly Spending (Past Year)")
        try:
            st.line_chart(monthly.tail(12))
        except Exception:
            st.info("Not enough data to show monthly chart.")

        st.subheader("Category-wise Spending")
        try:
            st.bar_chart(top_cat)
        except Exception:
            st.info("Not enough data to show category chart.")

# ------------------------------- ADD EXPENSE ---------------------------------
elif page == "Add Expense":
    st.header("Add New Expense")

    with st.form("add_expense_form", clear_on_submit=True):
        amount = st.text_input("Amount (₹)", placeholder="Enter amount...")
        category = st.text_input("Category", placeholder="Food, Travel, Bills...")
        date = st.date_input("Date", value=datetime.today())
        note = st.text_area("Note")
        submitted = st.form_submit_button("Add Expense")

    if submitted:
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                st.error("Amount must be greater than 0")
                st.stop()
        except:
            st.error("Invalid amount! Enter a number.")
            st.stop()

        df = load_data()
        new_row = {
            "id": generate_new_id(df),
            "amount": amount_val,
            "category": category.strip(),
            "date": pd.to_datetime(date),
            "note": note.strip()
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("Expense added successfully")

# ------------------------------- VIEW & FILTER ---------------------------------
elif page == "View & Filter":
    st.header("View and Filter Expenses")

    df = load_data()
    if df.empty:
        st.warning("No records found.")
    else:

        with st.expander("Apply Filters", expanded=False):
            cols = st.columns(3)

            with cols[0]:
                categories = ["All"] + sorted(df["category"].unique())
                selected_cat = st.selectbox("Category", categories)

            with cols[1]:
                start_date = st.date_input("Start date", df["date"].min().date())

            with cols[2]:
                end_date = st.date_input("End date", df["date"].max().date())

        filtered = df.copy()

        if selected_cat != "All":
            filtered = filtered[filtered["category"] == selected_cat]

        filtered = filtered[
            (filtered["date"].dt.date >= start_date) &
            (filtered["date"].dt.date <= end_date)
        ]

        st.subheader(f"Showing {len(filtered)} records")
        st.dataframe(filtered, use_container_width=True)

# ------------------------------- EDIT / DELETE ---------------------------------
elif page == "Edit / Delete":
    st.header("Edit or Delete Expense")

    df = load_data()

    if df.empty:
        st.info("No records to edit or delete")
    else:
        st.subheader("Select ID")
        ids = df["id"].tolist()
        selected_id = st.selectbox("Choose ID", [None] + ids)

        if selected_id:
            row = df[df["id"] == selected_id].iloc[0]

            with st.form("edit_form"):
                amt = st.text_input("Amount", value=str(row["amount"]))
                cat = st.text_input("Category", value=row["category"])
                date = st.date_input("Date", value=row["date"].date())
                note = st.text_area("Note", value=row["note"])

                save_btn = st.form_submit_button("Save Changes")

            if save_btn:
                try:
                    df.loc[df["id"] == selected_id, ["amount", "category", "date", "note"]] = [
                        float(amt), cat, pd.to_datetime(date), note
                    ]
                    save_data(df)
                    st.success("Record updated")
                except:
                    st.error("Invalid input!")

        st.markdown("---")
        delete_list = st.multiselect("Select IDs to delete", ids)

        if st.button("Delete Selected"):
            df = df[~df["id"].isin(delete_list)]
            save_data(df)
            st.success("Selected records deleted")

# ------------------------------- REPORTS ---------------------------------
elif page == "Reports":
    st.header("Reports and Charts")
    df = load_data()

    if df.empty:
        st.info("No data available")
    else:
        st.subheader("Category Summary Table")
        cat_summary = df.groupby("category")["amount"].sum()
        st.table(cat_summary)

        st.subheader("Category Pie Chart")
        fig, ax = plt.subplots()
        ax.pie(cat_summary.values, labels=cat_summary.index, autopct="%1.1f%%")
        st.pyplot(fig)

# ------------------------------- EXPORT / IMPORT ---------------------------------
elif page == "Export/Import":
    st.header("Export or Import Data")

    df = load_data()

    col1, col2 = st.columns(2)

    with col1:
        if df.empty:
            st.info("No data to export.")
        else:
            csv = df.to_csv(index=False).encode()
            st.download_button("Download CSV", csv, "expenses.csv")

    with col2:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            try:
                new_df = pd.read_csv(uploaded)
                save_data(new_df)
                st.success("Uploaded and replaced existing data")
            except:
                st.error("Invalid CSV format")
