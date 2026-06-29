from abc import ABC, abstractmethod
from database import Database


# ══════════════════════════════════════════════════════════════════════════════
# ABSTRACTION  — Abstract Base Classes define the contract; subclasses must
#               implement every @abstractmethod or Python raises TypeError.
# ══════════════════════════════════════════════════════════════════════════════

class BaseAuth(ABC):
    """
    Abstract contract for any entity that can authenticate.
    Forces Admin and User to implement: login(), get_role(), __str__()
    """

    def __init__(self, db: Database):
        self.db = db  # shared dependency injected into every subclass

    @abstractmethod
    def login(self, username: str, password: str):
        """Verify credentials against the database; return row-dict or None."""
        pass

    @abstractmethod
    def get_role(self) -> str:
        """Return the string label used in the bookings table ('admin'/'user')."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Human-readable description of this authenticator type."""
        pass


class BaseRecord(ABC):
    """
    Abstract contract for any database entity that supports read operations.
    Forces Movie and Booking to implement: get_all(), get_by_id()
    """

    def __init__(self, db: Database):
        self.db = db

    @abstractmethod
    def get_all(self) -> list:
        """Return all rows for this entity as a list of dicts."""
        pass

    @abstractmethod
    def get_by_id(self, record_id) -> dict | None:
        """Return a single row by primary-key / unique identifier."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# INHERITANCE + POLYMORPHISM
#   Admin  ──▶  BaseAuth    (overrides login, get_role, __str__)
#   User   ──▶  BaseAuth    (overrides login, get_role, __str__)
#   Movie  ──▶  BaseRecord  (overrides get_all, get_by_id, __str__)
#   Booking──▶  BaseRecord  (overrides get_all, get_by_id, __str__)
#
# Polymorphism: the same method name (e.g. login / get_all) behaves
# differently depending on which concrete class is called at runtime.
# ══════════════════════════════════════════════════════════════════════════════

class Admin(BaseAuth):
    """
    Concrete admin authenticator.
    POLYMORPHISM: login() queries the 'admins' table; get_role() returns 'admin'.
    """

    # ── Polymorphic override ──────────────────────────────────────────────────
    def login(self, username: str, password: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (username, self.db.hash_password(password)),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_role(self) -> str:
        return "admin"

    # ── Polymorphic override ──────────────────────────────────────────────────
    def __str__(self) -> str:
        return "Admin Portal"

    # ── Admin-specific behaviour ──────────────────────────────────────────────
    def add_movie(self, name: str, details: str, show_time: str, genre: str, price: float):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO movies (name, details, show_time, genre, total_seats, available_seats, price) VALUES (?,?,?,?,20,20,?)",
            (name, details, show_time, genre, price),
        )
        movie_id = cursor.lastrowid
        seat_numbers = [f"A{i}" for i in range(1, 11)] + [f"B{i}" for i in range(1, 11)]
        for seat in seat_numbers:
            cursor.execute("INSERT INTO seats (movie_id, seat_number) VALUES (?,?)", (movie_id, seat))
        conn.commit()
        conn.close()
        return movie_id


class User(BaseAuth):
    """
    Concrete customer authenticator.
    POLYMORPHISM: login() queries the 'users' table; get_role() returns 'user'.
    """

    # ── Polymorphic override ──────────────────────────────────────────────────
    def login(self, username: str, password: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, self.db.hash_password(password)),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_role(self) -> str:
        return "user"

    # ── Polymorphic override ──────────────────────────────────────────────────
    def __str__(self) -> str:
        return "Customer Portal"

    # ── User-specific behaviour ───────────────────────────────────────────────
    def signup(self, username: str, password: str, name: str, phone: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, name, phone) VALUES (?,?,?,?)",
                (username, self.db.hash_password(password), name, phone),
            )
            conn.commit()
            return True, "Account created successfully!"
        except Exception as exc:
            msg = "Username already exists!" if "UNIQUE" in str(exc) else str(exc)
            return False, msg
        finally:
            conn.close()

    def get_bookings(self, user_id: int) -> list:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.*, m.name AS movie_name, m.show_time, m.price
            FROM bookings b
            JOIN movies m ON b.movie_id = m.id
            WHERE b.booked_by='user' AND b.booked_by_id=?
            ORDER BY b.booking_time DESC
            """,
            (user_id,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


class Movie(BaseRecord):
    """
    Concrete record class for movies.
    POLYMORPHISM: get_all() returns movie rows; get_by_id() looks up movies table.
    """

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_all(self) -> list:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies ORDER BY show_time")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_by_id(self, record_id: int) -> dict | None:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id=?", (record_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ── Polymorphic override ──────────────────────────────────────────────────
    def __str__(self) -> str:
        return "Movie Catalog"

    # ── Movie-specific behaviour ──────────────────────────────────────────────
    def get_seats(self, movie_id: int) -> list:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM seats WHERE movie_id=? ORDER BY seat_number",
            (movie_id,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


class Booking(BaseRecord):
    """
    Concrete record class for bookings.
    POLYMORPHISM: get_all() returns booking rows joined with movies;
                  get_by_id() accepts a ticket_id string (not an int PK).
    """

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_all(self) -> list:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.*, m.name AS movie_name, m.show_time, m.price
            FROM bookings b
            JOIN movies m ON b.movie_id = m.id
            ORDER BY b.booking_time DESC
            """
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    # ── Polymorphic override ──────────────────────────────────────────────────
    def get_by_id(self, record_id: str) -> dict | None:
        """Accepts ticket_id string (e.g. 'TKT-ABC12345') as the identifier."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.*, m.name AS movie_name, m.show_time, m.price
            FROM bookings b
            JOIN movies m ON b.movie_id = m.id
            WHERE b.ticket_id=?
            """,
            (record_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ── Polymorphic override ──────────────────────────────────────────────────
    def __str__(self) -> str:
        return "Booking Records"

    # ── Booking-specific behaviour ────────────────────────────────────────────
    def book_ticket(self, movie_id: int, seat_number: str, customer_name: str,
                    phone: str, booked_by: str, booked_by_id: int):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_booked FROM seats WHERE movie_id=? AND seat_number=?",
            (movie_id, seat_number),
        )
        seat = cursor.fetchone()
        if not seat or seat["is_booked"]:
            conn.close()
            return False, "Seat is already booked!"
        ticket_id = self.db.generate_ticket_id()
        try:
            cursor.execute(
                "INSERT INTO bookings (ticket_id, movie_id, seat_number, customer_name, phone, booked_by, booked_by_id) VALUES (?,?,?,?,?,?,?)",
                (ticket_id, movie_id, seat_number, customer_name, phone, booked_by, booked_by_id),
            )
            cursor.execute(
                "UPDATE seats SET is_booked=1 WHERE movie_id=? AND seat_number=?",
                (movie_id, seat_number),
            )
            cursor.execute(
                "UPDATE movies SET available_seats = available_seats - 1 WHERE id=?",
                (movie_id,),
            )
            conn.commit()
            return True, ticket_id
        except Exception as exc:
            return False, str(exc)
        finally:
            conn.close()

    def cancel_ticket(self, ticket_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bookings WHERE ticket_id=? AND status='active'",
            (ticket_id,),
        )
        booking = cursor.fetchone()
        if not booking:
            conn.close()
            return False, "Ticket not found or already cancelled!"
        booking = dict(booking)
        try:
            cursor.execute("UPDATE bookings SET status='cancelled' WHERE ticket_id=?", (ticket_id,))
            cursor.execute(
                "UPDATE seats SET is_booked=0 WHERE movie_id=? AND seat_number=?",
                (booking["movie_id"], booking["seat_number"]),
            )
            cursor.execute(
                "UPDATE movies SET available_seats = available_seats + 1 WHERE id=?",
                (booking["movie_id"],),
            )
            conn.commit()
            return True, "Ticket cancelled successfully!"
        except Exception as exc:
            return False, str(exc)
        finally:
            conn.close()
