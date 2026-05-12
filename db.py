import mysql.connector

from config import DB_CONFIG


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


def setup_database():
    """Create database and tables if they don't exist."""
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG.get("port", 3306),
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )

    cursor = conn.cursor()
    db_name = DB_CONFIG["database"]

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        author VARCHAR(255),
        text TEXT,
        source_url VARCHAR(500),
        UNIQUE KEY uq_quote (author(100), text(200))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broker_moves (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        name VARCHAR(255) NOT NULL,
        broker VARCHAR(100) NOT NULL,
        action ENUM('retained', 'upgraded', 'downgraded', 'initiated') NOT NULL,
        rating VARCHAR(50) NOT NULL,
        price_target DECIMAL(10, 2) NOT NULL,
        previous_rating VARCHAR(50),
        previous_price_target DECIMAL(10, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_broker_move (date, symbol, broker),
        INDEX idx_date (date),
        INDEX idx_symbol (symbol),
        INDEX idx_broker (broker)
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("[OK] Database and tables created successfully")


def insert_quotes(rows):
    """
    rows: list of dicts with keys: author, text, source_url (optional)
    Dedup handled by UNIQUE KEY uq_quotes via ON DUPLICATE KEY.
    """
    conn = get_conn()
    cur = conn.cursor()

    sql = """
    INSERT INTO quotes (author, text, source_url)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
      source_url = COALESCE(VALUES(source_url), source_url)
    """

    data = [(r["author"], r["text"], r.get("source_url")) for r in rows]
    cur.executemany(sql, data)

    conn.commit()
    cur.close()
    conn.close()


def insert_jobs(rows):
    """
    rows: list of dicts with keys:
      source_site, job_url, title, company, location, posted_date, description
    Dedup handled by UNIQUE KEY uq_job_url via ON DUPLICATE KEY.
    """
    conn = get_conn()
    cur = conn.cursor()

    sql = """
    INSERT INTO jobs (source_site, job_url, title, company, location, posted_date, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      title = VALUES(title),
      company = VALUES(company),
      location = VALUES(location),
      posted_date = VALUES(posted_date),
      description = VALUES(description)
    """

    data = [
        (
            r["source_site"],
            r["job_url"],
            r["title"],
            r.get("company"),
            r.get("location"),
            r.get("posted_date"),
            r.get("description"),
        )
        for r in rows
    ]

    cur.executemany(sql, data)

    conn.commit()
    cur.close()
    conn.close()


def insert_broker_moves(date: str, moves: list):
    """
    Insert broker moves into the database.

    Args:
        date: Date string in YYYY-MM-DD format
        moves: List of broker move dicts with keys:
            symbol, name, broker, action, rating, price_target,
            previous_rating (optional), previous_price_target (optional)

    Returns:
        Number of rows inserted/updated
    """
    if not moves:
        return 0

    conn = get_conn()
    cur = conn.cursor()

    sql = """
    INSERT INTO broker_moves
        (date, symbol, name, broker, action, rating, price_target, previous_rating, previous_price_target)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        action = VALUES(action),
        rating = VALUES(rating),
        price_target = VALUES(price_target),
        previous_rating = VALUES(previous_rating),
        previous_price_target = VALUES(previous_price_target)
    """

    data = [
        (
            date,
            m["symbol"],
            m["name"],
            m["broker"],
            m["action"],
            m["rating"],
            m["price_target"],
            m.get("previous_rating"),
            m.get("previous_price_target"),
        )
        for m in moves
    ]

    cur.executemany(sql, data)
    affected = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return affected


def get_broker_moves(symbol: str = None, date: str = None, days: int = None):
    """
    Query broker moves from the database.

    Args:
        symbol: Filter by stock symbol (optional)
        date: Filter by specific date YYYY-MM-DD (optional)
        days: Get moves from last N days (optional)

    Returns:
        List of broker move records
    """
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    sql = "SELECT * FROM broker_moves WHERE 1=1"
    params = []

    if symbol:
        sql += " AND symbol = %s"
        params.append(symbol)

    if date:
        sql += " AND date = %s"
        params.append(date)
    elif days:
        sql += " AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
        params.append(days)

    sql += " ORDER BY date DESC, symbol ASC, broker ASC"

    cur.execute(sql, params)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results
