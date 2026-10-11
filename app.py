import sqlite3
import streamlit as st
from datetime import datetime

DB = "felineobs.db"

MODALITIES = [
    ("behaviour_action", "Behaviour / action"),
    ("posture_locomotion", "Posture / locomotion"),
    ("ears", "Ears"),
    ("tail_position", "Tail position"),
    ("tail_movement", "Tail movement"),
    ("eyes_orientation", "Eyes / orientation"),
    ("vocalisation", "Vocalisation"),
]

def ensure_v1_schema():
    """Apply small backwards-compatible V1 schema updates."""
    connection = sqlite3.connect(DB)
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(sequence_item)")
    columns = {row[1] for row in cursor.fetchall()}

    if "location" not in columns:
        cursor.execute("""
            ALTER TABLE sequence_item
            ADD COLUMN location TEXT
        """)

    connection.commit()
    connection.close()


ensure_v1_schema()

def ensure_coding_schema():
    """Add scientific coding without replacing or clearing existing observations."""
    with sqlite3.connect(DB) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("""CREATE TABLE IF NOT EXISTS source (
            source_id INTEGER PRIMARY KEY, authors TEXT NOT NULL, year INTEGER NOT NULL,
            title TEXT NOT NULL, source_url TEXT NOT NULL UNIQUE
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS code (
            code_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES source(source_id),
            original_code TEXT, original_name TEXT NOT NULL,
            operational_definition TEXT NOT NULL, applicable_interaction TEXT,
            temporal_type TEXT, source_location TEXT, modality TEXT,
            UNIQUE(source_id, original_name)
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS element_coding (
            element_coding_id INTEGER PRIMARY KEY,
            observed_element_id INTEGER NOT NULL REFERENCES observed_element(observed_element_id) ON DELETE CASCADE,
            code_id INTEGER NOT NULL REFERENCES code(code_id),
            UNIQUE(observed_element_id, code_id)
        )""")
        cols = {r[1] for r in connection.execute("PRAGMA table_info(observed_element)")}
        if "coding_status" not in cols:
            connection.execute("ALTER TABLE observed_element ADD COLUMN coding_status TEXT NOT NULL DEFAULT 'pending_review'")
        if "coding_reason" not in cols:
            connection.execute("ALTER TABLE observed_element ADD COLUMN coding_reason TEXT")
        # Small, explicitly limited starter catalogue. No automated assignment.
        url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC8381768/"
        connection.execute(
            "INSERT OR IGNORE INTO source(authors, year, title, source_url) VALUES (?, ?, ?, ?)",
            ("Haywood et al.", 2021,
             "Providing Humans With Practical, Best Practice Handling Guidelines During Human-Cat Interactions", url)
        )
        source_id = connection.execute("SELECT source_id FROM source WHERE source_url=?", (url,)).fetchone()[0]
        for name, definition in (
            ("Approach person", "Cat moves towards person"),
            ("Rub person", "Cat rubs head, cheek, or side of body against person"),
        ):
            connection.execute("""INSERT OR IGNORE INTO code
                (source_id, original_code, original_name, operational_definition,
                 applicable_interaction, temporal_type, source_location, modality)
                VALUES (?, NULL, ?, ?, 'Cat–human', 'Frequency event',
                        'Table 2 / Supplementary Data 2', 'behaviour_action')""",
                (source_id, name, definition))

ensure_coding_schema()


# -------------------------
# DATABASE HELPERS
# -------------------------

def connect():
    connection = sqlite3.connect(DB)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_extended_scientific_catalogue():
    """Idempotent additions; never remove existing observations or codes."""
    publications = [
        ("Kappel et al.", 2024, "Ethogram of the Domestic Cat",
         "https://doi.org/10.3390/pets1030021", [
            ("SIT", "Sit", "The cat's hindquarters rest fully on the ground; front paws touch the ground and the front legs are extended.", "posture_locomotion", "Table 2, item 1", "State"),
            ("STA", "Stand", "The cat stands on all four paws with its legs loosely extended and its head upright.", "posture_locomotion", "Table 2, item 2", "State"),
            ("WAL", "Walk", "The cat moves with a four-beat walking gait, placing its legs successively while keeping at least two paws on the ground.", "posture_locomotion", "Table 2, item 3", "State"),
        ]),
        ("Van Belle et al.", 2025,
         "Development of the Ethogram of Feline Social Interactions (EFSI) to study intraspecific interactions between cats in multicat households",
         "https://doi.org/10.1016/j.applanim.2025.106862", [
            (None, "Allogrooming", "The cat licks, orally manipulates or chews another cat's fur, or initiates a lick without making contact.", "behaviour_action", "Table 1, Communication and interaction", "State"),
            (None, "Autogrooming", "The cat licks, bites or chews its own fur, including wiping its head with a previously licked front paw.", "behaviour_action", "Table 1, Communication and interaction", "State"),
            (None, "Sniffing", "The cat inhales through its nose to smell another cat or an environmental target; target is an optional modifier.", "behaviour_action", "Table 1, Communication and interaction", "Event"),
        ]),
    ]
    with connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS publication_review (
            observed_element_id INTEGER NOT NULL REFERENCES observed_element(observed_element_id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL REFERENCES source(source_id),
            status TEXT NOT NULL DEFAULT 'pending_review',
            reason TEXT,
            PRIMARY KEY(observed_element_id, source_id)
        )""")
        for authors, year, title, url, entries in publications:
            connection.execute("INSERT OR IGNORE INTO source(authors, year, title, source_url) VALUES (?, ?, ?, ?)",
                               (authors, year, title, url))
            source_id = connection.execute("SELECT source_id FROM source WHERE source_url=?", (url,)).fetchone()[0]
            for abbreviation, name, definition, modality, location, temporal_type in entries:
                connection.execute("""INSERT OR IGNORE INTO code
                    (source_id, original_code, original_name, operational_definition,
                     applicable_interaction, temporal_type, source_location, modality)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_id, abbreviation, name, definition,
                     "Cat–cat social context" if authors == "Van Belle et al." else "Domestic cat behaviour",
                     temporal_type, location, modality))


ensure_extended_scientific_catalogue()


def get_cats():
    with connect() as connection:
        return connection.execute(
            "SELECT cat_id, name FROM cat ORDER BY name"
        ).fetchall()


