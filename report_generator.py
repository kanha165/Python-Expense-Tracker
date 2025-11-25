from datetime import datetime

class ReportGenerator:

    def total_expense(self, expenses):
        return sum(float(exp["amount"]) for exp in expenses)

    def category_summary(self, expenses):
        summary = {}
        for exp in expenses:
            cat = exp["category"]
            amt = float(exp["amount"])
            summary[cat] = summary.get(cat, 0) + amt
        return summary

    def top_category(self, expenses):
        summary = self.category_summary(expenses)
        if not summary:
            return None, 0
        top_cat = max(summary, key=summary.get)
        return top_cat, summary[top_cat]

    def monthly_summary(self, expenses, month, year):
        total = 0
        for exp in expenses:
            exp_date = datetime.strptime(exp["date"], "%Y-%m-%d")
            if exp_date.month == month and exp_date.year == year:
                total += float(exp["amount"])
        return total
