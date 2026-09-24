import host
from system import store, timefmt, ui

TITLE = "Expense"
ICON = "shopping_prices"
ORDER = 40

CATEGORIES = ["Food", "Travel", "Books", "Hardware", "Other"]
CATEGORY_ICONS = {
    "Food": "food:hamburger",
    "Travel": "travel:veichle_bus_1",
    "Books": "notepad",
    "Hardware": "hardware_computing",
    "Other": "shopping_basket",
}


def amount_of(entry):
    try:
        return float(entry["amount"])
    except ValueError:
        return 0.0


def launch():
    entries = store.load("expense", [])
    listing = ui.List(entries,
                      label=lambda e: e["note"] or e["category"],
                      detail=lambda e: "{:.2f}".format(amount_of(e)),
                      icon=lambda e: CATEGORY_ICONS.get(e["category"], "shopping_basket"),
                      empty="No expenses. MENU: new")

    def save():
        store.save("expense", entries)
        listing.set_items(entries)

    def add():
        def done(values):
            ui.pop()
            if amount_of(values):
                entries.insert(0, values)
                save()
                listing.select(0)

        form = ui.Form([
            ui.Field("Date", timefmt.iso_date(host.localtime())),
            ui.Field("Amount", numeric=True),
            ui.Field("Category", choices=CATEGORIES),
            ui.Field("Note"),
        ], on_submit=done)
        ui.push(ui.Screen("New expense", form, status="Enter: next"))

    def delete():
        if entries:
            ui.confirm("Delete this expense?", lambda: (entries.pop(listing.index), save()))

    return ui.Screen("Expense", listing,
                     status=lambda: "Total {:.2f}".format(sum(amount_of(e) for e in entries)),
                     menu=[("New expense", add), ("Delete", delete)])