def get_observations():
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                observation.observation_id,
                observation.cat_id,
                cat.name,
                observation.date,
                observation.time,
                observation.general_setting,
                observation.raw_observation,
                observation.structure_completed
            FROM observation
            JOIN cat
                ON observation.cat_id = cat.cat_id
            ORDER BY observation.observation_id DESC
            """
        ).fetchall()


def observation_label(observation):
    return (
        f"{observation[2]} — "
        f"{observation[3]} {observation[4]} — "
        f"{observation[6][:60]}"
    )


def get_moments(observation_id):
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                sequence_item_id,
                item_order,
                location
            FROM sequence_item
            WHERE observation_id = ?
              AND item_type = 'moment'
            ORDER BY item_order, sequence_item_id
            """,
            (observation_id,)
        )

        moments = cursor.fetchall()

        result = []

        for moment_id, moment_order, moment_location in moments:
            cursor.execute(
                """
                SELECT
                    modality,
                    factual_description,
                    target_type,
                    target_description,
                    spatial_context,
                    occurrence,
                    change
                FROM observed_element
                WHERE sequence_item_id = ?
                ORDER BY observed_element_id
                """,
                (moment_id,)
            )

            elements = {}
            for row in cursor.fetchall():
                elements[row[0]] = {
                    "description": row[1] or "",
                    "target_type": row[2] or "",
                    "target_description": row[3] or "",
                    "spatial_context": row[4] or "",
                    "occurrence": row[5] or "",
                    "change": row[6] or "",
                }

            result.append((moment_id, moment_order, moment_location, elements))

        return result


def update_moment(moment_id, location, elements):
    """Update elements in place; invalidate coding only when evidence changes."""
    fields = ("factual_description", "target_type", "target_description",
              "spatial_context", "occurrence", "change")
    with connect() as connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE sequence_item SET location = ? WHERE sequence_item_id = ?",
                       ((location or "").strip() or None, moment_id))
        existing = {
            row[1]: row for row in cursor.execute(
                "SELECT observed_element_id, modality, factual_description, target_type, "
                "target_description, spatial_context, occurrence, change "
                "FROM observed_element WHERE sequence_item_id = ?", (moment_id,)
            ).fetchall()
        }
        for modality, data in elements.items():
            description = (data.get("description") or "").strip()
            previous = existing.pop(modality, None)
            if not description:
                if previous:
                    cursor.execute("DELETE FROM element_coding WHERE observed_element_id = ?", (previous[0],))
                    cursor.execute("DELETE FROM publication_review WHERE observed_element_id = ?", (previous[0],))
                    cursor.execute("DELETE FROM observed_element WHERE observed_element_id = ?", (previous[0],))
                continue
            values = (
                description, data.get("target_type") or None,
                (data.get("target_description") or "").strip() or None,
                (data.get("spatial_context") or "").strip() or None,
                data.get("occurrence") or None, data.get("change") or None,
            )
            if previous:
                if tuple(previous[2:]) != values:
                    cursor.execute("DELETE FROM element_coding WHERE observed_element_id = ?", (previous[0],))
                    cursor.execute("DELETE FROM publication_review WHERE observed_element_id = ?", (previous[0],))
                    cursor.execute(
                        "UPDATE observed_element SET factual_description=?, target_type=?, "
                        "target_description=?, spatial_context=?, occurrence=?, change=?, "
                        "coding_status='pending_review', coding_reason=NULL "
                        "WHERE observed_element_id=?", (*values, previous[0])
                    )
            else:
                cursor.execute(
                    "INSERT INTO observed_element (sequence_item_id, modality, "
                    "factual_description, target_type, target_description, spatial_context, "
                    "occurrence, change) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (moment_id, modality, *values)
                )
        for previous in existing.values():
            cursor.execute("DELETE FROM element_coding WHERE observed_element_id=?", (previous[0],))
            cursor.execute("DELETE FROM publication_review WHERE observed_element_id=?", (previous[0],))
            cursor.execute("DELETE FROM observed_element WHERE observed_element_id=?", (previous[0],))


def delete_moment(observation_id, moment_id):
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM sequence_item
            WHERE sequence_item_id = ?
              AND observation_id = ?
              AND item_type = 'moment'
            """,
            (moment_id, observation_id)
        )

        cursor.execute(
            """
            SELECT sequence_item_id
            FROM sequence_item
            WHERE observation_id = ?
              AND item_type = 'moment'
            ORDER BY item_order, sequence_item_id
            """,
            (observation_id,)
        )

        remaining_moments = cursor.fetchall()

        for new_order, (remaining_id,) in enumerate(
            remaining_moments,
            start=1
        ):
            cursor.execute(
                """
                UPDATE sequence_item
                SET item_order = ?
                WHERE sequence_item_id = ?
                """,
                (new_order, remaining_id)
            )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM observed_element
            JOIN sequence_item
                ON observed_element.sequence_item_id =
                   sequence_item.sequence_item_id
            WHERE sequence_item.observation_id = ?
              AND sequence_item.item_type = 'moment'
            """,
            (observation_id,)
        )

        element_count = cursor.fetchone()[0]

        if element_count == 0:
            cursor.execute(
                """
                UPDATE observation
                SET structure_completed = 0
                WHERE observation_id = ?
                """,
                (observation_id,)
            )


def moment_fields(prefix, initial=None):
    initial = initial or {}
    values = {}

    for modality, label in MODALITIES:
        values[modality] = st.text_input(
            label,
            value=initial.get(modality, ""),
            key=f"{prefix}_{modality}"
        )

    return values


def show_moment_elements(elements):
    if not elements:
        st.warning(
            "No observed details have been recorded for this moment."
        )
        return

    for modality, label in MODALITIES:
        if modality in elements:
            data = elements[modality]
            st.write(f"**{label}:** {data['description']}")

            details = []

            if data["target_type"]:
                target_text = data["target_type"]
                if data["target_description"]:
                    target_text += f" — {data['target_description']}"
                details.append(f"Target: {target_text}")
            elif data["target_description"]:
                details.append(f"Target: {data['target_description']}")

            if data["spatial_context"]:
                details.append(
                    "Spatial relation / factual context: "
                    + data["spatial_context"]
                )

            if data["occurrence"]:
                details.append(
                    f"Occurrence: {data['occurrence']}"
                )

            if data["change"]:
                details.append(
                    f"Change: {data['change']}"
                )

            if details:
                st.caption(" · ".join(details))


# -------------------------
# APP HEADER
# -------------------------

st.title("🐈 FelineObs")
st.write("Structured feline behaviour observation")

cats = get_cats()


# -------------------------
# ADD A CAT
# -------------------------

st.subheader("Add a cat")

with st.form(
    "add_cat_form",
    clear_on_submit=True,
    enter_to_submit=False
):
    new_cat_name = st.text_input(
        "Cat name"
    )

    add_cat = st.form_submit_button(
        "Add cat"
    )

if add_cat:
    if new_cat_name.strip():

        with connect() as connection:
            connection.execute(
                "INSERT INTO cat (name) VALUES (?)",
                (new_cat_name.strip(),)
            )

        st.rerun()

    else:
        st.warning(
            "Please enter a cat name."
        )


# -------------------------
# DELETE A CAT
# -------------------------

st.subheader("Delete a cat")

