import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from database import Database
from models import Admin, User, Movie, Booking

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MovieBook", page_icon="🎬", layout="wide")

# ── Shared CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .seat-available { background:#22c55e; color:#fff; border-radius:6px;
                      padding:4px 6px; font-size:13px; text-align:center; }
    .seat-booked    { background:#ef4444; color:#fff; border-radius:6px;
                      padding:4px 6px; font-size:13px; text-align:center; }
    .ticket-card    { border:1px solid #e2e8f0; border-radius:10px;
                      padding:16px; margin-bottom:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Singletons ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return Database(os.path.join(os.path.dirname(__file__), "movie_tickets.db"))

db            = get_db()
admin_model   = Admin(db)
user_model    = User(db)
movie_model   = Movie(db)
booking_model = Booking(db)

# ── Session defaults ──────────────────────────────────────────────────────────
for key, val in {"logged_in": False, "user_type": None, "user_data": None, "page": "home"}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Helpers ───────────────────────────────────────────────────────────────────
def logout():
    for key in ("logged_in", "user_type", "user_data"):
        st.session_state[key] = None if key != "logged_in" else False
    st.session_state.page = "home"
    st.rerun()


def goto(page: str):
    st.session_state.page = page
    st.rerun()


def render_seat_map(seats: list):
    """Render a visual A1-A10 / B1-B10 seat grid (read-only display)."""
    seat_map = {s["seat_number"]: s["is_booked"] for s in seats}

    for row_letter in ("A", "B"):
        cols = st.columns(11)
        cols[0].markdown(f"**Row {row_letter}**")
        for i in range(1, 11):
            seat = f"{row_letter}{i}"
            booked = seat_map.get(seat, False)
            label = f"🔴 {seat}" if booked else f"🟢 {seat}"
            cols[i].markdown(
                f"<div class='{'seat-booked' if booked else 'seat-available'}'>{seat}</div>",
                unsafe_allow_html=True,
            )
    st.caption("🟢 Available  &nbsp;&nbsp;  🔴 Booked")


def book_ticket_form(movie_options: dict, actor: str, actor_id: int, extra_fields: bool = False):
    """Shared booking form used by both Admin and User screens."""
    if not movie_options:
        st.warning("No movies with available seats.")
        return

    selected_label = st.selectbox("Select Movie", list(movie_options.keys()), key=f"sel_movie_{actor}")
    movie_id       = movie_options[selected_label]
    seats          = movie_model.get_seats(movie_id)
    movie_info     = movie_model.get_by_id(movie_id)

    st.markdown("#### Seat Map")
    render_seat_map(seats)

    available = [s["seat_number"] for s in seats if not s["is_booked"]]

    if not available:
        st.error("All seats are booked for this show.")
        return

    st.markdown(f"**Ticket price: ₹{movie_info['price']}**")

    with st.form(f"book_form_{actor}"):
        selected_seat = st.selectbox("Choose Seat", available)

        if extra_fields:
            cust_name = st.text_input("Customer Name")
            cust_phone = st.text_input("Customer Phone")
        else:
            cust_name  = st.session_state.user_data["name"]
            cust_phone = st.session_state.user_data["phone"]
            st.info(f"Booking as: **{cust_name}** | Phone: **{cust_phone}**")

        submitted = st.form_submit_button("🎟️ Confirm Booking", use_container_width=True)
        if submitted:
            if extra_fields and (not cust_name or not cust_phone):
                st.error("Customer name and phone are required.")
                return
            ok, result = booking_model.book_ticket(
                movie_id, selected_seat, cust_name, cust_phone, actor, actor_id
            )
            if ok:
                st.success(f"Booking confirmed! **Ticket ID: {result}**")
                if actor == "user":
                    st.balloons()
            else:
                st.error(result)


# ═════════════════════════════════════════════════════════════════════════════
# HOME
# ═════════════════════════════════════════════════════════════════════════════
def page_home():
    st.title("🎬 MovieBook — Online Ticket Booking")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 👤 Customer Portal")
        st.write("Browse movies, book seats, and manage your tickets.")
        if st.button("Customer Login / Sign Up", use_container_width=True):
            goto("customer_auth")
    with c2:
        st.markdown("### 🔑 Admin Portal")
        st.write("Manage movies, view all bookings, and assist customers.")
        if st.button("Admin Login", use_container_width=True):
            goto("admin_auth")


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN AUTH
# ═════════════════════════════════════════════════════════════════════════════
def page_admin_auth():
    st.title("🔑 Admin Login")
    st.caption("Default credentials: **admin** / **admin123**")

    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            admin = admin_model.login(username, password)
            if admin:
                st.session_state.logged_in = True
                st.session_state.user_type  = "admin"
                st.session_state.user_data  = admin
                goto("admin_dashboard")
            else:
                st.error("Invalid credentials.")

    if st.button("← Back"):
        goto("home")


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOMER AUTH
# ═════════════════════════════════════════════════════════════════════════════
def page_customer_auth():
    st.title("👤 Customer Portal")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("user_login"):
            uname = st.text_input("Username", key="l_user")
            pwd   = st.text_input("Password", type="password", key="l_pass")
            if st.form_submit_button("Login", use_container_width=True):
                user = user_model.login(uname, pwd)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_type  = "user"
                    st.session_state.user_data  = user
                    goto("user_dashboard")
                else:
                    st.error("Invalid username or password.")

    with signup_tab:
        with st.form("user_signup"):
            full_name = st.text_input("Full Name")
            uname     = st.text_input("Username", key="s_user")
            phone     = st.text_input("Phone Number")
            pwd       = st.text_input("Password", type="password", key="s_pass")
            cpwd      = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Account", use_container_width=True):
                if pwd != cpwd:
                    st.error("Passwords do not match.")
                elif not all([full_name, uname, phone, pwd]):
                    st.error("All fields are required.")
                else:
                    ok, msg = user_model.signup(uname, pwd, full_name, phone)
                    st.success(msg) if ok else st.error(msg)

    if st.button("← Back"):
        goto("home")


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
def page_admin_dashboard():
    admin = st.session_state.user_data

    hdr_l, hdr_r = st.columns([4, 1])
    hdr_l.title(f"🔑 Admin Dashboard — {admin['name']}")
    if hdr_r.button("Logout"):
        logout()

    st.markdown("---")
    tab_movies, tab_book, tab_all, tab_add = st.tabs(
        ["🎥 Movies", "🎟️ Book Ticket", "📋 All Bookings", "➕ Add Movie"]
    )

    # ── Movies ────────────────────────────────────────────────────────────────
    with tab_movies:
        st.subheader("Current Movies")
        movies = movie_model.get_all()
        for m in movies:
            with st.expander(f"🎬 {m['name']}  |  {m['show_time']}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Genre", m["genre"])
                c2.metric("Seats Available", f"{m['available_seats']}/{m['total_seats']}")
                c3.metric("Price", f"₹{m['price']}")
                st.markdown(f"**About:** {m['details']}")

                seats = movie_model.get_seats(m["id"])
                st.markdown("**Seat Layout:**")
                render_seat_map(seats)

    # ── Book ticket ───────────────────────────────────────────────────────────
    with tab_book:
        st.subheader("Book a Ticket for a Customer")
        movies = movie_model.get_all()
        opts   = {f"{m['name']}  |  {m['show_time']}  (₹{m['price']})": m["id"] for m in movies}
        book_ticket_form(opts, actor="admin", actor_id=admin["id"], extra_fields=True)

    # ── All bookings ──────────────────────────────────────────────────────────
    with tab_all:
        st.subheader("All Bookings")
        all_bookings = booking_model.get_all()

        if not all_bookings:
            st.info("No bookings yet.")
        else:
            f1, f2, f3 = st.columns(3)
            status_f    = f1.selectbox("Status",     ["All", "active", "cancelled"])
            bookedby_f  = f2.selectbox("Booked by",  ["All", "admin", "user"])
            search_name = f3.text_input("Search customer name")

            shown = all_bookings
            if status_f   != "All": shown = [b for b in shown if b["status"]    == status_f]
            if bookedby_f != "All": shown = [b for b in shown if b["booked_by"] == bookedby_f]
            if search_name:         shown = [b for b in shown if search_name.lower() in b["customer_name"].lower()]

            st.markdown(f"**Showing {len(shown)} of {len(all_bookings)} bookings**")

            for b in shown:
                icon  = "🟢" if b["status"] == "active" else "🔴"
                actor = "🔑 Admin" if b["booked_by"] == "admin" else "👤 User"
                with st.expander(f"{icon} {b['ticket_id']}  —  {b['movie_name']}  |  {b['customer_name']}  [{actor}]"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"**Seat:** {b['seat_number']}")
                    c2.markdown(f"**Phone:** {b['phone']}")
                    c3.markdown(f"**Show:** {b['show_time']}")
                    c4.markdown(f"**Price:** ₹{b['price']}")
                    c1.markdown(f"**Status:** `{b['status'].upper()}`")
                    c2.markdown(f"**Booked via:** {actor}")
                    c3.markdown(f"**At:** {b['booking_time']}")

                    if b["status"] == "active":
                        if st.button("Cancel this ticket", key=f"adm_cancel_{b['ticket_id']}"):
                            ok, msg = booking_model.cancel_ticket(b["ticket_id"])
                            st.success(msg) if ok else st.error(msg)
                            st.rerun()

    # ── Add movie ─────────────────────────────────────────────────────────────
    with tab_add:
        st.subheader("Add New Movie")
        with st.form("add_movie"):
            name      = st.text_input("Movie Name")
            details   = st.text_area("Movie Description")
            show_time = st.text_input("Show Date & Time (YYYY-MM-DD HH:MM)", placeholder="2024-08-01 18:00")
            genre     = st.selectbox("Genre", ["Action", "Comedy", "Drama", "Sci-Fi", "Horror", "Romance", "Thriller", "Animation"])
            price     = st.number_input("Ticket Price (₹)", min_value=50.0, value=150.0, step=10.0)
            if st.form_submit_button("Add Movie", use_container_width=True):
                if not all([name, details, show_time]):
                    st.error("Name, description and show time are required.")
                else:
                    new_admin = Admin(db)
                    mid = new_admin.add_movie(name, details, show_time, genre, price)
                    st.success(f"'{name}' added! (Movie ID: {mid}, 20 seats A1-A10 & B1-B10 created)")


# ═════════════════════════════════════════════════════════════════════════════
# USER DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
def page_user_dashboard():
    user = st.session_state.user_data

    hdr_l, hdr_r = st.columns([4, 1])
    hdr_l.title(f"🎬 MovieBook — Hi, {user['name']}!")
    if hdr_r.button("Logout"):
        logout()

    st.markdown("---")
    tab_browse, tab_book, tab_mybookings, tab_cancel = st.tabs(
        ["🎥 Browse Movies", "🎟️ Book Ticket", "📋 My Bookings", "❌ Cancel Ticket"]
    )

    # ── Browse ────────────────────────────────────────────────────────────────
    with tab_browse:
        st.subheader("Now Showing")
        movies = movie_model.get_all()
        for m in movies:
            badge = "✅ Available" if m["available_seats"] > 0 else "❌ Sold Out"
            with st.expander(f"🎬 {m['name']}  |  {m['show_time']}  — {badge}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Genre", m["genre"])
                c2.metric("Seats Left", f"{m['available_seats']}/{m['total_seats']}")
                c3.metric("Price", f"₹{m['price']}")
                st.markdown(f"**About:** {m['details']}")

                seats = movie_model.get_seats(m["id"])
                st.markdown("**Seat Layout:**")
                render_seat_map(seats)

    # ── Book ──────────────────────────────────────────────────────────────────
    with tab_book:
        st.subheader("Book a Ticket")
        movies = movie_model.get_all()
        opts   = {
            f"{m['name']}  |  {m['show_time']}  (₹{m['price']})": m["id"]
            for m in movies
            if m["available_seats"] > 0
        }
        book_ticket_form(opts, actor="user", actor_id=user["id"], extra_fields=False)

    # ── My bookings ───────────────────────────────────────────────────────────
    with tab_mybookings:
        st.subheader("My Bookings")
        my_bookings = user_model.get_bookings(user["id"])

        if not my_bookings:
            st.info("You have no bookings yet. Head to 'Book Ticket' to get started!")
        else:
            active   = [b for b in my_bookings if b["status"] == "active"]
            inactive = [b for b in my_bookings if b["status"] == "cancelled"]

            if active:
                st.markdown("#### Active Tickets")
                for b in active:
                    with st.expander(f"🟢 {b['ticket_id']}  —  {b['movie_name']}"):
                        c1, c2 = st.columns(2)
                        c1.markdown(f"**Seat:** {b['seat_number']}")
                        c2.markdown(f"**Show:** {b['show_time']}")
                        c1.markdown(f"**Price:** ₹{b['price']}")
                        c2.markdown(f"**Booked At:** {b['booking_time']}")

            if inactive:
                st.markdown("#### Cancelled Tickets")
                for b in inactive:
                    with st.expander(f"🔴 {b['ticket_id']}  —  {b['movie_name']}"):
                        c1, c2 = st.columns(2)
                        c1.markdown(f"**Seat:** {b['seat_number']}")
                        c2.markdown(f"**Show:** {b['show_time']}")
                        c1.markdown(f"**Status:** Cancelled")
                        c2.markdown(f"**Booked At:** {b['booking_time']}")

    # ── Cancel ────────────────────────────────────────────────────────────────
    with tab_cancel:
        st.subheader("Cancel a Ticket")
        with st.form("cancel_form"):
            ticket_id = st.text_input("Enter your Ticket ID", placeholder="TKT-XXXXXXXX")
            if st.form_submit_button("Cancel Ticket", use_container_width=True):
                if not ticket_id.strip():
                    st.error("Please enter a ticket ID.")
                else:
                    booking = booking_model.get_by_id(ticket_id.strip().upper())
                    if not booking:
                        st.error("Ticket not found.")
                    elif booking["booked_by"] != "user" or booking["booked_by_id"] != user["id"]:
                        st.error("This ticket does not belong to your account.")
                    elif booking["status"] == "cancelled":
                        st.warning("This ticket is already cancelled.")
                    else:
                        ok, msg = booking_model.cancel_ticket(ticket_id.strip().upper())
                        st.success(msg) if ok else st.error(msg)


# ═════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═════════════════════════════════════════════════════════════════════════════
def main():
    page = st.session_state.page

    if page == "home":
        page_home()
    elif page == "admin_auth":
        page_admin_auth()
    elif page == "customer_auth":
        page_customer_auth()
    elif page == "admin_dashboard":
        if st.session_state.logged_in and st.session_state.user_type == "admin":
            page_admin_dashboard()
        else:
            goto("home")
    elif page == "user_dashboard":
        if st.session_state.logged_in and st.session_state.user_type == "user":
            page_user_dashboard()
        else:
            goto("home")
    else:
        goto("home")


if __name__ == "__main__":
    main()
