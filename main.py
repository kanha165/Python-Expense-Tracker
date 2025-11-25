from expense_manager import ExpenseManager
from report_generator import ReportGenerator
from datetime import datetime

manager = ExpenseManager()
reporter = ReportGenerator()

def display_menu():
    print("\n===== Expense Analyzer =====")
    print("1. Add Expense")
    print("2. List All Expenses")
    print("3. Search by Category")
    print("4. Search by Date Range")
    print("5. Monthly Summary Report (ExpenseManager)")
    print("6. Full Report (ReportGenerator)")
    print("7. Exit")
    print("============================")

# ------------ MAIN LOOP ----------------
while True:
    display_menu()
    choice = input("Enter your choice: ")

    # --------- ADD EXPENSE ---------
    if choice == "1":

        while True:
            amount = input("Enter amount: ")
            try:
                amount_value = float(amount)
                if amount_value <= 0:
                    print("Amount must be greater than 0!")
                    continue
                break
            except:
                print("Invalid amount! Please enter a number (Example: 250).")

        category = input("Enter category: ")

        while True:
            date = input("Enter date (YYYY-MM-DD): ")
            try:
                datetime.strptime(date, "%Y-%m-%d")
                break
            except:
                print("Invalid date format! Use YYYY-MM-DD")

        note = input("Enter note: ")

        success, message = manager.add_expense(amount, category, date, note)
        print(message)

    # --------- LIST ALL ---------
    elif choice == "2":
        expenses = manager.list_expenses()
        if len(expenses) == 0:
            print("No expenses found!")
        else:
            print("\nID | Amount | Category | Date | Note")
            print("---------------------------------------")
            for exp in expenses:
                print(f"{exp['id']} | {exp['amount']} | {exp['category']} | {exp['date']} | {exp['note']}")

    # --------- CATEGORY SEARCH ---------
    elif choice == "3":
        category = input("Enter category to search: ")

        results = manager.filter_by_category(category)
        if len(results) == 0:
            print("No results found!")
        else:
            print("\nFiltered by Category:")
            for exp in results:
                print(f"{exp['id']} | {exp['amount']} | {exp['category']} | {exp['date']} | {exp['note']}")

    # --------- DATE RANGE SEARCH ---------
    elif choice == "4":

        while True:
            start = input("Enter start date (YYYY-MM-DD): ")
            try:
                datetime.strptime(start, "%Y-%m-%d")
                break
            except:
                print("Invalid start date!")

        while True:
            end = input("Enter end date (YYYY-MM-DD): ")
            try:
                datetime.strptime(end, "%Y-%m-%d")
                break
            except:
                print("Invalid end date!")

        results = manager.filter_by_date_range(start, end)

        if len(results) == 0:
            print("No expenses found in this range!")
        else:
            print("\nFiltered by Date Range:")
            for exp in results:
                print(f"{exp['id']} | {exp['amount']} | {exp['category']} | {exp['date']} | {exp['note']}")

    # --------- MONTHLY SUMMARY (ExpenseManager) ---------
    elif choice == "5":
        try:
            month = int(input("Enter month (1-12): "))
            year = int(input("Enter year (YYYY): "))
        except:
            print("Invalid month or year!")
            continue

        summary = manager.monthly_summary(month, year)

        print("\n===== Monthly Report =====")
        print(f"Total Spending: {summary['total_spending']}")
        print("\nCategory-wise Spending:")
        if len(summary["category_summary"]) == 0:
            print("No data found for this month!")
        else:
            for cat, amt in summary["category_summary"].items():
                print(f"  {cat}: {amt}")

        print("\nTop Category:", summary["top_category"])

    # --------- FULL REPORT (ReportGenerator) ---------
    elif choice == "6":
        expenses = manager.list_expenses()

        print("\n===== FULL REPORT =====")

        print("\nTotal Expense:", reporter.total_expense(expenses))

        print("\nCategory Summary:")
        category_data = reporter.category_summary(expenses)
        if len(category_data) == 0:
            print("No expenses found!")
        else:
            for c, a in category_data.items():
                print(f"  {c}: {a}")

        top_cat, top_amt = reporter.top_category(expenses)
        print("\nTop Category:", top_cat, "→", top_amt)

    # --------- EXIT ---------
    elif choice == "7":
        print("Goodbye! 👋")
        break

    else:
        print("Invalid choice, try again!")