if cats:

    cat_to_delete = st.selectbox(
        "Select cat to delete",
        cats,
        index=None,
        placeholder="Select a cat...",
        format_func=lambda cat: cat[1],
        key="cat_to_delete"
    )

    delete_cat_state_key = "confirming_cat_delete"

    if delete_cat_state_key not in st.session_state:
        st.session_state[delete_cat_state_key] = False

    if cat_to_delete is None:
        st.session_state[delete_cat_state_key] = False

    if not st.session_state[delete_cat_state_key]:
        if st.button(
            "Delete cat",
            key="delete_cat_button",
            disabled=cat_to_delete is None
        ):
            st.session_state[delete_cat_state_key] = True
            st.rerun()

    else:
        st.warning(
            f"{cat_to_delete[1]} will be permanently deleted."
        )

        with st.form(
            "confirm_delete_cat_form",
            enter_to_submit=False
        ):
            confirm_cat_delete = st.checkbox(
                f"I confirm that I want to delete {cat_to_delete[1]}"
            )

            confirm_delete_cat = st.form_submit_button(
                "Confirm deletion"
            )

            cancel_delete_cat = st.form_submit_button(
                "Cancel"
            )

        if confirm_delete_cat:
            if not confirm_cat_delete:
                st.warning(
                    "Please confirm before deleting the cat."
                )
            else:
                try:
                    with connect() as connection:
                        connection.execute(
                            """
                            DELETE FROM cat
                            WHERE cat_id = ?
                            """,
                            (cat_to_delete[0],)
                        )

                except sqlite3.IntegrityError:
                    st.error(
                        "This cat cannot be deleted because it has observations."
                    )

                else:
                    st.session_state[delete_cat_state_key] = False
                    st.rerun()

        if cancel_delete_cat:
            st.session_state[delete_cat_state_key] = False
            st.rerun()


# -------------------------
# STEP 1 — RECORD OBSERVATION
# -------------------------

st.divider()
st.header("1 · Record observation")

