from system import store, ui

TITLE = "Memo"
ICON = "notepad"
ORDER = 30


def first_line(memo):
    return memo.split("\n", 1)[0] or "(blank)"


def launch():
    memos = store.load("memo", [])
    listing = ui.List(memos, label=first_line, icon=lambda memo: "notepad", empty="No memos. MENU: new memo")

    def save():
        store.save("memo", memos)
        listing.set_items(memos)

    def edit(memo, index):
        editor = ui.TextEdit(memos[index], placeholder="Type away...")

        def close():
            text = editor.value.rstrip()
            if text:
                memos[index] = text
            else:
                del memos[index]
            save()

        ui.push(ui.Screen("Memo", editor, status=lambda: "{} chars".format(len(editor.value)), on_close=close))

    def new():
        memos.insert(0, "")
        listing.set_items(memos)
        listing.select(0)
        edit(memos[0], 0)

    def delete():
        if memos:
            ui.confirm("Delete this memo?", lambda: (memos.pop(listing.index), save()))

    listing.on_select = edit
    return ui.Screen("Memo", listing, status=lambda: str(len(memos)),
                     menu=[("New memo", new), ("Delete", delete)])
