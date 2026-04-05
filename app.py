import sqlite3
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

DF_HEIGHT = 380

BATA_RED = "#E21F26"
BATA_RED_HOVER = "#B3191E"
BATA_BG = "#F8F9FA"
BATA_CHARCOAL = "#212529"

# --- CLEAN BATA DESIGN SYSTEM ---
BATA_RED = "#E21F26"
BATA_BG = "#FFFFFF" 
BATA_CHARCOAL = "#333333"

BATA_CSS = f"""
<style>
    .stApp {{ background-color: {BATA_BG} !important; }}
    section[data-testid="stSidebar"] {{
        background-color: #F8F9FA !important;
        border-right: 2px solid {BATA_RED} !important;
    }}
    div.stButton > button {{
        background-color: {BATA_RED} !important;
        color: white !important;
        border-radius: 4px !important;
        font-weight: bold !important;
        width: 100%;
    }}
    .bata-brand-bar {{
        background: {BATA_RED};
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 1rem;
    }}
    .bata-tile {{
        background: white;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #EEE;
        border-top: 4px solid {BATA_RED};
        text-align: center;
    }}
</style>
"""

def bata_tile_html(label, value, tile_kind):
    color = BATA_RED
    if tile_kind == "net-pos": color = "#28A745"
    return f'<div class="bata-tile" style="border-top-color: {color}"><div style="font-size:0.8rem; color:#666;">{label}</div><div style="font-size:1.5rem; font-weight:bold;">{value}</div></div>'

def style_article_name_column(df, col_name="name"):
    return df # Simplified to prevent layout breaking

def style_article_name_column(df, col_name="name"):
    """Bold dark charcoal for article / name column (catalog)."""

    def _col_style(col):
        if col.name == col_name:
            return [f"font-weight: 700; color: {BATA_CHARCOAL}"] * len(col)
        return [""] * len(col)

    return df.style.apply(_col_style, axis=0)

_ROOT = Path(__file__).resolve().parent
DB = str(_ROOT / "shop_data.db")
SHOP_NAME = "Bhai's Shop Name"


def rs(amount):
    return f"Rs. {round(amount)}"


def receipt_text(data):
    w = 28
    dash = "-" * w
    r = round(data["rate"])
    t = round(data["total"])
    q = data["qty"]
    article = data["item"].replace("\n", " ").strip()
    if len(article) > w - 2:
        article = article[: w - 3] + "…"
    shop = SHOP_NAME[: w - 1] + ("…" if len(SHOP_NAME) > w - 1 else "")
    when = data["when"]
    if len(when) > w:
        when = when[: w - 1] + "…"

    def cen(s):
        s = str(s)
        return s[:w].center(w) if len(s) <= w else (s[: w - 1] + "…")

    return "\n".join(
        [
            dash,
            cen(shop),
            dash,
            cen("RECEIPT"),
            dash,
            cen(when),
            dash,
            cen("Article"),
            cen(article),
            dash,
            cen(f"Qty  {q}"),
            cen(f"Rate Rs.{r}"),
            cen(f"Line  Rs.{r * q}"),
            dash,
            cen(f"TOTAL Rs.{t}"),
            dash,
            cen("Thank you for"),
            cen("shopping!"),
            dash,
        ]
    )


