import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3

# ---------------- Database setup & migration ----------------
conn = sqlite3.connect("bus_booking.db")
cursor = conn.cursor()

# Create / migrate users table to include role
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
""")
# Add role column if missing
cursor.execute("PRAGMA table_info(users)")
cols = [c[1] for c in cursor.fetchall()]
if "role" not in cols:
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

# Create buses table
cursor.execute('''
CREATE TABLE IF NOT EXISTS buses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_name TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    time TEXT NOT NULL,
    price REAL NOT NULL
)
''')

# Create bookings table
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bus_id INTEGER,
    seat_no INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(bus_id) REFERENCES buses(id)
)
''')

# ensure default admin exists
cursor.execute("SELECT * FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin", "admin"))

# seed some buses if none
cursor.execute("SELECT COUNT(*) FROM buses")
if cursor.fetchone()[0] == 0:
    sample_buses = [
        ("Victory Liner", "Manila", "Baguio", "07:00 AM", 650),
        ("Five Star", "Manila", "Pampanga", "09:00 AM", 250),
        ("DLTB Co.", "Batangas", "Manila", "06:30 AM", 300),
        ("Philtranco", "Manila", "Legazpi", "08:00 PM", 900),
        ("Ceres Liner", "Cebu", "Dumaguete", "01:00 PM", 400),
    ]
    cursor.executemany("INSERT INTO buses (bus_name, origin, destination, time, price) VALUES (?, ?, ?, ?, ?)", sample_buses)
conn.commit()

# ---------------- Application ----------------
class BusBookingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bus Booking System")
        self.root.geometry("1000x700")
        self.current_user = None  # (id, username, role)
        self.login_screen()

    # ----- Login / Register (single screen) -----
    def login_screen(self):
        self.clear_root()
        frame = tk.Frame(self.root, pady=20)
        frame.pack(expand=True)

        tk.Label(frame, text="🚌 Bus Booking System", font=("Arial", 28, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        tk.Label(frame, text="Username:", font=("Arial", 14)).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.username_entry = tk.Entry(frame, font=("Arial", 14))
        self.username_entry.grid(row=1, column=1, padx=6, pady=6)

        tk.Label(frame, text="Password:", font=("Arial", 14)).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.password_entry = tk.Entry(frame, show="*", font=("Arial", 14))
        self.password_entry.grid(row=2, column=1, padx=6, pady=6)

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=12)
        tk.Button(btn_frame, text="Login", width=14, bg="#2e7d32", fg="white", command=self.handle_login).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Register", width=14, bg="#1565c0", fg="white", command=self.handle_register).pack(side="left", padx=8)

        # hint
        tk.Label(frame, text="(default admin: admin / admin)", fg="gray").grid(row=4, column=0, columnspan=2, pady=6)

    def handle_login(self):
        user = self.username_entry.get().strip()
        pw = self.password_entry.get().strip()
        if not user or not pw:
            messagebox.showwarning("Input", "Enter username and password.")
            return
        cursor.execute("SELECT id, username, role FROM users WHERE username=? AND password=?", (user, pw))
        row = cursor.fetchone()
        if not row:
            messagebox.showerror("Login Failed", "Invalid credentials.")
            return
        self.current_user = row  # (id, username, role)
        # route to admin or user dashboard
        if row[2] == "admin":
            self.open_admin_dashboard()
        else:
            self.open_user_dashboard()

    def handle_register(self):
        user = self.username_entry.get().strip()
        pw = self.password_entry.get().strip()
        if not user or not pw:
            messagebox.showwarning("Input", "Enter username and password.")
            return
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (user, pw, "user"))
            conn.commit()
            messagebox.showinfo("Registered", "Account created. Please login.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

    # ----- Admin Dashboard (separate UI) -----
    def open_admin_dashboard(self):
        self.clear_root()
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text=f"Admin Dashboard — {self.current_user[1]}", font=("Arial", 16, "bold")).pack(side="left")
        tk.Button(top, text="Logout", bg="#c62828", fg="white", command=self.logout).pack(side="right", padx=6)
        tk.Button(top, text="View All Bookings", bg="#6a1b9a", fg="white", command=self.admin_show_all_bookings).pack(side="right", padx=6)

        # Admin panel: buses Treeview + controls
        mid = tk.Frame(self.root)
        mid.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(mid)
        left.pack(side="left", fill="both", expand=True, padx=(0,8))

        tk.Label(left, text="Buses", font=("Arial", 14, "bold")).pack(anchor="w")
        self.admin_tree = ttk.Treeview(left, columns=("id","bus_name","origin","destination","time","price"), show="headings")
        for col in self.admin_tree["columns"]:
            self.admin_tree.heading(col, text=col.title())
            self.admin_tree.column(col, width=120, anchor="center")
        self.admin_tree.pack(fill="both", expand=True, pady=8)

        # Admin controls (add/edit/delete)
        ctrl = tk.Frame(left)
        ctrl.pack(fill="x", pady=6)
        tk.Button(ctrl, text="Add Bus", bg="#2e7d32", fg="white", command=self.admin_add_bus).pack(side="left", padx=6)
        tk.Button(ctrl, text="Edit Selected", bg="#f9a825", command=self.admin_edit_bus).pack(side="left", padx=6)
        tk.Button(ctrl, text="Delete Selected", bg="#c62828", fg="white", command=self.admin_delete_bus).pack(side="left", padx=6)
        tk.Button(ctrl, text="Refresh", command=self.admin_load_buses).pack(side="left", padx=6)

        # Right: quick search for buses for admin convenience
        right = tk.Frame(mid, width=320)
        right.pack(side="right", fill="y")
        tk.Label(right, text="Search Buses (admin view)", font=("Arial", 12)).pack(anchor="w", pady=(0,6))
        tk.Label(right, text="From:").pack(anchor="w")
        self.ad_from = tk.Entry(right); self.ad_from.pack(fill="x", pady=2)
        tk.Label(right, text="To:").pack(anchor="w")
        self.ad_to = tk.Entry(right); self.ad_to.pack(fill="x", pady=2)
        tk.Button(right, text="Search", command=self.admin_search_buses).pack(pady=6)
        tk.Button(right, text="Show All", command=self.admin_load_buses).pack()
        self.admin_load_buses()

    def admin_load_buses(self):
        cursor.execute("SELECT * FROM buses")
        rows = cursor.fetchall()
        self.admin_tree.delete(*self.admin_tree.get_children())
        for r in rows:
            self.admin_tree.insert("", "end", values=r)

    def admin_search_buses(self):
        o = self.ad_from.get().strip()
        d = self.ad_to.get().strip()
        q = "SELECT * FROM buses WHERE 1=1"
        params=[]
        if o:
            q += " AND origin LIKE ?"; params.append(f"%{o}%")
        if d:
            q += " AND destination LIKE ?"; params.append(f"%{d}%")
        cursor.execute(q, params)
        rows = cursor.fetchall()
        self.admin_tree.delete(*self.admin_tree.get_children())
        for r in rows:
            self.admin_tree.insert("", "end", values=r)

    def admin_add_bus(self):
        win = tk.Toplevel(self.root); win.title("Add Bus"); win.geometry("420x260")
        frm = tk.Frame(win, padx=10, pady=10); frm.pack(fill="both", expand=True)
        tk.Label(frm, text="Bus Name:").grid(row=0,column=0,sticky="e"); bn=tk.Entry(frm); bn.grid(row=0,column=1)
        tk.Label(frm, text="Origin:").grid(row=1,column=0,sticky="e"); o=tk.Entry(frm); o.grid(row=1,column=1)
        tk.Label(frm, text="Destination:").grid(row=2,column=0,sticky="e"); d=tk.Entry(frm); d.grid(row=2,column=1)
        tk.Label(frm, text="Time:").grid(row=3,column=0,sticky="e"); t=tk.Entry(frm); t.grid(row=3,column=1)
        tk.Label(frm, text="Price:").grid(row=4,column=0,sticky="e"); p=tk.Entry(frm); p.grid(row=4,column=1)
        def add():
            name=o2=dest=time=price=None
            name = bn.get().strip(); o2 = o.get().strip(); dest = d.get().strip(); time = t.get().strip(); price = p.get().strip()
            if not (name and o2 and dest and time and price):
                messagebox.showwarning("Input","Fill all fields", parent=win); return
            try:
                cursor.execute("INSERT INTO buses (bus_name, origin, destination, time, price) VALUES (?, ?, ?, ?, ?)",
                               (name, o2, dest, time, float(price)))
                conn.commit()
                messagebox.showinfo("Added","Bus added", parent=win)
                win.destroy()
                self.admin_load_buses()
            except ValueError:
                messagebox.showerror("Error","Price must be a number", parent=win)
        tk.Button(frm, text="Add Bus", bg="#2e7d32", fg="white", command=add).grid(row=5,column=0,columnspan=2,pady=10)

    def admin_edit_bus(self):
        sel = self.admin_tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a bus to edit"); return
        vals = self.admin_tree.item(sel[0],"values")
        bus_id = vals[0]
        # prompts
        new_name = simpledialog.askstring("Edit", "Bus Name:", initialvalue=vals[1], parent=self.root)
        if new_name is None: return
        new_origin = simpledialog.askstring("Edit", "Origin:", initialvalue=vals[2], parent=self.root)
        if new_origin is None: return
        new_dest = simpledialog.askstring("Edit", "Destination:", initialvalue=vals[3], parent=self.root)
        if new_dest is None: return
        new_time = simpledialog.askstring("Edit", "Time:", initialvalue=vals[4], parent=self.root)
        if new_time is None: return
        new_price = simpledialog.askstring("Edit", "Price:", initialvalue=str(vals[5]), parent=self.root)
        if new_price is None: return
        try:
            cursor.execute("UPDATE buses SET bus_name=?, origin=?, destination=?, time=?, price=? WHERE id=?",
                           (new_name.strip(), new_origin.strip(), new_dest.strip(), new_time.strip(), float(new_price), bus_id))
            conn.commit()
            messagebox.showinfo("Updated","Bus updated")
            self.admin_load_buses()
        except ValueError:
            messagebox.showerror("Error","Price must be numeric")

    def admin_delete_bus(self):
        sel = self.admin_tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a bus to delete"); return
        bus_id = self.admin_tree.item(sel[0],"values")[0]
        if messagebox.askyesno("Confirm","Delete bus and its bookings?"):
            cursor.execute("DELETE FROM bookings WHERE bus_id=?", (bus_id,))
            cursor.execute("DELETE FROM buses WHERE id=?", (bus_id,))
            conn.commit()
            messagebox.showinfo("Deleted","Bus deleted (and bookings removed)")
            self.admin_load_buses()

    def admin_show_all_bookings(self):
        win = tk.Toplevel(self.root); win.title("All Bookings"); win.geometry("900x500")
        tree = ttk.Treeview(win, columns=("booking_id","username","bus_name","origin","destination","time","seat_no","price"), show="headings")
        headings = [("booking_id","Booking ID"),("username","User"),("bus_name","Bus"),
                    ("origin","Origin"),("destination","Destination"),("time","Time"),
                    ("seat_no","Seat No"),("price","Price")]
        for col,hd in headings:
            tree.heading(col, text=hd); tree.column(col, width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        cursor.execute('''SELECT bk.id, u.username, b.bus_name, b.origin, b.destination, b.time, bk.seat_no, b.price
                          FROM bookings bk
                          JOIN users u ON bk.user_id = u.id
                          JOIN buses b ON bk.bus_id = b.id
                          ORDER BY bk.id DESC''')
        for r in cursor.fetchall():
            tree.insert("", "end", values=r)
        # admin may delete a booking
        def delete_booking():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select","Select a booking"); return
            bid = tree.item(sel[0],"values")[0]
            if messagebox.askyesno("Confirm","Delete selected booking?"):
                cursor.execute("DELETE FROM bookings WHERE id=?", (bid,))
                conn.commit()
                tree.delete(sel[0])
                messagebox.showinfo("Deleted","Booking deleted")
        tk.Button(win, text="Delete Selected Booking", bg="#c62828", fg="white", command=delete_booking).pack(pady=6)

    # ----- User Dashboard (separate UI) -----
    def open_user_dashboard(self):
        self.clear_root()
        top = tk.Frame(self.root); top.pack(fill="x", padx=8, pady=8)
        tk.Label(top, text=f"User Dashboard — {self.current_user[1]}", font=("Arial", 16, "bold")).pack(side="left")
        tk.Button(top, text="Logout", bg="#c62828", fg="white", command=self.logout).pack(side="right", padx=6)
        tk.Button(top, text="My Bookings", bg="#6a1b9a", fg="white", command=self.user_view_bookings).pack(side="right", padx=6)

        # Search & bus list
        search_frame = tk.LabelFrame(self.root, text="Search Bus", padx=8, pady=8)
        search_frame.pack(fill="x", padx=12, pady=10)
        tk.Label(search_frame, text="From:").grid(row=0,column=0, padx=4); self.us_from = tk.Entry(search_frame); self.us_from.grid(row=0,column=1, padx=4)
        tk.Label(search_frame, text="To:").grid(row=0,column=2, padx=4); self.us_to = tk.Entry(search_frame); self.us_to.grid(row=0,column=3, padx=4)
        tk.Button(search_frame, text="Search", bg="#2e7d32", fg="white", command=self.user_search_buses).grid(row=0,column=4,padx=6)
        tk.Button(search_frame, text="Show All", bg="#1565c0", fg="white", command=self.user_load_buses).grid(row=0,column=5,padx=6)

        # Treeview for buses
        self.user_tree = ttk.Treeview(self.root, columns=("id","bus_name","origin","destination","time","price"), show="headings")
        for col in self.user_tree["columns"]:
            self.user_tree.heading(col, text=col.title())
            self.user_tree.column(col, width=130, anchor="center")
        self.user_tree.pack(fill="both", expand=True, padx=12, pady=10)

        # Seat dropdown + book button
        bf = tk.Frame(self.root); bf.pack(pady=6)
        tk.Label(bf, text="Seat No:").grid(row=0,column=0,padx=4)
        self.user_seat_var = tk.StringVar()
        self.user_seat_cb = ttk.Combobox(bf, textvariable=self.user_seat_var, values=[str(i) for i in range(1,41)], width=6)
        self.user_seat_cb.grid(row=0,column=1,padx=6)
        tk.Button(bf, text="Book Selected Bus", bg="#ff8f00", command=self.user_book_selected).grid(row=0,column=2,padx=8)

        self.user_load_buses()

    def user_load_buses(self):
        cursor.execute("SELECT * FROM buses")
        rows = cursor.fetchall()
        self.user_tree.delete(*self.user_tree.get_children())
        for r in rows:
            self.user_tree.insert("", "end", values=r)

    def user_search_buses(self):
        o = self.us_from.get().strip(); d = self.us_to.get().strip()
        q="SELECT * FROM buses WHERE 1=1"; params=[]
        if o: q+=" AND origin LIKE ?"; params.append(f"%{o}%")
        if d: q+=" AND destination LIKE ?"; params.append(f"%{d}%")
        cursor.execute(q, params)
        rows = cursor.fetchall()
        self.user_tree.delete(*self.user_tree.get_children())
        for r in rows:
            self.user_tree.insert("", "end", values=r)

    def user_book_selected(self):
        sel = self.user_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a bus to book."); return
        seat = self.user_seat_var.get().strip()
        if not seat:
            messagebox.showwarning("Select", "Choose a seat number."); return
        bus_id = self.user_tree.item(sel[0],"values")[0]
        # check seat taken
        cursor.execute("SELECT * FROM bookings WHERE bus_id=? AND seat_no=?", (bus_id, seat))
        if cursor.fetchone():
            messagebox.showerror("Taken", f"Seat {seat} is already booked on this bus."); return
        # prevent same user duplicating same bus seatless booking (optional)
        cursor.execute("SELECT * FROM bookings WHERE user_id=? AND bus_id=?", (self.current_user[0], bus_id))
        if cursor.fetchone():
            # user already booked this bus (possibly different seat) - allow or block? We'll allow multiple bookings for same bus if desired.
            pass
        cursor.execute("INSERT INTO bookings (user_id, bus_id, seat_no) VALUES (?, ?, ?)", (self.current_user[0], bus_id, int(seat)))
        conn.commit()
        messagebox.showinfo("Booked", f"Seat {seat} booked successfully.")
        self.user_seat_var.set("")

    def user_view_bookings(self):
        win = tk.Toplevel(self.root); win.title("My Bookings"); win.geometry("850x400")
        tree = ttk.Treeview(win, columns=("booking_id","bus_name","origin","destination","time","seat_no","price"), show="headings")
        cols=[("booking_id","Booking ID"),("bus_name","Bus"),("origin","Origin"),("destination","Destination"),
              ("time","Time"),("seat_no","Seat No"),("price","Price")]
        for col,hd in cols:
            tree.heading(col, text=hd); tree.column(col, width=110, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        # load only current user's bookings
        cursor.execute('''SELECT bk.id, b.bus_name, b.origin, b.destination, b.time, bk.seat_no, b.price
                          FROM bookings bk JOIN buses b ON bk.bus_id = b.id
                          WHERE bk.user_id = ? ORDER BY bk.id DESC''', (self.current_user[0],))
        for r in cursor.fetchall():
            tree.insert("", "end", values=r)
        def cancel():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select","Select booking to cancel."); return
            bid = tree.item(sel[0],"values")[0]
            if messagebox.askyesno("Confirm","Cancel selected booking?"):
                cursor.execute("DELETE FROM bookings WHERE id=?", (bid,))
                conn.commit()
                tree.delete(sel[0])
                messagebox.showinfo("Cancelled","Booking cancelled.")
        tk.Button(win, text="Cancel Selected Booking", bg="#c62828", fg="white", command=cancel).pack(pady=6)

    # ----- Utilities -----
    def logout(self):
        self.current_user = None
        self.login_screen()

    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()

# Run app
if __name__ == "__main__":
    root = tk.Tk()
    app = BusBookingApp(root)
    root.mainloop()
