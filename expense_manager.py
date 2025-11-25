import csv
import os
from datetime import datetime

class ExpenseManager:
    FILE_NAME = "storage.csv"

    def __init__(self):
        if not os.path.exists(self.FILE_NAME):
            with open(self.FILE_NAME, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["id", "amount", "category", "date", "note"])

    def load_expenses(self):
        expenses = []
        with open(self.FILE_NAME, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                expenses.append(row)
        return expenses

    def save_expenses(self, expenses):
        with open(self.FILE_NAME, "w", newline="") as file:
            fieldnames = ["id", "amount", "category", "date", "note"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(expenses)

    def add_expense(self, amount, category, date, note):
        if not self.validate_input(amount, date):
            return False, "Invalid amount or date format!"

        expenses = self.load_expenses()

        new_id = 1 if len(expenses) == 0 else int(expenses[-1]["id"]) + 1

        new_exp = {
            "id": str(new_id),
            "amount": amount,
            "category": category,
            "date": date,
            "note": note
        }

        expenses.append(new_exp)
        self.save_expenses(expenses)
        return True, "Expense added successfully!"

    def list_expenses(self):
        return self.load_expenses()

    def filter_by_category(self, category):
        expenses = self.load_expenses()
        return [exp for exp in expenses if exp["category"].lower() == category.lower()]

    def filter_by_date_range(self, start_date, end_date):
        expenses = self.load_expenses()

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        results = []
        for exp in expenses:
            exp_date = datetime.strptime(exp["date"], "%Y-%m-%d")
            if start <= exp_date <= end:
                results.append(exp)
        return results

    def validate_input(self, amount, date):
        try:
            amt = float(amount)
            if amt <= 0:
                return False
        except:
            return False

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except:
            return False

        return True

    # ========== MONTHLY SUMMARY ADDED ==========
    def monthly_summary(self, month, year):
        expenses = self.load_expenses()
        total = 0
        category_summary = {}

        for exp in expenses:
            exp_date = exp["date"]  # format YYYY-MM-DD
            y, m, d = exp_date.split("-")

            if int(m) == month and int(y) == year:
                amount = float(exp["amount"])
                total += amount

                cat = exp["category"]
                category_summary[cat] = category_summary.get(cat, 0) + amount

        if category_summary:
            top_category = max(category_summary, key=category_summary.get)
        else:
            top_category = "No Data"

        return {
            "total_spending": total,
            "category_summary": category_summary,
            "top_category": top_category
        }