if cats:

    with st.form(
        "new_observation_form",
        clear_on_submit=True,
        enter_to_submit=False
    ):

        observation_cat = st.selectbox(
            "Focal cat",
            cats,
            index=None,
            placeholder="Select a cat...",
            format_func=lambda cat: cat[1]
        )

        observation_date = st.date_input(
            "Date",
            value=None,
            max_value=datetime.today().date()
        )

        observation_time_text = st.text_input(
            "Time",
            placeholder="HH:MM",
            help="Enter the observed time manually, for example 18:35."
        )

        raw_observation = st.text_area(
            "What did you observe?",
            placeholder="Describe the observation in your own words.",
            help=(
                "Write what you observed naturally. "
                "The next step will separate the observable details "
                "from possible interpretations."
            )
        )

        save_observation = st.form_submit_button(
            "+ Create observation"
        )

    if save_observation:

        parsed_observation_time = None

        if observation_cat is None:
            st.warning("Please select the focal cat.")

        elif observation_date is None:
            st.warning("Please select the date.")

        elif not observation_time_text.strip():
            st.warning("Please enter the time.")

        else:
            try:
                parsed_observation_time = datetime.strptime(
                    observation_time_text.strip(),
                    "%H:%M"
                ).time()
            except ValueError:
                st.warning(
                    "Please enter the time in HH:MM format, for example 18:35."
                )

        if (
            observation_cat is not None
            and observation_date is not None
            and parsed_observation_time is not None
        ):
            if not raw_observation.strip():
                st.warning("Please describe what you observed.")
            else:
                with connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO observation (
                            cat_id,
                            date,
                            time,
                            general_setting,
                            initial_context,
                            raw_observation,
                            notes,
                            structure_completed
                        )
                        VALUES (?, ?, ?, ?, NULL, ?, NULL, 0)
                        """,
                        (
                            observation_cat[0],
                            str(observation_date),
                            parsed_observation_time.strftime("%H:%M"),
                            None,
                            raw_observation.strip()
                        )
                    )

                st.success(
                    "Observation saved. You can now structure it in Step 2."
                )

else:
    st.info(
        "Add a cat before recording an observation."
    )


# -------------------------
# STEP 2 — STRUCTURE OBSERVATION
# -------------------------

st.divider()
st.header("2 · Structure observation")

with st.container(border=True):
    observations_for_structure = get_observations()

    if observations_for_structure:

        selected_observation = st.selectbox(
            "Select observation",
            observations_for_structure,
            index=None,
            placeholder="Select an observation...",
            format_func=observation_label,
            key="structure_observation"
        )

        if selected_observation is None:
            st.info(
                "Select an observation to view and structure its moments."
            )
        else:
            observation_id = selected_observation[0]
            structure_completed = bool(
                selected_observation[7]
            )

            st.write("Observation description (recorded in Step 1):")
            st.info(selected_observation[6])

            st.caption(
                "Break the observation down into moments in chronological order. "
                "Each moment describes what the focal cat was doing at that stage "
                "of the sequence. Record only what you directly observed and "
                "leave unknown details blank."
            )

            saved_moments = get_moments(
                observation_id
            )

            # -------------------------
            # SAVED MOMENTS
            # -------------------------

            for moment_id, moment_order, moment_location, moment_elements in saved_moments:

                if moment_elements:
                    st.subheader(
                        f"Moment {moment_order} ✓"
                    )
                else:
                    st.subheader(
                        f"Moment {moment_order} ⚠️"
                    )

                if moment_location:
                    st.write(f"**Location:** {moment_location}")

                show_moment_elements(
                    moment_elements
                )

                edit_state_key = (
                    f"editing_moment_{observation_id}_{moment_id}"
                )

                delete_state_key = (
                    f"deleting_moment_{observation_id}_{moment_id}"
                )

                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False

                if delete_state_key not in st.session_state:
                    st.session_state[delete_state_key] = False

                if not st.session_state[edit_state_key]:

                    edit_col, delete_col = st.columns(2)

                    with edit_col:
                        if st.button(
                            "Edit moment",
                            key=f"edit_button_{observation_id}_{moment_id}"
                        ):
                            st.session_state[edit_state_key] = True
                            st.session_state[delete_state_key] = False
                            st.rerun()

                    with delete_col:
                        if st.button(
                            "Delete moment",
                            key=f"delete_button_{observation_id}_{moment_id}"
                        ):
                            st.session_state[delete_state_key] = True
                            st.session_state[edit_state_key] = False
                            st.rerun()

                if st.session_state[edit_state_key]:

                    st.write(
                        f"**Editing Moment {moment_order}**"
                    )

                    with st.form(
                        f"edit_moment_form_{observation_id}_{moment_id}",
                        enter_to_submit=False
                    ):

                        edited_location = st.text_input(
                            "Moment location (optional)",
                            value=moment_location or "",
                            help=(
                                "Where the focal cat was during this moment, "
                                "for example: bedroom, hallway or kitchen."
                            )
                        )

                        edited_elements = {}

                        for modality, label in MODALITIES:
                            current = moment_elements.get(modality, {})

                            description = st.text_input(
                                label,
                                value=current.get("description", ""),
                                key=f"edit_desc_{observation_id}_{moment_id}_{modality}"
                            )

                            with st.expander(
                                f"Optional details — {label}"
                            ):
                                target_options = [
                                    "",
                                    "Cat",
                                    "Person",
                                    "Object",
                                    "Environment"
                                ]
                                current_target = current.get(
                                    "target_type",
                                    ""
                                )
                                target_index = (
                                    target_options.index(current_target)
                                    if current_target in target_options
                                    else 0
                                )

                                target_type = st.selectbox(
                                    "Target type",
                                    target_options,
                                    index=target_index,
                                    key=f"edit_target_type_{observation_id}_{moment_id}_{modality}"
                                )

                                target_description = st.text_input(
                                    "Target description",
                                    value=current.get(
                                        "target_description",
                                        ""
                                    ),
                                    key=f"edit_target_description_{observation_id}_{moment_id}_{modality}"
                                )

                                spatial_context = st.text_input(
                                    "Spatial relation / factual context",
                                    value=current.get(
                                        "spatial_context",
                                        ""
                                    ),
                                    key=f"edit_spatial_{observation_id}_{moment_id}_{modality}"
                                )

                                occurrence_options = [
                                    "",
                                    "single",
                                    "repeated",
                                    "ongoing"
                                ]
                                current_occurrence = current.get(
                                    "occurrence",
                                    ""
                                )
                                occurrence_index = (
                                    occurrence_options.index(
                                        current_occurrence
                                    )
                                    if current_occurrence
                                    in occurrence_options
                                    else 0
                                )

                                occurrence = st.selectbox(
                                    "Occurrence",
                                    occurrence_options,
                                    index=occurrence_index,
                                    key=f"edit_occurrence_{observation_id}_{moment_id}_{modality}"
                                )

                                change_options = [
                                    "",
                                    "observed_start",
                                    "observed_stop"
                                ]
                                current_change = current.get(
                                    "change",
                                    ""
                                )
                                change_index = (
                                    change_options.index(current_change)
                                    if current_change in change_options
                                    else 0
                                )

                                change = st.selectbox(
                                    "Change",
                                    change_options,
                                    index=change_index,
                                    key=f"edit_change_{observation_id}_{moment_id}_{modality}"
                                )

                            edited_elements[modality] = {
                                "description": description,
                                "target_type": target_type,
                                "target_description": target_description,
                                "spatial_context": spatial_context,
                                "occurrence": occurrence,
                                "change": change,
                            }

                        save_changes = st.form_submit_button(
                            "Save changes"
                        )

                        cancel_edit = st.form_submit_button(
                            "Cancel"
                        )

                    if save_changes:

                        if not any(
                            data["description"].strip()
                            for data in edited_elements.values()
                        ):
                            st.warning(
                                "Fill in at least one field, "
                                "or delete this moment."
                            )

                        else:
                            update_moment(
                                moment_id,
                                edited_location,
                                edited_elements
                            )

                            st.session_state[edit_state_key] = False
                            st.rerun()

                    if cancel_edit:
                        st.session_state[edit_state_key] = False
                        st.rerun()

                if st.session_state[delete_state_key]:

                    st.warning(
                        f"Moment {moment_order} will be permanently deleted."
                    )

                    with st.form(
                        f"delete_moment_form_{observation_id}_{moment_id}",
                        enter_to_submit=False
                    ):

                        confirm_moment_delete = st.checkbox(
                            "I confirm that I want to delete this moment."
                        )

                        confirm_delete_moment = st.form_submit_button(
                            "Confirm deletion"
                        )

                        cancel_delete_moment = st.form_submit_button(
                            "Cancel"
                        )

                    if confirm_delete_moment:

                        if not confirm_moment_delete:
                            st.warning(
                                "Please confirm before deleting the moment."
                            )

                        else:
                            delete_moment(
                                observation_id,
                                moment_id
                            )

                            st.session_state[delete_state_key] = False
                            st.rerun()

                    if cancel_delete_moment:
                        st.session_state[delete_state_key] = False
                        st.rerun()

                st.divider()

            # -------------------------
            # NEXT MOMENT / END
            # -------------------------

            saved_moments = get_moments(
                observation_id
            )

            has_empty_moment = any(
                not elements
                for _, _, _, elements in saved_moments
            )

            has_content = any(
                bool(elements)
                for _, _, _, elements in saved_moments
            )

            add_moment_key = (
                f"adding_moment_{observation_id}"
            )

            if add_moment_key not in st.session_state:
                st.session_state[add_moment_key] = False

            if not structure_completed:

                if has_empty_moment:
                    st.info(
                        "There is an empty saved moment. "
                        "Edit it and fill in at least one field, "
                        "or delete it before continuing."
                    )

                elif not st.session_state[add_moment_key]:

                    action_col_1, action_col_2 = st.columns(2)

                    with action_col_1:
                        if st.button(
                            "+ Add moment",
                            key=f"add_moment_{observation_id}"
                        ):
                            st.session_state[add_moment_key] = True
                            st.rerun()

                    with action_col_2:
                        if st.button(
                            "✓ End observation",
                            key=f"end_observation_{observation_id}",
                            disabled=not has_content
                        ):
                            with connect() as connection:
                                connection.execute(
                                    """
                                    UPDATE observation
                                    SET structure_completed = 1
                                    WHERE observation_id = ?
                                    """,
                                    (observation_id,)
                                )

                            st.session_state[add_moment_key] = False
                            st.rerun()

                    if not has_content:
                        st.caption(
                            "Add at least one moment before ending the observation."
                        )

                else:
                    next_moment_number = len(saved_moments) + 1

                    st.subheader(
                        f"Moment {next_moment_number}"
                    )

                    st.caption(
                        "Fill in the details you directly observed. "
                        "Leave unknown details blank. "
                        "At least one observed detail is required to save a moment."
                    )

                    with st.form(
                        f"new_moment_form_{observation_id}_{next_moment_number}",
                        clear_on_submit=True,
                        enter_to_submit=False
                    ):

                        new_moment_location = st.text_input(
                            "Moment location (optional)",
                            help=(
                                "Where the focal cat was during this moment, "
                                "for example: bedroom, hallway or kitchen."
                            )
                        )

                        new_elements = {}

                        for modality, label in MODALITIES:
                            description = st.text_input(
                                label,
                                key=f"new_desc_{observation_id}_{next_moment_number}_{modality}"
                            )

                            with st.expander(
                                f"Optional details — {label}"
                            ):
                                target_type = st.selectbox(
                                    "Target type",
                                    [
                                        "",
                                        "Cat",
                                        "Person",
                                        "Object",
                                        "Environment"
                                    ],
                                    key=f"new_target_type_{observation_id}_{next_moment_number}_{modality}"
                                )

                                target_description = st.text_input(
                                    "Target description",
                                    key=f"new_target_description_{observation_id}_{next_moment_number}_{modality}"
                                )

                                spatial_context = st.text_input(
                                    "Spatial relation / factual context",
                                    key=f"new_spatial_{observation_id}_{next_moment_number}_{modality}"
                                )

                                occurrence = st.selectbox(
                                    "Occurrence",
                                    [
                                        "",
                                        "single",
                                        "repeated",
                                        "ongoing"
                                    ],
                                    key=f"new_occurrence_{observation_id}_{next_moment_number}_{modality}"
                                )

                                change = st.selectbox(
                                    "Change",
                                    [
                                        "",
                                        "observed_start",
                                        "observed_stop"
                                    ],
                                    key=f"new_change_{observation_id}_{next_moment_number}_{modality}"
                                )

                            new_elements[modality] = {
                                "description": description,
                                "target_type": target_type,
                                "target_description": target_description,
                                "spatial_context": spatial_context,
                                "occurrence": occurrence,
                                "change": change,
                            }

                        save_new_moment = st.form_submit_button(
                            f"Save Moment {next_moment_number}"
                        )

                        cancel_new_moment = st.form_submit_button(
                            "Cancel"
                        )

                    if save_new_moment:

                        if not any(
                            data["description"].strip()
                            for data in new_elements.values()
                        ):
                            st.warning(
                                "No observed details have been recorded for this moment. "
                                "Fill in at least one observed field."
                            )

                        else:
                            with connect() as connection:
                                cursor = connection.cursor()

                                cursor.execute(
                                    """
                                    INSERT INTO sequence_item (
                                        observation_id,
                                        item_order,
                                        item_type,
                                        factual_description,
                                        location
                                    )
                                    VALUES (?, ?, 'moment', NULL, ?)
                                    """,
                                    (
                                        observation_id,
                                        next_moment_number,
                                        new_moment_location.strip() or None
                                    )
                                )

                                new_moment_id = cursor.lastrowid

                                for modality, data in new_elements.items():
                                    description = data[
                                        "description"
                                    ].strip()

                                    if description:
                                        cursor.execute(
                                            """
                                            INSERT INTO observed_element (
                                                sequence_item_id,
                                                modality,
                                                factual_description,
                                                target_type,
                                                target_description,
                                                spatial_context,
                                                occurrence,
                                                change
                                            )
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                            """,
                                            (
                                                new_moment_id,
                                                modality,
                                                description,
                                                data["target_type"] or None,
                                                data["target_description"].strip() or None,
                                                data["spatial_context"].strip() or None,
                                                data["occurrence"] or None,
                                                data["change"] or None
                                            )
                                        )

                            st.session_state[add_moment_key] = False
                            st.rerun()

                    if cancel_new_moment:
                        st.session_state[add_moment_key] = False
                        st.rerun()

            else:
                st.success(
                    "✓ This observation has been structured."
                )

                st.caption(
                    "You can still edit or delete saved moments."
                )

                if st.button(
                    "Reopen observation to add moments",
                    key=f"reopen_observation_{observation_id}"
                ):
                    with connect() as connection:
                        connection.execute(
                            """
                            UPDATE observation
                            SET structure_completed = 0
                            WHERE observation_id = ?
                            """,
                            (observation_id,)
                        )

                    st.session_state[add_moment_key] = False
                    st.rerun()

    else:
        st.info(
            "Create an observation before structuring it."
        )


# -------------------------
# STEP 3 — VIEW / EDIT OBSERVATIONS
# -------------------------

st.divider()
st.header("3 · View / edit observations")

with st.container(border=True):
    observations_for_view = get_observations()

    if observations_for_view:

        view_observation = st.selectbox(
            "Select observation",
            observations_for_view,
            index=None,
            placeholder="Select an observation...",
            format_func=observation_label,
            key="view_observation"
        )

        if view_observation is None:
            st.info(
                "Select an observation to open, edit or delete it."
            )

        else:
            view_observation_id = view_observation[0]

            open_col, delete_col = st.columns(2)

            with open_col:
                if st.button(
                    "Open observation",
                    key=f"open_observation_{view_observation_id}"
                ):
                    st.session_state["open_observation_id"] = (
                        view_observation_id
                    )
                    edit_key = (
                        f"edit_observation_mode_{view_observation_id}"
                    )
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False
                    st.rerun()

            delete_state_key = (
                f"delete_observation_selected_{view_observation_id}"
            )

            if delete_state_key not in st.session_state:
                st.session_state[delete_state_key] = False

            with delete_col:
                if not st.session_state[delete_state_key]:
                    if st.button(
                        "Delete observation",
                        key=f"delete_selected_observation_{view_observation_id}"
                    ):
                        st.session_state[delete_state_key] = True
                        st.rerun()

            if st.session_state[delete_state_key]:
                st.warning(
                    "This observation will be permanently deleted."
                )

                with st.form(
                    f"delete_selected_observation_form_{view_observation_id}",
                    enter_to_submit=False
                ):
                    confirm_selected_delete = st.checkbox(
                        "I confirm that I want to permanently "
                        "delete this observation."
                    )

                    confirm_selected_delete_button = (
                        st.form_submit_button("Confirm deletion")
                    )

                    cancel_selected_delete = (
                        st.form_submit_button("Cancel")
                    )

                if confirm_selected_delete_button:
                    if not confirm_selected_delete:
                        st.warning(
                            "Please confirm before deleting the observation."
                        )
                    else:
                        with connect() as connection:
                            connection.execute(
                                """
                                DELETE FROM observation
                                WHERE observation_id = ?
                                """,
                                (view_observation_id,)
                            )

                        st.session_state.pop(
                            "open_observation_id",
                            None
                        )
                        st.session_state.pop(
                            delete_state_key,
                            None
                        )
                        st.session_state.pop(
                            f"edit_observation_mode_{view_observation_id}",
                            None
                        )
                        st.rerun()

                if cancel_selected_delete:
                    st.session_state[delete_state_key] = False
                    st.rerun()

            if (
                st.session_state.get("open_observation_id")
                == view_observation_id
            ):

                current_observations = get_observations()

                current_observation = next(
                    observation
                    for observation in current_observations
                    if observation[0] == view_observation_id
                )

                (
                    current_id,
                    current_cat_id,
                    current_cat_name,
                    current_date,
                    current_time,
                    _current_location,
                    current_raw,
                    current_completed
                ) = current_observation

                edit_mode_key = (
                    f"edit_observation_mode_{current_id}"
                )

                if edit_mode_key not in st.session_state:
                    st.session_state[edit_mode_key] = False

                st.subheader("Observation summary")

                # -------------------------
                # VIEW MODE
                # -------------------------

                if not st.session_state[edit_mode_key]:

                    top_action_col_1, top_action_col_2 = st.columns(2)

                    with top_action_col_1:
                        if st.button(
                            "✏️ Edit observation",
                            key=f"edit_observation_top_{current_id}"
                        ):
                            st.session_state[edit_mode_key] = True
                            st.rerun()

                    with top_action_col_2:
                        if st.button(
                            "Close observation",
                            key=f"close_observation_top_{current_id}"
                        ):
                            st.session_state.pop(
                                "open_observation_id",
                                None
                            )
                            st.session_state.pop(
                                edit_mode_key,
                                None
                            )
                            st.rerun()

                    st.write("### Observation details")
                    st.write(f"**Focal cat:** {current_cat_name}")
                    st.write(f"**Date:** {current_date}")
                    st.write(f"**Time:** {current_time}")
                    st.write(
                        f"**Observation:** {current_raw}"
                    )

                    st.write("### Structured sequence")

                    summary_moments = get_moments(current_id)

                    if summary_moments:
                        for (
                            moment_id,
                            moment_order,
                            moment_location,
                            elements
                        ) in summary_moments:

                            st.write(
                                f"**Moment {moment_order} "
                                f"{'✓' if elements else '⚠️'}**"
                            )

                            if moment_location:
                                st.write(
                                    f"**Location:** {moment_location}"
                                )

                            show_moment_elements(elements)
                    else:
                        st.write(
                            "No structured moments have been recorded yet."
                        )

                # -------------------------
                # EDIT MODE
                # -------------------------

                else:
                    st.info("Editing observation")

                    # -------------------------
                    # EDIT OBSERVATION DETAILS
                    # -------------------------

                    st.write("### Edit observation details")

                    cat_ids = [cat[0] for cat in cats]
                    current_cat_index = (
                        cat_ids.index(current_cat_id)
                        if current_cat_id in cat_ids
                        else 0
                    )

                    try:
                        date_value = datetime.strptime(
                            current_date,
                            "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        date_value = datetime.today().date()

                    with st.form(
                        f"edit_observation_details_form_{current_id}",
                        enter_to_submit=False
                    ):
                        edited_cat = st.selectbox(
                            "Focal cat",
                            cats,
                            index=current_cat_index,
                            format_func=lambda cat: cat[1]
                        )

                        edited_date = st.date_input(
                            "Date",
                            value=date_value,
                            max_value=datetime.today().date()
                        )

                        edited_time_text = st.text_input(
                            "Time",
                            value=current_time[:5],
                            placeholder="HH:MM"
                        )

                        edited_raw = st.text_area(
                            "Observation",
                            value=current_raw,
                            help=(
                                "This is the description recorded "
                                "in Step 1."
                            )
                        )

                        save_details = st.form_submit_button(
                            "Save changes"
                        )

                        cancel_details = st.form_submit_button(
                            "Cancel"
                        )

                    if save_details:
                        try:
                            parsed_edited_time = datetime.strptime(
                                edited_time_text.strip(),
                                "%H:%M"
                            ).time()
                        except ValueError:
                            st.warning(
                                "Please enter the time in HH:MM "
                                "format, for example 18:35."
                            )
                        else:
                            if not edited_raw.strip():
                                st.warning(
                                    "The observation cannot be empty."
                                )
                            else:
                                with connect() as connection:
                                    connection.execute(
                                        """
                                        UPDATE observation
                                        SET
                                            cat_id = ?,
                                            date = ?,
                                            time = ?,
                                            raw_observation = ?
                                        WHERE observation_id = ?
                                        """,
                                        (
                                            edited_cat[0],
                                            str(edited_date),
                                            parsed_edited_time.strftime(
                                                "%H:%M"
                                            ),
                                            edited_raw.strip(),
                                            current_id
                                        )
                                    )

                                st.session_state[
                                    f"observation_details_saved_{current_id}"
                                ] = True
                                st.session_state[edit_mode_key] = True
                                st.rerun()

                    if st.session_state.pop(
                        f"observation_details_saved_{current_id}",
                        False
                    ):
                        st.success(
                            "✓ Observation details saved. "
                            "You can continue editing the structured sequence below."
                        )

                    if cancel_details:
                        st.rerun()

                    # -------------------------
                    # EDIT STRUCTURED SEQUENCE
                    # -------------------------

                    st.write("### Edit structured sequence")

                    edit_summary_moments = get_moments(
                        current_id
                    )

                    if edit_summary_moments:

                        all_edited_moments = {}

                        with st.form(
                            f"edit_full_sequence_{current_id}",
                            enter_to_submit=False
                        ):

                            for (
                                moment_id,
                                moment_order,
                                moment_location,
                                moment_elements
                            ) in edit_summary_moments:

                                st.write(
                                    f"#### Moment {moment_order}"
                                )

                                edited_location = st.text_input(
                                    "Moment location (optional)",
                                    value=moment_location or "",
                                    key=f"sequence_location_{current_id}_{moment_id}"
                                )

                                edited_elements = {}

                                for modality, label in MODALITIES:
                                    current = moment_elements.get(
                                        modality,
                                        {}
                                    )

                                    description = st.text_input(
                                        label,
                                        value=current.get(
                                            "description",
                                            ""
                                        ),
                                        key=f"sequence_desc_{current_id}_{moment_id}_{modality}"
                                    )

                                    with st.expander(
                                        f"Optional details — {label}"
                                    ):
                                        target_options = [
                                            "",
                                            "Cat",
                                            "Person",
                                            "Object",
                                            "Environment"
                                        ]

                                        current_target = current.get(
                                            "target_type",
                                            ""
                                        )

                                        target_index = (
                                            target_options.index(
                                                current_target
                                            )
                                            if current_target
                                            in target_options
                                            else 0
                                        )

                                        target_type = st.selectbox(
                                            "Target type",
                                            target_options,
                                            index=target_index,
                                            key=f"sequence_target_type_{current_id}_{moment_id}_{modality}"
                                        )

                                        target_description = st.text_input(
                                            "Target description",
                                            value=current.get(
                                                "target_description",
                                                ""
                                            ),
                                            key=f"sequence_target_description_{current_id}_{moment_id}_{modality}"
                                        )

                                        spatial_context = st.text_input(
                                            "Spatial relation / factual context",
                                            value=current.get(
                                                "spatial_context",
                                                ""
                                            ),
                                            key=f"sequence_spatial_{current_id}_{moment_id}_{modality}"
                                        )

                                        occurrence_options = [
                                            "",
                                            "single",
                                            "repeated",
                                            "ongoing"
                                        ]

                                        current_occurrence = current.get(
                                            "occurrence",
                                            ""
                                        )

                                        occurrence_index = (
                                            occurrence_options.index(
                                                current_occurrence
                                            )
                                            if current_occurrence
                                            in occurrence_options
                                            else 0
                                        )

                                        occurrence = st.selectbox(
                                            "Occurrence",
                                            occurrence_options,
                                            index=occurrence_index,
                                            key=f"sequence_occurrence_{current_id}_{moment_id}_{modality}"
                                        )

                                        change_options = [
                                            "",
                                            "observed_start",
                                            "observed_stop"
                                        ]

                                        current_change = current.get(
                                            "change",
                                            ""
                                        )

                                        change_index = (
                                            change_options.index(
                                                current_change
                                            )
                                            if current_change
                                            in change_options
                                            else 0
                                        )

                                        change = st.selectbox(
                                            "Change",
                                            change_options,
                                            index=change_index,
                                            key=f"sequence_change_{current_id}_{moment_id}_{modality}"
                                        )

                                    edited_elements[modality] = {
                                        "description": description,
                                        "target_type": target_type,
                                        "target_description": target_description,
                                        "spatial_context": spatial_context,
                                        "occurrence": occurrence,
                                        "change": change,
                                    }

                                all_edited_moments[moment_id] = {
                                    "order": moment_order,
                                    "location": edited_location,
                                    "elements": edited_elements,
                                }

                                st.divider()

                            save_sequence_changes = (
                                st.form_submit_button(
                                    "Save sequence changes"
                                )
                            )

                            cancel_sequence_changes = (
                                st.form_submit_button(
                                    "Cancel"
                                )
                            )

                        if save_sequence_changes:
                            invalid_moments = [
                                data["order"]
                                for data in all_edited_moments.values()
                                if not any(
                                    element["description"].strip()
                                    for element
                                    in data["elements"].values()
                                )
                            ]

                            if invalid_moments:
                                st.warning(
                                    "Each moment must contain at least "
                                    "one observed detail. Check Moment(s): "
                                    + ", ".join(
                                        str(number)
                                        for number in invalid_moments
                                    )
                                )
                            else:
                                for moment_id, data in (
                                    all_edited_moments.items()
                                ):
                                    update_moment(
                                        moment_id,
                                        data["location"],
                                        data["elements"]
                                    )

                                st.session_state[
                                    f"sequence_saved_{current_id}"
                                ] = True
                                st.session_state[edit_mode_key] = True
                                st.rerun()

                        if st.session_state.pop(
                            f"sequence_saved_{current_id}",
                            False
                        ):
                            st.success(
                                "Structured sequence changes saved."
                            )

                        if cancel_sequence_changes:
                            st.session_state[edit_mode_key] = True
                            st.rerun()

                    else:
                        st.info(
                            "There are no moments to edit."
                        )

                    st.divider()

                    st.caption(
                        "Save Observation details and Structured sequence "
                        "separately. Close editing only when you have finished."
                    )

                    if st.button(
                        "Close editing",
                        key=f"close_editing_{current_id}"
                    ):
                        st.session_state[edit_mode_key] = False
                        st.rerun()

    else:
        st.info(
            "There are no observations to view."
        )



# -------------------------
# STEP 4 — SCIENTIFIC CODING
# -------------------------

def preliminary_coding_assessment(element, candidates, authors):
    """Conservative screening; returns leads to review, never scientific assignments."""
    import re
    description = (element["factual_description"] or "").strip().casefold()
    words = re.findall(r"[^\W_]+", description, flags=re.UNICODE)
    placeholders = {"asdf", "sdf", "asd", "test", "testing", "prueba", "xxx", "abc", "qwerty"}
    if not words or all(w in placeholders for w in words) or len(description) < 8:
        return "Insufficient observable detail", "The description is too brief or appears to be a placeholder.", []

    def any_term(*terms):
        return any(term in description for term in terms)

    suggestions = []
    for c in candidates:
        name = c["original_name"].casefold()
        match = False
        if authors == "Haywood et al.":
            person = element["target_type"] == "Person" or any_term("person", "human", "owner", "guardian", "persona", "humano", "tutor", "dueño", "dueña")
            if name == "approach person":
                match = person and any_term("approach", "toward", "se acerca", "se acercó", "acercarse")
            elif name == "rub person":
                match = person and any_term("rub", "frota", "frotó", "restriega", "restrega")
        elif authors == "Kappel et al." and element["modality"] == "posture_locomotion":
            if name == "sit":
                match = any_term("sitting", "sits", "se sienta", "sentado", "sentada")
            elif name == "stand":
                match = any_term("standing", "stands", "de pie", "parado", "parada")
            elif name == "walk":
                match = any_term("walking", "walks", "camina", "caminando", "anda ")
        elif authors == "Van Belle et al." and element["modality"] == "behaviour_action":
            if name == "allogrooming":
                match = any_term("lick", "groom", "lam", "acical") and (
                    element["target_type"] == "Cat" or any_term("another cat", "other cat", "otro gato", "otra gata", "princesa", "kiko")
                )
            elif name == "autogrooming":
                match = any_term("self-groom", "autogroom", "acicala", "se lame", "licks itself", "licking itself")
            elif name == "sniffing":
                match = any_term("sniff", "olfatea", "huele", "olfate")
        if match:
            suggestions.append(c)
    if suggestions:
        return "Possible candidates — verification needed", "Simple word matching found possible entries; check every original definition and its context.", suggestions
    if not candidates:
        return "No codes for this element type", "This publication has no imported codes for this recording field.", []
    return "No candidate detected", "Limited keyword screening found no candidate. This does not mean that no scientific definition applies.", []


st.divider()
st.header("4 · Scientific coding")
st.caption("Select a publication and review suggested codes. No code is assigned automatically.")

SCIENTIFIC_PUBLICATIONS = {
    "Haywood et al. (2021) — Cat–human interactions": "Haywood et al.",
    "Kappel et al. (2024) — Domestic cat ethogram": "Kappel et al.",
    "Van Belle et al. (2025) — Cat–cat social interactions": "Van Belle et al.",
}
selected_publication = st.selectbox("Scientific publication", list(SCIENTIFIC_PUBLICATIONS))
selected_authors = SCIENTIFIC_PUBLICATIONS[selected_publication]

with connect() as connection:
    connection.row_factory = sqlite3.Row
    selected_source = connection.execute(
        "SELECT * FROM source WHERE authors=? ORDER BY source_id DESC LIMIT 1", (selected_authors,)
    ).fetchone()
    source_codes = connection.execute(
        """SELECT c.*, s.authors, s.year, s.source_url FROM code c
           JOIN source s ON s.source_id=c.source_id WHERE s.source_id=?
           ORDER BY c.original_name""", (selected_source["source_id"],)
    ).fetchall() if selected_source else []

if selected_source:
    st.caption(f"{len(source_codes)} definitions currently available from this publication · Partial catalogue")
    st.markdown(f"[Read the original publication]({selected_source['source_url']})")
with st.expander("About the scientific catalogue"):
    st.write(
        "All three publications are treated as independent scientific sources. "
        "Only a small, verified selection of their behavioural definitions has been imported. "
        "Definitions shown here are concise paraphrases: consult the original tables before confirming a code. "
        "A missing suggestion does not mean a behaviour is absent from the literature."
    )

coding_observations = get_observations()
if not coding_observations:
    st.info("Create and structure an observation before scientific coding.")
else:
    coding_observation = st.selectbox(
        "Select observation", coding_observations, index=None,
        placeholder="Select an observation...", format_func=observation_label,
        key="coding_observation"
    )
    if coding_observation is not None:
        with connect() as connection:
            connection.row_factory = sqlite3.Row
            observed_rows = connection.execute("""
                SELECT e.*, s.item_order FROM observed_element e
                JOIN sequence_item s ON s.sequence_item_id=e.sequence_item_id
                WHERE s.observation_id=? AND s.item_type='moment'
                ORDER BY s.item_order, e.observed_element_id
            """, (coding_observation[0],)).fetchall()
            assigned_rows = connection.execute("""
                SELECT ec.observed_element_id, ec.code_id FROM element_coding ec
                JOIN code c ON c.code_id=ec.code_id
                JOIN observed_element e ON e.observed_element_id=ec.observed_element_id
                JOIN sequence_item si ON si.sequence_item_id=e.sequence_item_id
                WHERE si.observation_id=? AND c.source_id=?
            """, (coding_observation[0], selected_source["source_id"])).fetchall()
            review_rows = connection.execute("""
                SELECT pr.* FROM publication_review pr
                JOIN observed_element e ON e.observed_element_id=pr.observed_element_id
                JOIN sequence_item si ON si.sequence_item_id=e.sequence_item_id
                WHERE si.observation_id=? AND pr.source_id=?
            """, (coding_observation[0], selected_source["source_id"])).fetchall()
        assigned_by_element = {}
        for row in assigned_rows:
            assigned_by_element.setdefault(row["observed_element_id"], set()).add(row["code_id"])
        review_by_element = {row["observed_element_id"]: row for row in review_rows}
        if not observed_rows:
            st.info("This observation has no structured elements yet. Add moments in Step 2.")
        else:
            st.caption(f"{len(observed_rows)} observed elements")

        for element in observed_rows:
            element_id = element["observed_element_id"]
            candidates = [c for c in source_codes if c["modality"] == element["modality"]]
            assessment, explanation, suggested = preliminary_coding_assessment(element, candidates, selected_authors)
            label = dict(MODALITIES).get(element["modality"], element["modality"])
            code_by_id = {c["code_id"]: c for c in candidates}
            assigned = assigned_by_element.get(element_id, set())
            review = review_by_element.get(element_id)
            status = review["status"] if review else (
                element["coding_status"] if selected_authors == "Haywood et al." else "pending_review"
            )
            reason = review["reason"] if review else (
                element["coding_reason"] if selected_authors == "Haywood et al." else None
            )

            with st.container(border=True):
                st.markdown(f"**Moment {element['item_order']} · {label}**")
                st.write(element["factual_description"])
                if assigned:
                    st.success("Confirmed codes")
                    for cid in sorted(assigned):
                        if cid in code_by_id:
                            st.caption(code_by_id[cid]["original_name"])
                elif status == "not_coded":
                    st.info("Reviewed · Not coded")
                    if reason:
                        st.caption(reason)
                elif suggested:
                    st.warning("Possible candidates · Review needed")
                    st.write(", ".join(c["original_name"] for c in suggested))
                else:
                    st.info(assessment)

                with st.expander("Review scientific assessment"):
                    st.caption(explanation)
                    if selected_authors == "Van Belle et al.":
                        st.caption("EFSI was developed for social interactions in multicat households. Verify that the observed context is appropriate.")
                    for c in candidates:
                        with st.expander(f"{c['original_name']} — {c['authors']} ({c['year']})"):
                            st.write(f"**Definition (concise paraphrase):** {c['operational_definition']}")
                            if c["original_code"]:
                                st.write(f"**Original abbreviation:** {c['original_code']}")
                            st.write(f"**Original table:** {c['source_location']}")
                            st.write(f"**Temporal type:** {c['temporal_type']}")
                            st.markdown(f"[Check original definition]({c['source_url']})")

                    with st.form(f"review_{element_id}_{selected_source['source_id']}", enter_to_submit=False):
                        selection = st.multiselect(
                            "Verified codes (optional)", options=list(code_by_id),
                            default=[cid for cid in assigned if cid in code_by_id],
                            format_func=lambda cid: code_by_id[cid]["original_name"]
                        )
                        reason_options = [
                            "Insufficient observed detail to meet a definition",
                            "No suitable code in the currently imported catalogue",
                        ]
                        default_reason = reason if reason in reason_options else reason_options[1]
                        no_code_reason = st.selectbox(
                            "Reason if no code is confirmed", reason_options,
                            index=reason_options.index(default_reason)
                        )
                        verified = st.checkbox("I checked the original definitions and their context.")
                        left, right = st.columns(2)
                        with left:
                            save = st.form_submit_button("Save review")
                        with right:
                            reset = st.form_submit_button("Mark as pending")

                    if save or reset:
                        if save and selection and not verified:
                            st.warning("Check the original definitions before confirming codes.")
                        else:
                            with connect() as connection:
                                # Only remove assignments from the SELECTED publication.
                                connection.execute("""
                                    DELETE FROM element_coding WHERE observed_element_id=? AND code_id IN
                                    (SELECT code_id FROM code WHERE source_id=?)
                                """, (element_id, selected_source["source_id"]))
                                if save:
                                    for cid in selection:
                                        connection.execute(
                                            "INSERT OR IGNORE INTO element_coding(observed_element_id, code_id) VALUES (?, ?)",
                                            (element_id, cid)
                                        )
                                if reset:
                                    connection.execute(
                                        "DELETE FROM publication_review WHERE observed_element_id=? AND source_id=?",
                                        (element_id, selected_source["source_id"])
                                    )
                                    # Legacy Haywood status must not masquerade as a new review.
                                    if selected_authors == "Haywood et al.":
                                        connection.execute(
                                            "UPDATE observed_element SET coding_status='pending_review', coding_reason=NULL WHERE observed_element_id=?",
                                            (element_id,)
                                        )
                                else:
                                    new_status = "coded" if selection else "not_coded"
                                    new_reason = None if selection else no_code_reason
                                    connection.execute("""
                                        INSERT INTO publication_review(observed_element_id, source_id, status, reason)
                                        VALUES (?, ?, ?, ?)
                                        ON CONFLICT(observed_element_id, source_id)
                                        DO UPDATE SET status=excluded.status, reason=excluded.reason
                                    """, (element_id, selected_source["source_id"], new_status, new_reason))
                                    if selected_authors == "Haywood et al.":
                                        connection.execute(
                                            "UPDATE observed_element SET coding_status=?, coding_reason=? WHERE observed_element_id=?",
                                            (new_status, new_reason, element_id)
                                        )
                            st.rerun()