def init_db():
    c = sqlite3.connect(DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            size TEXT,
            color TEXT,
            p_price REAL,
            s_price REAL,
            stock INTEGER
        )"""
    )
    has_sales = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales_history'"
    ).fetchone()
    if not has_sales:
        c.execute(
            """CREATE TABLE sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                total_bill REAL NOT NULL,
                profit REAL NOT NULL,
                timestamp TEXT NOT NULL
            )"""
        )
    else:
        cols = [r[1] for r in c.execute("PRAGMA table_info(sales_history)")]
        if "item_name" not in cols:
            c.execute(
                """CREATE TABLE sales_history__new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    total_bill REAL NOT NULL,
                    profit REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )"""
            )
            if "product_name" in cols:
                try:
                    c.execute(
                        """INSERT INTO sales_history__new
                        (id, item_name, qty, total_bill, profit, timestamp)
                        SELECT id, product_name, quantity, total_price, profit, date
                        FROM sales_history"""
                    )
                except sqlite3.OperationalError:
                    pass
            c.execute("DROP TABLE sales_history")
            c.execute("ALTER TABLE sales_history__new RENAME TO sales_history")
    c.execute(
        """CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )"""
    )
    c.commit()
    c.close()


st.set_page_config(page_title="Bata Style POS", layout="wide", page_icon="👟")
init_db()

st.markdown(BATA_CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="bata-brand-bar"><span class="bata-mark">BATA STYLE</span>'
    '<span class="bata-divider">|</span><span class="bata-sub">AWAIS RETAIL</span></div>',
    unsafe_allow_html=True,
)

PAGE_LABELS = {
    "add": "➕ Add New Article",
    "stock": "📦 Current Stock",
    "manage": "✏️ Edit / Manage",
    "pos": "💰 POS (Sales)",
    "expenses": "☕ Daily Expenses",
    "report": "📊 Sales Report",
    "admin": "⚙️ Admin",
}

st.sidebar.markdown("### 👟 Shoe Shop")
st.sidebar.caption("Navigation")
page = st.sidebar.radio(
    "Section",
    list(PAGE_LABELS.keys()),
    format_func=lambda k: PAGE_LABELS[k],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption("Developed by Muhammad Umer ")

if page == "add":
    st.subheader("Add New Article")
    with st.form("add"):
        name = st.text_input("Article Name/Code")
        brand = st.text_input("Brand")
        size = st.text_input("Size")
        color = st.text_input("Color")
        p_price = st.number_input("Purchase price (p_price)", min_value=0.0, step=1.0, format="%.0f")
        s_price = st.number_input("Sale price (s_price)", min_value=0.0, step=1.0, format="%.0f")
        stock = st.number_input("Stock", min_value=0.0, step=1.0, value=0.0, format="%.0f")
        if st.form_submit_button("Save"):
            conn = sqlite3.connect(DB)
            conn.execute(
                "INSERT INTO inventory (name, brand, size, color, p_price, s_price, stock) VALUES (?,?,?,?,?,?,?)",
                (name, brand, size, color, round(p_price), round(s_price), int(round(stock))),
            )
            conn.commit()
            conn.close()
            st.success("Saved.")
elif page == "stock":
    st.subheader("Current Stock")
    q_search = st.text_input(
        "Search",
        placeholder="Article name/code or brand…",
        key="stock_search_q",
    ).strip()
    cols = ("id", "name", "brand", "size", "color", "p_price", "s_price", "stock")
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM inventory ORDER BY id DESC"
    ).fetchall()
    conn.close()

    if q_search:
        needle = q_search.lower()
        rows = [
            r
            for r in rows
            if needle in (r[1] or "").lower() or needle in (r[2] or "").lower()
        ]

    records = []
    for r in rows:
        d = dict(zip(cols, r))
        stk = int(d["stock"])
        records.append(
            {
                "id": d["id"],
                "name": d["name"],
                "brand": d["brand"],
                "size": d["size"],
                "p_price": rs(d["p_price"]),
                "s_price": rs(d["s_price"]),
                "stock": stk,
                "Alert": (
                    "Out of stock"
                    if stk == 0
                    else ("Low stock (<5)" if stk < 5 else "")
                ),
            }
        )
    df = pd.DataFrame(records)
    if df.empty:
        st.info("No matching articles." if q_search else "No inventory yet.")
    else:
        if (df["stock"] == 0).any():
            st.error("Red rows: out of stock (0).")
        if ((df["stock"] > 0) & (df["stock"] < 5)).any():
            st.warning("Orange rows: stock below 5 units.")
        def highlight_stock(row):
            n = len(row)
            s = row["stock"]
            if s == 0:
                return ["background-color: #ffcdd2; color: #b71c1c"] * n
            if s < 5:
                return ["background-color: #ffe0b2; color: #e65100"] * n
            return [""] * n

        styled = style_article_name_column(df, "name").apply(
            highlight_stock, axis=1
        )
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=DF_HEIGHT,
        )
elif page == "manage":
    st.subheader("Edit / Manage Inventory")
    st.session_state.setdefault("edit_id", None)
    st.session_state.setdefault("pending_delete", None)

    cols = ("id", "name", "brand", "size", "color", "p_price", "s_price", "stock")

    if st.session_state.pending_delete is not None:
        pid = st.session_state.pending_delete
        pname = st.session_state.get("pending_delete_name", "this article")
        st.warning(f'Delete "{pname}" (id {pid})? This cannot be undone.')
        b1, b2 = st.columns(2)
        if b1.button("Yes, delete permanently", type="primary", key="confirm_delete_yes"):
            conn = sqlite3.connect(DB)
            conn.execute("DELETE FROM inventory WHERE id = ?", (pid,))
            conn.commit()
            conn.close()
            if st.session_state.edit_id == pid:
                st.session_state.edit_id = None
            st.session_state.pending_delete = None
            st.session_state.pop("pending_delete_name", None)
            st.success("Article removed from inventory.")
            st.rerun()
        if b2.button("Cancel", key="confirm_delete_no"):
            st.session_state.pending_delete = None
            st.session_state.pop("pending_delete_name", None)
            st.rerun()

    elif st.session_state.edit_id is not None:
        eid = st.session_state.edit_id
        conn = sqlite3.connect(DB)
        row = conn.execute(
            f"SELECT {', '.join(c for c in cols if c != 'id')} FROM inventory WHERE id = ?",
            (eid,),
        ).fetchone()
        conn.close()
        if not row:
            st.session_state.edit_id = None
            st.error("That article no longer exists.")
            st.rerun()
        name, brand, size, color, p_price, s_price, stock = row
        st.markdown(f"##### Editing article **#{eid}**")
        with st.form("edit_article"):
            n = st.text_input("Article Name/Code", value=name or "")
            br = st.text_input("Brand", value=brand or "")
            sz = st.text_input("Size", value=size or "")
            cl = st.text_input("Color", value=color or "")
            pp = st.number_input(
                "Purchase price (p_price)",
                min_value=0.0,
                step=1.0,
                format="%.0f",
                value=float(round(p_price)),
            )
            sp = st.number_input(
                "Sale price (s_price)",
                min_value=0.0,
                step=1.0,
                format="%.0f",
                value=float(round(s_price)),
            )
            stc = st.number_input(
                "Stock",
                min_value=0.0,
                step=1.0,
                format="%.0f",
                value=float(int(stock)),
            )
            save = st.form_submit_button("Save changes")
        if st.button("Cancel editing", key="cancel_edit"):
            st.session_state.edit_id = None
            st.rerun()
        if save:
            conn = sqlite3.connect(DB)
            conn.execute(
                """UPDATE inventory SET name=?, brand=?, size=?, color=?,
                p_price=?, s_price=?, stock=? WHERE id=?""",
                (
                    n,
                    br,
                    sz,
                    cl,
                    round(pp),
                    round(sp),
                    int(round(stc)),
                    eid,
                ),
            )
            conn.commit()
            conn.close()
            st.session_state.edit_id = None
            st.success("Inventory updated.")
            st.rerun()

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM inventory ORDER BY id DESC"
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No articles in inventory yet.")
    else:
        st.markdown("##### All articles")
        for r in rows:
            d = dict(zip(cols, r))
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.write(
                    f"**#{d['id']}** **{d['name']}** · {d['brand'] or '—'} · "
                    f"{rs(d['p_price'])} / {rs(d['s_price'])} · stock **{d['stock']}**"
                )
            with c2:
                if st.button("Edit", key=f"edit_btn_{d['id']}"):
                    st.session_state.edit_id = d["id"]
                    st.session_state.pending_delete = None
                    st.rerun()
            with c3:
                if st.button("Delete", key=f"del_btn_{d['id']}"):
                    st.session_state.pending_delete = d["id"]
                    st.session_state.pending_delete_name = d["name"]
                    st.session_state.edit_id = None
                    st.rerun()
elif page == "pos":
    st.subheader("POS (Sales)")
    st.session_state.setdefault("pos_receipt", None)
    st.session_state.setdefault("pos_receipt_show", False)
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, name, brand, s_price, p_price, stock FROM inventory ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        st.warning("No articles in inventory.")
    else:
        pos_q = st.text_input(
            "Search article (name, code, brand, or #id)",
            placeholder="Type to filter the list…",
            key="pos_article_search",
        ).strip()
        needle = pos_q.lower().strip()
        id_part = needle[1:].strip() if needle.startswith("#") else needle

        def pos_row_match(r):
            if not needle:
                return True
            if id_part.isdigit() and int(id_part) == r[0]:
                return True
            return needle in (r[1] or "").lower() or needle in (r[2] or "").lower()

        filtered = rows if not needle else [r for r in rows if pos_row_match(r)]
        if not filtered:
            st.warning("No articles match your search. Clear or change the search text.")
        else:
            pick = st.selectbox(
                "Article",
                filtered,
                format_func=lambda r: f"#{r[0]} {r[1]} ({r[2]}) — stock {r[5]} — {rs(r[3])}",
            )
            qty = st.number_input(
                "Quantity Sold", min_value=1.0, step=1.0, value=1.0, format="%.0f"
            )
            sid, pname, _, s_price, p_price, stock = pick
            q = int(qty)
            qty_invalid = q > stock
            if qty_invalid:
                st.warning(f"⚠️ Only {stock} pieces available!")
            complete = st.button(
                "Complete Sale",
                type="primary",
                disabled=qty_invalid,
                help="Quantity cannot exceed stock on hand.",
            )
            if complete and not qty_invalid:
                conn = sqlite3.connect(DB)
                cur = conn.execute(
                    "UPDATE inventory SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (q, sid, q),
                )
                if cur.rowcount:
                    sp, pp = round(s_price), round(p_price)
                    total = sp * q
                    profit = (sp - pp) * q
                    sale_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        """INSERT INTO sales_history
                        (item_name, qty, total_bill, profit, timestamp)
                        VALUES (?,?,?,?,?)""",
                        (pname, q, total, profit, sale_ts),
                    )
                    conn.commit()
                    st.session_state.pos_receipt = {
                        "item": pname,
                        "qty": q,
                        "rate": sp,
                        "total": total,
                        "when": sale_ts,
                    }
                    st.session_state.pos_receipt_show = False
                    st.success(f"Sale complete. Total bill: {rs(total)}")
                else:
                    conn.rollback()
                    st.error("Not enough stock.")
                conn.close()
        pr = st.session_state.pos_receipt
        if pr:
            if st.button("Generate Receipt", key="pos_gen_receipt"):
                st.session_state.pos_receipt_show = True
            if st.session_state.pos_receipt_show:
                st.markdown(
                    '<div class="thermal-wrap"><pre class="thermal-receipt">'
                    f"{escape(receipt_text(pr))}"
                    "</pre></div>",
                    unsafe_allow_html=True,
                )
elif page == "expenses":
    st.subheader("Daily Expenses")
    if st.session_state.pop("_expense_saved", False):
        st.success("Expense saved.")
    st.caption("Record shop costs such as rent, bills, tea, supplies, etc.")
    with st.form("expense_form"):
        preset = st.selectbox(
            "Quick type",
            ("Custom", "Rent", "Electric bill", "Tea / refreshments", "Transport", "Supplies"),
        )
        desc_custom = st.text_input("Description", placeholder="What was this for?")
        desc = desc_custom.strip() if preset == "Custom" else preset
        amt = st.number_input("Amount (Rs.)", min_value=0.0, step=1.0, format="%.0f")
        exp_date = st.date_input("Date", value=datetime.now().date())
        submitted = st.form_submit_button("Save expense")
    if submitted:
        if not desc:
            st.error("Please enter a description.")
        else:
            conn = sqlite3.connect(DB)
            conn.execute(
                "INSERT INTO expenses (description, amount, date) VALUES (?,?,?)",
                (desc, round(amt), exp_date.isoformat()),
            )
            conn.commit()
            conn.close()
            st.session_state["_expense_saved"] = True
            st.rerun()

    st.markdown("---")
    st.markdown("##### Recent expenses")
    conn = sqlite3.connect(DB)
    erows = conn.execute(
        "SELECT description, amount, date FROM expenses ORDER BY date DESC, id DESC"
    ).fetchall()
    conn.close()
    if not erows:
        st.caption("No expenses recorded yet.")
    else:
        st.dataframe(
            [
                {"Description": d, "Amount (Rs.)": round(a), "Date": dt}
                for d, a, dt in erows
            ],
            use_container_width=True,
            hide_index=True,
            height=min(DF_HEIGHT, max(120, 36 + 36 * len(erows))),
        )
elif page == "report":
    st.subheader("Sales Report")
    today = date.today()
    period = st.selectbox(
        "Report period",
        (
            "This month",
            "Today",
            "This week",
            "Custom range",
            "All time",
        ),
        help="Sales, expenses, and net profit use this date range.",
    )
    if period == "Today":
        start_d = end_d = today
    elif period == "This week":
        start_d = today - timedelta(days=today.weekday())
        end_d = today
    elif period == "This month":
        start_d = today.replace(day=1)
        end_d = today
    elif period == "All time":
        start_d = date(2000, 1, 1)
        end_d = today
    else:
        c_sd, c_ed = st.columns(2)
        start_d = c_sd.date_input(
            "Start date", value=today.replace(day=1), key="rep_range_start"
        )
        end_d = c_ed.date_input("End date", value=today, key="rep_range_end")

    if start_d > end_d:
        st.error("Start date must be on or before end date.")
        st.stop()

    start_s = start_d.isoformat()
    end_s = end_d.isoformat()

    conn = sqlite3.connect(DB)
    total_sales, total_profit, items_sold = conn.execute(
        """SELECT COALESCE(SUM(total_bill), 0), COALESCE(SUM(profit), 0),
        COALESCE(SUM(qty), 0) FROM sales_history
        WHERE substr(timestamp, 1, 10) >= ? AND substr(timestamp, 1, 10) <= ?""",
        (start_s, end_s),
    ).fetchone()
    total_expenses = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) FROM expenses
        WHERE date >= ? AND date <= ?""",
        (start_s, end_s),
    ).fetchone()[0]
    srows = conn.execute(
        """SELECT item_name, qty, total_bill, profit, timestamp FROM sales_history
        WHERE substr(timestamp, 1, 10) >= ? AND substr(timestamp, 1, 10) <= ?
        ORDER BY timestamp DESC, id DESC""",
        (start_s, end_s),
    ).fetchall()
    conn.close()

    net_profit = round(total_profit) - round(total_expenses)

    st.caption(f"Showing data from {start_s} to {end_s} (inclusive).")

    net_kind = "net-pos" if net_profit >= 0 else "net-neg"
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(
            bata_tile_html("Total Sales (Rs.)", round(total_sales), "sales"),
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            bata_tile_html("Net Profit (Rs.)", net_profit, net_kind),
            unsafe_allow_html=True,
        )
    with t3:
        st.markdown(
            bata_tile_html("Expenses (Rs.)", round(total_expenses), "expense"),
            unsafe_allow_html=True,
        )

    st.caption(
        f"Items sold in period: {int(items_sold)} · "
        f"Gross sales profit: Rs. {round(total_profit)}"
    )

    st.markdown("---")

    def sale_row(r):
        name, q, bill, prof, ts = r
        return {
            "Date": ts,
            "Article": name,
            "Qty": q,
            "Total bill": rs(bill),
            "Profit": rs(prof),
        }

    sdf = pd.DataFrame([sale_row(r) for r in srows])
    if sdf.empty:
        st.dataframe(sdf, use_container_width=True, hide_index=True, height=120)
    else:
        st.dataframe(
            style_article_name_column(sdf, "Article"),
            use_container_width=True,
            hide_index=True,
            height=DF_HEIGHT,
        )

    st.markdown("---")
    st.markdown("##### Reset sales data")
    st.warning(
        "**Clear History** removes every row in sales history (for a new month, etc.). "
        "Inventory is **not** changed. This cannot be undone."
    )
    st.session_state.setdefault("sales_clear_pending", False)
    if st.button("Clear History", type="secondary", key="clear_sales_btn"):
        st.session_state.sales_clear_pending = True
        st.rerun()
    if st.session_state.sales_clear_pending:
        st.error("Confirm: permanently delete all sales records?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, clear all sales history", type="primary", key="clear_sales_yes"):
            conn = sqlite3.connect(DB)
            log_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO admin_logs (action, timestamp) VALUES (?, ?)",
                (f"Sales History Cleared on {log_ts}", log_ts),
            )
            conn.execute("DELETE FROM sales_history")
            conn.commit()
            conn.close()
            st.session_state.sales_clear_pending = False
            st.success("Sales history cleared.")
            st.rerun()
        if c2.button("No, keep data", key="clear_sales_no"):
            st.session_state.sales_clear_pending = False
            st.rerun()

    st.markdown("---")
    st.markdown("##### Admin Logs")
    conn = sqlite3.connect(DB)
    logs = conn.execute(
        "SELECT action, timestamp FROM admin_logs ORDER BY timestamp DESC, id DESC"
    ).fetchall()
    conn.close()
    if not logs:
        st.caption("No admin activity logged yet.")
    else:
        st.dataframe(
            [{"Action": a, "Timestamp": t} for a, t in logs],
            use_container_width=True,
            hide_index=True,
            height=min(DF_HEIGHT, max(120, 36 + 36 * len(logs))),
        )
elif page == "admin":
    st.subheader("Admin")
    st.markdown("##### Database backup")
    st.caption("Download a copy of your SQLite database for safekeeping.")
    db_path = _ROOT / "shop_data.db"
    if db_path.is_file():
        st.download_button(
            label="Download shop_data.db backup",
            data=db_path.read_bytes(),
            file_name="shop_data.db",
            mime="application/octet-stream",
            type="primary",
        )
    else:
        st.warning("Database file was not found next to app.py.")
