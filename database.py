import sqlite3

connection = sqlite3.connect("felineobs.db")
connection.execute("PRAGMA foreign_keys = ON")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS cat (
    cat_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS observation (
    observation_id INTEGER PRIMARY KEY,
    cat_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    general_setting TEXT,
    initial_context TEXT,
    raw_observation TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (cat_id) REFERENCES cat(cat_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sequence_item (
    sequence_item_id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL,
    item_order INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    factual_description TEXT,
    FOREIGN KEY (observation_id)
        REFERENCES observation(observation_id)
        ON DELETE CASCADE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS observed_element (
    observed_element_id INTEGER PRIMARY KEY,
    sequence_item_id INTEGER NOT NULL,
    modality TEXT NOT NULL,
    factual_description TEXT NOT NULL,
    target_type TEXT,
    target_description TEXT,
    spatial_context TEXT,
    occurrence TEXT,
    change TEXT,
    FOREIGN KEY (sequence_item_id)
        REFERENCES sequence_item(sequence_item_id)
        ON DELETE CASCADE
)
""")

try:
    cursor.execute("""
        ALTER TABLE observation
        ADD COLUMN structure_completed INTEGER NOT NULL DEFAULT 0
    """)
except sqlite3.OperationalError:
    pass

connection.commit()
connection.close()

print("FelineObs database created successfully!")