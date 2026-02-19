from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def connect_db():
    return sqlite3.connect("database.db")

@app.route("/")
def home():
    return "SecureBank API Running"

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Email already exists"}), 400

    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                   (name, email, password))
    user_id = cursor.lastrowid

    # Create account with default balance 5000
    cursor.execute("INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
                   (user_id, 5000))

    conn.commit()
    conn.close()

    return jsonify({"message": "User registered successfully"}), 201


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# ---------------- CHECK BALANCE ----------------
@app.route("/balance/<email>", methods=["GET"])
def check_balance(email):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT accounts.balance FROM accounts
        JOIN users ON accounts.user_id = users.id
        WHERE users.email=?
    """, (email,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify({"balance": result[0]}), 200
    else:
        return jsonify({"error": "User not found"}), 404


# ---------------- FUND TRANSFER ----------------
@app.route("/transfer", methods=["POST"])
def transfer():
    data = request.json
    sender_email = data.get("sender_email")
    receiver_email = data.get("receiver_email")
    amount = data.get("amount")

    if amount <= 0:
        return jsonify({"error": "Invalid transfer amount"}), 400

    conn = connect_db()
    cursor = conn.cursor()

    # Get sender
    cursor.execute("SELECT id FROM users WHERE email=?", (sender_email,))
    sender = cursor.fetchone()

    cursor.execute("SELECT id FROM users WHERE email=?", (receiver_email,))
    receiver = cursor.fetchone()

    if not sender or not receiver:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    sender_id = sender[0]
    receiver_id = receiver[0]

    # Check sender balance
    cursor.execute("SELECT balance FROM accounts WHERE user_id=?", (sender_id,))
    sender_balance = cursor.fetchone()[0]

    if sender_balance < amount:
        conn.close()
        return jsonify({"error": "Insufficient balance"}), 400

    # Deduct from sender
    cursor.execute("UPDATE accounts SET balance=balance-? WHERE user_id=?",
                   (amount, sender_id))

    # Add to receiver
    cursor.execute("UPDATE accounts SET balance=balance+? WHERE user_id=?",
                   (amount, receiver_id))

    # Add transaction record
    cursor.execute("""
        INSERT INTO transactions (user_id, receiver_email, amount)
        VALUES (?, ?, ?)
    """, (sender_id, receiver_email, amount))

    conn.commit()
    conn.close()

    return jsonify({"message": "Transfer successful"}), 200


# ---------------- TRANSACTION HISTORY ----------------
@app.route("/transactions/<email>", methods=["GET"])
def transaction_history(email):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT transactions.amount, transactions.date
        FROM transactions
        JOIN users ON transactions.user_id = users.id
        WHERE users.email=?
        ORDER BY transactions.date DESC
    """, (email,))

    data = cursor.fetchall()
    conn.close()

    return jsonify({"transactions": data}), 200


if __name__ == "__main__":
    app.run(debug=True)
