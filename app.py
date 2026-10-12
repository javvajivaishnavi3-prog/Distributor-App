import io
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Vendor & Distributor Parts Lookup",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }

    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px 30px;
        border-radius: 14px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
        border: 1px solid #334155;
    }
    .main-header h1 {
        color: #ffffff !important;
        margin: 0;
        font-weight: 800;
        font-size: 2.2rem;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #94a3b8;
        margin-top: 6px;
        margin-bottom: 0;
        font-size: 1rem;
    }

    div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #dc2626 !important;
        box-shadow: 0 0 0 1px #dc2626 !important;
    }

    .filter-card-red {
        background: #ffffff;
        padding: 14px 12px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(185, 28, 28, 0.06);
        border-top: 4px solid #dc2626;
        margin-bottom: 10px;
    }

    .filter-title-red {
        font-weight: 700;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
        color: #991b1b;
    }

    span[data-baseweb="tag"] {
        background-color: #fee2e2 !important;
        border: 1px solid #fca5a5 !important;
        border-radius: 6px !important;
    }
    span[data-baseweb="tag"] span {
        color: #991b1b !important;
        font-weight: 600;
    }

    .result-card {
        background: #ffffff;
        border-left: 5px solid #dc2626;
        padding: 14px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(220, 38, 38, 0.4) !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Persistent Database Setup (SQLite Server-side with Separate Tables)
DB_FILE = "automotive_app.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS distributors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_name TEXT,
            location TEXT,
            brand TEXT,
            category TEXT,
            available_parts TEXT,
            available_cars TEXT,
            part_origin TEXT,
            part_type TEXT,
            contact TEXT,
            updated_at TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT,
            part_name TEXT,
            brand TEXT,
            distributor_name TEXT,
            location TEXT,
            contact TEXT,
            part_origin TEXT,
            category TEXT,
            part_type TEXT,
            updated_at TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()


def load_db_data(table_name):
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
  conn.close()

  if table_name == "distributors" and not df.empty:
    df = df.rename(
        columns={
            "distributor_name": "DISTRIBUTOR NAME",
            "location": "LOCATION",
            "brand": "BRAND",
            "category": "CATEGORY",
            "available_parts": "AVAILABLE PARTS",
            "available_cars": "AVAILABLE CARS",
            "part_origin": "PART ORIGIN",
            "part_type": "PART TYPE",
            "contact": "_CONTACT",
        }
    )
  elif table_name == "parts" and not df.empty:
    df = df.rename(
        columns={
            "part_number": "PART NUMBER",
            "part_name": "PART NAME",
            "brand": "BRAND",
            "distributor_name": "DISTRIBUTOR NAME",
            "location": "LOCATION",
            "contact": "CONTACT",
            "part_origin": "PART ORIGIN",
            "category": "CATEGORY",
            "part_type": "PART TYPE",
        }
    )
  return df


def save_records_to_db(new_df, table_name):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

  for _, row in new_df.iterrows():
    if table_name == "distributors":
      cursor.execute(
          """
                INSERT INTO distributors (distributor_name, location, brand, category, available_parts, available_cars, part_origin, part_type, contact, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(row.get("DISTRIBUTOR NAME", "")),
              str(row.get("LOCATION", "")),
              str(row.get("BRAND", "")),
              str(row.get("CATEGORY", "")),
              str(row.get("AVAILABLE PARTS", "")),
              str(row.get("AVAILABLE CARS", "")),
              str(row.get("PART ORIGIN", "")),
              str(row.get("PART TYPE", "")),
              str(row.get("_CONTACT", "")),
              timestamp,
          ),
      )
    else:
      cursor.execute(
          """
                INSERT INTO parts (part_number, part_name, brand, distributor_name, location, contact, part_origin, category, part_type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(row.get("PART NUMBER", "")),
              str(row.get("PART NAME", "")),
              str(row.get("BRAND", "")),
              str(row.get("DISTRIBUTOR NAME", "")),
              str(row.get("LOCATION", "")),
              str(row.get("CONTACT", "")),
              str(row.get("PART ORIGIN", "")),
              str(row.get("CATEGORY", "")),
              str(row.get("PART TYPE", "")),
              timestamp,
          ),
      )
  conn.commit()
  conn.close()


# Helper Functions
def clean_key(val):
  if not val or pd.isna(val):
    return ""
  return re.sub(r"[^a-z0-9]", "", str(val).lower())


def split_multivalue_string(text):
  if not text or pd.isna(text) or str(text).lower() in ["n/a", "nan", "none", ""]:
    return []
  items = re.split(r"[,|/;\n]+", str(text))
  return [item.strip() for item in items if item.strip()]


def get_col_by_exact_or_alias(df, possible_names):
  if df.empty:
    return None
  for target in possible_names:
    for col in df.columns:
      if col.strip().lower() == target.lower():
        return col
  for target in possible_names:
    for col in df.columns:
      if target.lower() in col.strip().lower():
        return col
  return None


# Sidebar Navigation & Backend Protection Control
st.sidebar.markdown("<h2>📦 Admin Repo</h2>", unsafe_allow_html=True)

backend_unlocked = False
with st.sidebar.expander("🔒 Backend Access (Admin)"):
  admin_pass = st.text_input("Enter Password", type="password")
  if admin_pass == "admin123":
    backend_unlocked = True
    st.success("Backend access granted.")
  elif admin_pass:
    st.error("Incorrect password.")

nav_options = ["View & Search"]
if backend_unlocked:
  nav_options = ["Add Record", "View & Search", "Import Data"]

st.sidebar.markdown("### Navigation")
navigation = st.sidebar.radio(
    "Select Mode", options=nav_options, label_visibility="collapsed"
)

st.sidebar.divider()
total_dist_count = len(load_db_data("distributors"))
total_parts_count = len(load_db_data("parts"))
st.sidebar.markdown(f"**Database:** `{DB_FILE}`")
st.sidebar.markdown(f"**Distributor Records:** `{total_dist_count}`")
st.sidebar.markdown(f"**Parts Records:** `{total_parts_count}`")

# Load Active Database Data
clean_dist_df = load_db_data("distributors")
parts_df = load_db_data("parts")


def extract_field_values(df, col_name, field_type):
  if df.empty or not col_name or col_name not in df.columns:
    return []
  all_vals = set()
  unique_series = df[col_name].dropna().unique()
  if field_type in ["DISTRIBUTOR NAME", "LOCATION", "BRAND"]:
    for v in unique_series:
      items = split_multivalue_string(v)
      for item in items:
        if item and item.lower() not in ["n/a", "nan", "none", ""]:
          all_vals.add(item)
  elif field_type in ["CATEGORY", "TYPE", "PART ORIGIN"]:
    for val in unique_series:
      items = split_multivalue_string(val)
      for item in items:
        if item.lower() not in ["n/a", "nan", "none"]:
          all_vals.add(item)
  return sorted(list(all_vals))


def to_excel(df):
  output = io.BytesIO()
  clean_export = df.drop(
      columns=[c for c in df.columns if c.startswith("_")], errors="ignore"
  )
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    clean_export.to_excel(writer, index=False, sheet_name="Lookup_Results")
  return output.getvalue()


# ---------------------------------------------------------
# TAB 1: ADD RECORD MANUALLY (Restricted Backend)
# ---------------------------------------------------------
if navigation == "Add Record":
  st.markdown(
      "<h1>➕ Add New Record to Database</h1>", unsafe_allow_html=True
  )
  target_table = st.selectbox(
      "Select Target Table", options=["distributors", "parts"]
  )

  with st.form("add_record_form"):
    if target_table == "distributors":
      c1, c2 = st.columns(2)
      with c1:
        f_name = st.text_input("Distributor Name *")
        f_loc = st.text_input("Location / City")
        f_brand = st.text_input("Brand Handled")
        f_cat = st.text_input("Category")
      with c2:
        f_contact = st.text_input("Distributor Contact Number *")
        f_type = st.text_input("Part Type / Quality")
        f_origin = st.text_input("Part Origin")

      f_avail_parts = st.text_area(
          "Available Parts", placeholder="One part per line or comma-separated"
      )
      f_avail_cars = st.text_area(
          "Available Cars", placeholder="Car models or brands supported"
      )

      submitted = st.form_submit_button("Save Distributor Record")
      if submitted:
        if not f_name or not f_contact:
          st.error("Distributor Name and Contact Number are mandatory fields!")
        else:
          new_row = pd.DataFrame([{
              "DISTRIBUTOR NAME": f_name,
              "LOCATION": f_loc,
              "BRAND": f_brand,
              "CATEGORY": f_cat,
              "AVAILABLE PARTS": f_avail_parts,
              "AVAILABLE CARS": f_avail_cars,
              "PART ORIGIN": f_origin,
              "PART TYPE": f_type,
              "_CONTACT": f_contact,
          }])
          save_records_to_db(new_row, "distributors")
          st.success(f"Successfully added distributor: {f_name}!")
          st.rerun()
    else:
      c1, c2 = st.columns(2)
      with c1:
        p_num = st.text_input("Part Number *")
        p_name = st.text_input("Part Name / Description *")
        p_brand = st.text_input("Brand")
        p_dist = st.text_input("Distributor Name")
      with c2:
        p_loc = st.text_input("Location")
        p_contact = st.text_input("Contact")
        p_origin = st.text_input("Part Origin")
        p_cat = st.text_input("Category")
        p_type = st.text_input("Part Type")

      submitted = st.form_submit_button("Save Parts Record")
      if submitted:
        if not p_num or not p_name:
          st.error("Part Number and Part Name are mandatory fields!")
        else:
          new_row = pd.DataFrame([{
              "PART NUMBER": p_num,
              "PART NAME": p_name,
              "BRAND": p_brand,
              "DISTRIBUTOR NAME": p_dist,
              "LOCATION": p_loc,
              "CONTACT": p_contact,
              "PART ORIGIN": p_origin,
              "CATEGORY": p_cat,
              "PART TYPE": p_type,
          }])
          save_records_to_db(new_row, "parts")
          st.success(f"Successfully added part: {p_num}!")
          st.rerun()

# ---------------------------------------------------------
# TAB 2: IMPORT DATA BULK (Restricted Backend)
# ---------------------------------------------------------
elif navigation == "Import Data":
  st.markdown(
      "<h1>📂 Bulk Import Data via Excel / CSV</h1>", unsafe_allow_html=True
  )
  target_table = st.selectbox(
      "Select Target Table to Import Into", options=["distributors", "parts"]
  )

  uploaded_file = st.file_uploader(
      "Upload Catalog File", type=["xlsx", "xls", "csv"]
  )
  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        import_df = pd.read_csv(uploaded_file, dtype=str)
      else:
        try:
          import_df = pd.read_excel(uploaded_file, engine="openpyxl", dtype=str)
        except Exception:
          import_df = pd.read_excel(uploaded_file, engine="calamine", dtype=str)

      st.write("Preview of Uploaded Data:", import_df.head())

      if st.button("Confirm and Import into Server Database"):
        processed_import = pd.DataFrame()
        if target_table == "distributors":
          c_dist = (
              get_col_by_exact_or_alias(
                  import_df,
                  [
                      "DISTRIBUTOR NAME",
                      "VENDOR",
                      "SUPPLIER",
                      "COMPANY",
                      "DISTRIBUTOR",
                  ],
              )
              or import_df.columns[0]
          )
          c_loc = get_col_by_exact_or_alias(
              import_df, ["LOCATION", "CITY", "ADDRESS"]
          )
          c_brand = get_col_by_exact_or_alias(
              import_df, ["BRAND", "MAKE", "MANUFACTURER"]
          )
          c_cat = get_col_by_exact_or_alias(import_df, ["CATEGORY", "GROUP"])
          c_parts = get_col_by_exact_or_alias(
              import_df, ["AVAILABLE PARTS", "PARTS", "ITEMS"]
          )
          c_cars = get_col_by_exact_or_alias(
              import_df, ["AVAILABLE CARS", "AVAILABLE BRANDS", "CARS"]
          )
          c_origin = get_col_by_exact_or_alias(
              import_df, ["PART ORIGIN", "ORIGIN"]
          )
          c_type = get_col_by_exact_or_alias(import_df, ["TYPE", "QUALITY"])
          c_contact = get_col_by_exact_or_alias(
              import_df, ["CONTACT", "PHONE", "MOBILE"]
          )

          processed_import["DISTRIBUTOR NAME"] = (
              import_df[c_dist].astype(str).str.strip() if c_dist else ""
          )
          processed_import["LOCATION"] = (
              import_df[c_loc].astype(str).str.strip() if c_loc else ""
          )
          processed_import["BRAND"] = (
              import_df[c_brand].astype(str).str.strip() if c_brand else ""
          )
          processed_import["CATEGORY"] = (
              import_df[c_cat].astype(str).str.strip() if c_cat else ""
          )
          processed_import["AVAILABLE PARTS"] = (
              import_df[c_parts].astype(str).str.strip() if c_parts else ""
          )
          processed_import["AVAILABLE CARS"] = (
              import_df[c_cars].astype(str).str.strip() if c_cars else ""
          )
          processed_import["PART ORIGIN"] = (
              import_df[c_origin].astype(str).str.strip() if c_origin else ""
          )
          processed_import["PART TYPE"] = (
              import_df[c_type].astype(str).str.strip() if c_type else ""
          )
          processed_import["_CONTACT"] = (
              import_df[c_contact].astype(str).str.strip() if c_contact else ""
          )
        else:
          col_pnum = (
              get_col_by_exact_or_alias(
                  import_df,
                  [
                      "PART NUMBER",
                      "PART NO",
                      "CODE",
                      "ITEM NO",
                      "PART_NUMBER",
                      "SKU",
                  ],
              )
              or import_df.columns[0]
          )
          col_pname = get_col_by_exact_or_alias(
              import_df, ["PART NAME", "DESCRIPTION", "ITEM NAME", "TITLE"]
          )
          col_pbrand = get_col_by_exact_or_alias(
              import_df, ["BRAND", "MAKE", "TAX:PRODUCT_BRAND"]
          )
          col_pdist = (
              get_col_by_exact_or_alias(
                  import_df, ["DISTRIBUTOR NAME", "VENDOR", "SUPPLIER"]
              )
              or "DISTRIBUTOR NAME"
          )
          col_ploc = get_col_by_exact_or_alias(
              import_df, ["LOCATION", "CITY", "STATE", "ADDRESS"]
          )
          col_pcontact = get_col_by_exact_or_alias(
              import_df, ["CONTACT", "PHONE", "MOBILE"]
          )
          col_porigin = get_col_by_exact_or_alias(
              import_df, ["PART ORIGIN", "ORIGIN", "COUNTRY"]
          )
          col_pcat = get_col_by_exact_or_alias(
              import_df, ["CATEGORY", "CAT", "GROUP"]
          )
          col_ptype = get_col_by_exact_or_alias(
              import_df, ["TYPE", "PART TYPE", "QUALITY"]
          )

          processed_import["PART NUMBER"] = (
              import_df[col_pnum].astype(str).str.strip() if col_pnum else ""
          )
          processed_import["PART NAME"] = (
              import_df[col_pname].astype(str).str.strip() if col_pname else ""
          )
          processed_import["BRAND"] = (
              import_df[col_pbrand].astype(str).str.strip() if col_pbrand else ""
          )
          processed_import["DISTRIBUTOR NAME"] = (
              import_df[col_pdist].astype(str).str.strip()
              if col_pdist in import_df.columns
              else os.path.splitext(uploaded_file.name)[0]
          )
          processed_import["LOCATION"] = (
              import_df[col_ploc].astype(str).str.strip() if col_ploc else ""
          )
          processed_import["CONTACT"] = (
              import_df[col_pcontact].astype(str).str.strip()
              if col_pcontact
              else ""
          )
          processed_import["PART ORIGIN"] = (
              import_df[col_porigin].astype(str).str.strip()
              if col_porigin
              else ""
          )
          processed_import["CATEGORY"] = (
              import_df[col_pcat].astype(str).str.strip() if col_pcat else ""
          )
          processed_import["PART TYPE"] = (
              import_df[col_ptype].astype(str).str.strip() if col_ptype else ""
          )

        save_records_to_db(processed_import, target_table)
        st.success(
            f"Successfully imported {len(processed_import)} records into"
            f" '{target_table}' database!"
        )
    except Exception as e:
      st.error(f"Error parsing file: {e}")

  st.divider()
  st.markdown("### 🗑️ Clear Table Data")
  table_to_clear = st.selectbox(
      "Select Table to Clear",
      options=["distributors", "parts"],
      key="clear_table_sel",
  )
  if st.button("Confirm and Clear Selected Table"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_to_clear}")
    conn.commit()
    conn.close()
    st.warning(f"Table '{table_to_clear}' has been cleared successfully.")
    st.rerun()

# ---------------------------------------------------------
# TAB 3: VIEW & SEARCH (Public / Company-wide Access)
# ---------------------------------------------------------
elif navigation == "View & Search":
  st.markdown(
      """
        <div class="main-header">
            <h1>📦 Automotive Vendor & Parts Catalog</h1>
            <p>Stateless Real-Time Parts & Distributor Data Engine.</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  filter_keys = [
      "sel_vendors",
      "sel_locations",
      "sel_brands",
      "sel_categories",
      "sel_types",
      "sel_origins",
  ]
  for key in filter_keys:
    if key not in st.session_state:
      st.session_state[key] = []

  search_col, mode_col = st.columns([3, 1])

  with search_col:
    search_query = st.text_input(
        "🔍 Global Keyword Search",
        placeholder="Search by part number, part name, vendor, location...",
    )

  with mode_col:
    data_mode = st.selectbox(
        "📊 Data View Mode", options=["Parts Data", "Distributor Data"]
    )

  active_base_df = parts_df if data_mode == "Parts Data" else clean_dist_df


  def build_filtered_df(df, exclude=None):
    if exclude is None:
      exclude = []
    temp = df.copy()
    if temp.empty:
      return temp

    if (
        "vendors" not in exclude
        and st.session_state["sel_vendors"]
        and "DISTRIBUTOR NAME" in temp.columns
    ):
      temp = temp[
          temp["DISTRIBUTOR NAME"]
          .astype(str)
          .isin(st.session_state["sel_vendors"])
      ]

    if (
        "locations" not in exclude
        and st.session_state["sel_locations"]
        and "LOCATION" in temp.columns
    ):
      temp = temp[
          temp["LOCATION"].astype(str).isin(st.session_state["sel_locations"])
      ]

    if "brands" not in exclude and st.session_state["sel_brands"]:
      pattern = (
          r"\b(?:"
          + "|".join([re.escape(b) for b in st.session_state["sel_brands"]])
          + r")\b"
      )
      if "BRAND" in temp.columns:
        temp = temp[
            temp["BRAND"]
            .astype(str)
            .str.contains(pattern, case=False, na=False, regex=True)
        ]

    if (
        "categories" not in exclude
        and st.session_state["sel_categories"]
        and "CATEGORY" in temp.columns
    ):
      pattern = (
          r"\b(?:"
          + "|".join([re.escape(c) for c in st.session_state["sel_categories"]])
          + r")\b"
      )
      temp = temp[
          temp["CATEGORY"]
          .astype(str)
          .str.contains(pattern, case=False, na=False, regex=True)
      ]

    if (
        "types" not in exclude
        and st.session_state["sel_types"]
        and "PART TYPE" in temp.columns
    ):
      pattern = (
          r"\b(?:"
          + "|".join([re.escape(t) for t in st.session_state["sel_types"]])
          + r")\b"
      )
      temp = temp[
          temp["PART TYPE"]
          .astype(str)
          .str.contains(pattern, case=False, na=False, regex=True)
      ]

    if (
        "origins" not in exclude
        and st.session_state["sel_origins"]
        and "PART ORIGIN" in temp.columns
    ):
      pattern = (
          r"\b(?:"
          + "|".join([re.escape(o) for o in st.session_state["sel_origins"]])
          + r")\b"
      )
      temp = temp[
          temp["PART ORIGIN"]
          .astype(str)
          .str.contains(pattern, case=False, na=False, regex=True)
      ]

    return temp


  with ThreadPoolExecutor(max_workers=6) as executor:
    fut_vendors = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["vendors"]),
        "DISTRIBUTOR NAME",
        "DISTRIBUTOR NAME",
    )
    fut_locations = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["locations"]),
        "LOCATION",
        "LOCATION",
    )
    fut_brands = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["brands"]),
        "BRAND",
        "BRAND",
    )
    fut_categories = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["categories"]),
        "CATEGORY",
        "CATEGORY",
    )
    fut_types = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["types"]),
        "PART TYPE",
        "TYPE",
    )
    fut_origins = executor.submit(
        extract_field_values,
        build_filtered_df(active_base_df, exclude=["origins"]),
        "PART ORIGIN",
        "PART ORIGIN",
    )

    valid_vendors = fut_vendors.result()
    valid_locations = fut_locations.result()
    valid_brands = fut_brands.result()
    valid_categories = fut_categories.result()
    valid_types = fut_types.result()
    valid_origins = fut_origins.result()

  st.session_state["sel_vendors"] = [
      v for v in st.session_state["sel_vendors"] if v in valid_vendors
  ]
  st.session_state["sel_locations"] = [
      l for l in st.session_state["sel_locations"] if l in valid_locations
  ]
  st.session_state["sel_brands"] = [
      b for b in st.session_state["sel_brands"] if b in valid_brands
  ]
  st.session_state["sel_categories"] = [
      c for c in st.session_state["sel_categories"] if c in valid_categories
  ]
  st.session_state["sel_types"] = [
      t for t in st.session_state["sel_types"] if t in valid_types
  ]
  st.session_state["sel_origins"] = [
      o for o in st.session_state["sel_origins"] if o in valid_origins
  ]

  st.markdown("#### 🎛️ Filter Options")
  f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns(6)

  with f_col1:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">🏢 Distributor</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Distributor",
        options=valid_vendors,
        key="sel_vendors",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_col2:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">📍 Location</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Location",
        options=valid_locations,
        key="sel_locations",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_col3:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">🚘 Brand</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Brand",
        options=valid_brands,
        key="sel_brands",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_col4:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">📂 Category</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Category",
        options=valid_categories,
        key="sel_categories",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_col5:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">⚙ Part Type</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Type",
        options=valid_types,
        key="sel_types",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with f_col6:
    st.markdown(
        '<div class="filter-card-red"><div'
        ' class="filter-title-red">🌍 Origin</div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Select Origin",
        options=valid_origins,
        key="sel_origins",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

  st.divider()

  is_filter_active = bool(
      search_query.strip() or any(st.session_state[k] for k in filter_keys)
  )

  if not is_filter_active:
    st.info(
        "💡 **Search Ready:** Enter a keyword or select any filter above to"
        " display matching records."
    )
  else:
    results_to_show = (
        build_filtered_df(active_base_df)
        if not active_base_df.empty
        else pd.DataFrame()
    )

    if search_query.strip() and not results_to_show.empty:
      query = search_query.strip().lower()
      search_cols = [
          c for c in results_to_show.columns if not c.startswith("_")
      ]
      mask = results_to_show[search_cols].apply(
          lambda row: row.astype(str)
          .str.lower()
          .str.contains(query, regex=False)
          .any(),
          axis=1,
      )
      results_to_show = results_to_show[mask]

    res_title_col, dl_col = st.columns([3, 1])

    with res_title_col:
      st.markdown(
          f"""
                <div class="result-card">
                    <span style="font-size: 1.15rem; font-weight: 700; color: #991b1b;">
                        📊 Found {len(results_to_show)} matching records ({data_mode})
                    </span>
                </div>
            """,
          unsafe_allow_html=True,
      )

    with dl_col:
      if not results_to_show.empty:
        excel_data = to_excel(results_to_show)
        st.download_button(
            label="📥 Export Excel",
            data=excel_data,
            file_name="lookup_results.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    if results_to_show.empty:
      st.warning("⚠️ No records found matching your active filter criteria.")
    else:
      if data_mode == "Distributor Data":
        final_cols = [
            "DISTRIBUTOR NAME",
            "LOCATION",
            "_CONTACT",
            "BRAND",
            "CATEGORY",
            "AVAILABLE PARTS",
            "AVAILABLE CARS",
            "PART ORIGIN",
            "PART TYPE",
        ]
        display_df = (
            results_to_show.reindex(columns=final_cols)
            .rename(columns={"_CONTACT": "CONTACT"})
            .fillna("")
        )
      else:
        final_cols = [
            "PART NUMBER",
            "PART NAME",
            "BRAND",
            "DISTRIBUTOR NAME",
            "LOCATION",
            "CONTACT",
            "PART ORIGIN",
        ]
        display_df = results_to_show.reindex(columns=final_cols).fillna("")

      st.data_editor(
          display_df.head(1000),
          use_container_width=True,
          hide_index=True,
          disabled=True,
      )
