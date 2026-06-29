import sqlite3
import hashlib
import uuid


# encapusltion ()

class Database:
    def __init__(self, db_path="movie_tickets.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def generate_ticket_id(self):
        return "TKT-" + str(uuid.uuid4())[:8].upper()

    def _init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS admins (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name     TEXT NOT NULL,
                phone    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                details         TEXT,
                show_time       TEXT NOT NULL,
                genre           TEXT,
                total_seats     INTEGER DEFAULT 20,
                available_seats INTEGER DEFAULT 20,
                price           REAL    DEFAULT 150.0
            );

            CREATE TABLE IF NOT EXISTS seats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id    INTEGER NOT NULL,
                seat_number TEXT    NOT NULL,
                is_booked   INTEGER DEFAULT 0,
                FOREIGN KEY (movie_id) REFERENCES movies(id),
                UNIQUE(movie_id, seat_number)
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id            INTEGER   PRIMARY KEY AUTOINCREMENT,
                ticket_id     TEXT      UNIQUE NOT NULL,
                movie_id      INTEGER   NOT NULL,
                seat_number   TEXT      NOT NULL,
                customer_name TEXT      NOT NULL,
                phone         TEXT      NOT NULL,
                booked_by     TEXT      NOT NULL,
                booked_by_id  INTEGER   NOT NULL,
                booking_time  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status        TEXT      DEFAULT 'active',
                FOREIGN KEY (movie_id) REFERENCES movies(id)
            );
        """)

        # Default admin account (admin / admin123)
        cursor.execute(
            "INSERT OR IGNORE INTO admins (username, password, name) VALUES (?, ?, ?)",
            ("admin", self.hash_password("admin123"), "Super Admin"),
        )

        # Default movies
        default_movies = [
            ("Avengers: Endgame", "The epic conclusion to the Infinity Saga. Heroes unite to reverse Thanos's snap.", "2024-07-15 18:00", "Action",    20, 20, 200.0),
            ("Inception",         "A skilled thief enters the dreams of others to steal secrets from their subconscious.", "2024-07-15 20:30", "Sci-Fi",    20, 20, 180.0),
            ("The Dark Knight",   "Batman faces the chaos unleashed by the anarchical Joker in Gotham City.",            "2024-07-16 15:00", "Action",    20, 20, 150.0),
            ("Interstellar",      "A team of explorers travel through a wormhole in space to ensure humanity's survival.", "2024-07-16 19:00", "Sci-Fi",    20, 20, 175.0),
            ("3 Idiots",          "Three friends navigate engineering college while challenging the flawed education system.", "2024-07-17 17:00", "Comedy",    20, 20, 130.0),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO movies (name, details, show_time, genre, total_seats, available_seats, price) VALUES (?,?,?,?,?,?,?)",
            default_movies,
        )
        conn.commit()

        # Generate A1-A10, B1-B10 seats for every movie
        cursor.execute("SELECT id FROM movies")
        movie_ids = [row["id"] for row in cursor.fetchall()]
        seat_numbers = [f"A{i}" for i in range(1, 11)] + [f"B{i}" for i in range(1, 11)]
        for mid in movie_ids:
            for seat in seat_numbers:
                cursor.execute(
                    "INSERT OR IGNORE INTO seats (movie_id, seat_number, is_booked) VALUES (?,?,0)",
                    (mid, seat),
                )
        conn.commit()
        conn.close()
