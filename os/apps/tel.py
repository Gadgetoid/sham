from system import store, ui

TITLE = "Tel"
ICON = "telephone_handset"
ORDER = 10

SAMPLE = [
    {"name": "Ada Lovelace", "phone": "01632 960001", "email": "ada@example.com", "note": "Analytical Engine notes due Thursday."},
    {"name": "Alan Turing", "phone": "01632 960002", "email": "alan@example.com", "note": "Chess by post. His move."},
    {"name": "Grace Hopper", "phone": "01632 960003", "email": "grace@example.com", "note": "Owes me a nanosecond of wire."},
    {"name": "Charles Babbage", "phone": "01632 960004", "email": "charles@example.com", "note": ""},
    {"name": "Dorothy Vaughan", "phone": "01632 960005", "email": "dorothy@example.com", "note": "FORTRAN study group, Tuesdays."},
    {"name": "Edsger Dijkstra", "phone": "01632 960006", "email": "edsger@example.com", "note": "Do not mention goto."},
    {"name": "Hedy Lamarr", "phone": "01632 960007", "email": "hedy@example.com", "note": "Frequency hopping patent chat."},
    {"name": "Margaret Hamilton", "phone": "01632 960008", "email": "margaret@example.com", "note": "Priority displays."},
]


def describe(person):
    lines = [person.get("phone", ""), person.get("email", "")]
    if person.get("note"):
        lines += ["", person["note"]]
    return "\n".join(line for line in lines)


def launch():
    people = store.load("tel") or [dict(person) for person in SAMPLE]
    people.sort(key=lambda person: person["name"].lower())

    detail = ui.TextView()
    listing = ui.List(people, label=lambda person: person["name"], empty="No entries")

    def show(person, index):
        detail.set_text(describe(person) if person else "")

    def save():
        people.sort(key=lambda person: person["name"].lower())
        store.save("tel", people)
        listing.set_items(people)

    def add():
        def done(values):
            ui.pop()
            if values["name"]:
                people.append(values)
                save()
                listing.select(people.index(values))

        form = ui.Form([ui.Field("Name"), ui.Field("Phone", numeric=True), ui.Field("Email"), ui.Field("Note")],
                       on_submit=done)
        ui.push(ui.Screen("New entry", form, status="Enter: next"))

    def delete():
        person = listing.selected
        if person:
            ui.confirm("Delete {}?".format(person["name"]), lambda: (people.remove(person), save()))

    listing.on_change = show
    show(listing.selected, 0)
    return ui.Screen("Tel", ui.Split(listing, detail, ratio=0.42),
                     status=lambda: "{}/{}".format(listing.index + 1 if people else 0, len(people)),
                     menu=[("New entry", add), ("Delete", delete)])
