import sqlite3

connection = sqlite3.connect("felineobs.db")
cursor = connection.cursor()

print("CATS:")

cursor.execute("SELECT * FROM cat")
cats = cursor.fetchall()

for cat in cats:
    print(cat)

print("\nOBSERVATIONS:")

cursor.execute("SELECT * FROM observation")
observations = cursor.fetchall()

for observation in observations:
    print(observation)

connection.close()