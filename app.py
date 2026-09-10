from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hashlib
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","change-this-secret-in-production")
DB = "money_earn.db"

EASYPAISA_NAME = "Abid Afzal"
EASYPAISA_NUMBER = "03034201512"

TASKS = [
    (1, "Sponsored Offer", "Visit and review the sponsored offer.", 10),
    (2, "Short Survey", "Complete a short survey.", 10),
    (3, "Partner Promotion", "Visit a partner promotion page.", 10),
]

VIP_PLANS = [
    ("VIP 1", 300, "Standard support"),
    ("VIP 2", 600, "Priority task notifications"),
    ("VIP 3", 1000, "Higher sponsored-task capacity when available"),
    ("VIP 4", 1500, "Priority support + task alerts"),
    ("VIP 5", 2500, "Maximum membership features"),
]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      phone TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      coins INTEGER NOT NULL DEFAULT 0,
      referral_code TEXT UNIQUE,
      referred_by TEXT,
      is_admin INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS task_claims(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      task_id INTEGER NOT NULL,
      reward INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL,
      UNIQUE(user_id, task_id)
    );
    CREATE TABLE IF NOT EXISTS payments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      plan TEXT NOT NULL,
      amount INTEGER NOT NULL,
      trx_id TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS withdrawals(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      amount INTEGER NOT NULL,
      easypaisa_number TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL
    );
    """)
    # default admin
    admin = c.execute("SELECT id FROM users WHERE phone=?", ("03000000000",)).fetchone()
    if not admin:
        c.execute("""INSERT INTO users(name,phone,password,coins,referral_code,is_admin,created_at)
                     VALUES(?,?,?,?,?,?,?)""",
                  ("Admin","03000000000",hash_pw("admin123"),0,"ADMIN001",1,datetime.now().isoformat()))
    c.commit(); c.close()

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session: return redirect(url_for("login"))
        return f(*a, **k)
    return w

def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("is_admin"): return redirect(url_for("home"))
        return f(*a, **k)
    return w

@app.route("/")
def home():
    return render_template("home.html", tasks=TASKS, plans=VIP_PLANS,
                           ep_name=EASYPAISA_NAME, ep_number=EASYPAISA_NUMBER)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip()
        phone=request.form["phone"].strip()
        password=request.form["password"]
        referred_by=request.form.get("referral","").strip() or None
        code="ME"+phone[-4:]+str(abs(hash(phone))%1000)
        c=db()
        try:
            c.execute("""INSERT INTO users(name,phone,password,referral_code,referred_by,created_at)
                         VALUES(?,?,?,?,?,?)""",
                      (name,phone,hash_pw(password),code,referred_by,datetime.now().isoformat()))
            c.commit()
            flash("Account created. Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Phone number already registered.")
        finally:
            c.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db()
        u=c.execute("SELECT * FROM users WHERE phone=? AND password=?",
                    (request.form["phone"].strip(),hash_pw(request.form["password"]))).fetchone()
        c.close()
        if u:
            session["uid"]=u["id"]; session["name"]=u["name"]; session["is_admin"]=bool(u["is_admin"])
            return redirect(url_for("dashboard"))
        flash("Invalid login.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    c=db()
    u=c.execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
    claims={r["task_id"]:r["status"] for r in c.execute("SELECT * FROM task_claims WHERE user_id=?",(u["id"],))}
    pays=c.execute("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    withdrawals=c.execute("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    refs=c.execute("SELECT COUNT(*) n FROM users WHERE referred_by=?",(u["referral_code"],)).fetchone()["n"]
    c.close()
    return render_template("dashboard.html", user=u, tasks=TASKS, claims=claims,
                           plans=VIP_PLANS, pays=pays, withdrawals=withdrawals, refs=refs,
                           ep_name=EASYPAISA_NAME, ep_number=EASYPAISA_NUMBER)

@app.route("/claim/<int:task_id>", methods=["POST"])
@login_required
def claim(task_id):
    task=next((t for t in TASKS if t[0]==task_id),None)
    if not task: return "Not found",404
    c=db()
    try:
        c.execute("INSERT INTO task_claims(user_id,task_id,reward,status,created_at) VALUES(?,?,?,?,?)",
                  (session["uid"],task_id,task[3],"pending",datetime.now().isoformat()))
        c.commit(); flash("Task submitted for verification.")
    except sqlite3.IntegrityError:
        flash("Task already submitted.")
    finally: c.close()
    return redirect(url_for("dashboard"))

@app.route("/buy-vip", methods=["POST"])
@login_required
def buy_vip():
    plan=request.form["plan"]
    trx=request.form["trx_id"].strip()
    p=next((x for x in VIP_PLANS if x[0]==plan),None)
    if not p or not trx:
        flash("Select a plan and enter transaction ID.")
        return redirect(url_for("dashboard"))
    c=db()
    c.execute("INSERT INTO payments(user_id,plan,amount,trx_id,status,created_at) VALUES(?,?,?,?,?,?)",
              (session["uid"],p[0],p[1],trx,"pending",datetime.now().isoformat()))
    c.commit(); c.close()
    flash("Membership payment submitted for manual verification.")
    return redirect(url_for("dashboard"))

@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    amount=int(request.form.get("amount","0") or 0)
    number=request.form.get("number","").strip()
    c=db()
    u=c.execute("SELECT coins FROM users WHERE id=?",(session["uid"],)).fetchone()
    if amount < 50:
        flash("Minimum withdrawal is 50 coins.")
    elif amount > u["coins"]:
        flash("Insufficient verified reward balance.")
    elif not number:
        flash("Enter Easypaisa number.")
    else:
        c.execute("INSERT INTO withdrawals(user_id,amount,easypaisa_number,status,created_at) VALUES(?,?,?,?,?)",
                  (session["uid"],amount,number,"pending",datetime.now().isoformat()))
        c.commit(); flash("Withdrawal request submitted.")
    c.close()
    return redirect(url_for("dashboard"))

@app.route("/admin")
@admin_required
def admin():
    c=db()
    claims=c.execute("""SELECT tc.*,u.name,u.phone FROM task_claims tc JOIN users u ON u.id=tc.user_id
                        WHERE tc.status='pending' ORDER BY tc.id DESC""").fetchall()
    pays=c.execute("""SELECT p.*,u.name,u.phone FROM payments p JOIN users u ON u.id=p.user_id
                      WHERE p.status='pending' ORDER BY p.id DESC""").fetchall()
    wd=c.execute("""SELECT w.*,u.name,u.phone FROM withdrawals w JOIN users u ON u.id=w.user_id
                    WHERE w.status='pending' ORDER BY w.id DESC""").fetchall()
    c.close()
    return render_template("admin.html", claims=claims,pays=pays,withdrawals=wd)

@app.route("/admin/task/<int:cid>/<action>", methods=["POST"])
@admin_required
def admin_task(cid,action):
    c=db()
    row=c.execute("SELECT * FROM task_claims WHERE id=?",(cid,)).fetchone()
    if row and row["status"]=="pending":
        status="approved" if action=="approve" else "rejected"
        c.execute("UPDATE task_claims SET status=? WHERE id=?",(status,cid))
        if status=="approved":
            c.execute("UPDATE users SET coins=coins+? WHERE id=?",(row["reward"],row["user_id"]))
        c.commit()
    c.close(); return redirect(url_for("admin"))

@app.route("/admin/payment/<int:pid>/<action>", methods=["POST"])
@admin_required
def admin_payment(pid,action):
    c=db(); status="approved" if action=="approve" else "rejected"
    c.execute("UPDATE payments SET status=? WHERE id=? AND status='pending'",(status,pid))
    c.commit(); c.close(); return redirect(url_for("admin"))

@app.route("/admin/withdraw/<int:wid>/<action>", methods=["POST"])
@admin_required
def admin_withdraw(wid,action):
    c=db(); row=c.execute("SELECT * FROM withdrawals WHERE id=?",(wid,)).fetchone()
    if row and row["status"]=="pending":
        status="approved" if action=="approve" else "rejected"
        if status=="approved":
            u=c.execute("SELECT coins FROM users WHERE id=?",(row["user_id"],)).fetchone()
            if u["coins"] >= row["amount"]:
                c.execute("UPDATE users SET coins=coins-? WHERE id=?",(row["amount"],row["user_id"]))
            else:
                status="rejected"
        c.execute("UPDATE withdrawals SET status=? WHERE id=?",(status,wid))
        c.commit()
    c.close(); return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
