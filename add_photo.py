import sqlite3

conn = sqlite3.connect("travel.db")

with conn:
    conn.execute("""
        UPDATE attractions_photo
        SET url = ?
        WHERE attraction_id = ?
    """, ("https://lh3.googleusercontent.com/gps-cs-s/AB5caB9ZS0wbzl1NmBF4T1qfVz6kaqOJVPAwoX_7Yaiy2hZtQlE9d4384j05-fd2MqHpYjypEW-NZXavDWJy9dFE8oJlaI7iWNRalDoiPbogx1lkZdBoURWrIKEXKanIcbHyGyHWKbt68w=s680-w680-h510", 3))

conn.close()
print("URL для attraction_id=15 успешно обновлён.")
