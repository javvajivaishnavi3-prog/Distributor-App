import io
import os
import re
import sys
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

# Application Header
st.markdown(
    """
    <div class="main-header">
        <h1>📦 Automotive Vendor & Parts Catalog</h1>
        <p>Stateless Real-Time Parts & Distributor Data Engine.</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Base directory relative resolution for Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def read_single_abs_file(file_path):
    filename = os.path.basename(file_path)
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file_path, low_memory=False, dtype=str)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path, engine="openpyxl", dtype=str)
        else:
            return None, None

        if df.empty:
            return None, None

        # Clean Header Row safely converting floats/NaNs to strings
        for idx in range(min(5, len(df))):
            row_str = " ".join([str(val) for val in df.iloc[idx].values if pd.notna(val)]).lower()
            if any(
                k in row_str
                for k in [
                    "part",
                    "code",
                    "item",
                    "description",
                    "distributor",
                    "vendor",
                ]
            ):
                if idx > 0:
                    df.columns = df.iloc[idx].astype(str)
                    df = df.iloc[idx + 1 :].reset_index(drop=True)
                break

        df.columns = df.columns.astype(str).str.strip()

        dist_keywords = [
            "distributor",
            "vendor",
            "supplier",
            "vender",
            "dist",
            "dealer",
            "partner",
            "network",
        ]
        filename_lower = filename.lower()
        filename_match = any(k in filename_lower for k in dist_keywords)

        cols_lower = [c.lower() for c in df.columns]
        column_match = any(
            c in cols_lower
            for c in [
                "distributor name",
                "vendor name",
                "supplier name",
                "company",
                "dealer name",
            ]
        )

        is_distributor = filename_match or column_match

        if is_distributor:
            return "distributor", df
        else:
            raw_vendor_name = os.path.splitext(filename)[0]
            clean_vendor_name = re.sub(
                r"(?i)(_parts|_catalog|_list|_inventory|\s+parts|\s+catalog)",
                "",
                raw_vendor_name,
            ).strip()
            if "DISTRIBUTOR NAME" not in df.columns:
                df["DISTRIBUTOR NAME"] = clean_vendor_name
            return "parts", df
    except Exception as e:
        st.error(f"Error loading {filename}: {e}")
        return None, None


@st.cache_data
def read_current_disk_data():
    distributor_dfs = []
    parts_dfs = []

    for f in os.listdir(BASE_DIR):
        if (
            f.endswith((".csv", ".xlsx", ".xls"))
            and not f.startswith("~$")
            and not f.startswith(".")
        ):
            full_path = os.path.join(BASE_DIR, f)
            f_type, df = read_single_abs_file(full_path)
            if f_type == "distributor" and df is not None and not df.empty:
                distributor_dfs.append(df)
            elif f_type == "parts" and df is not None and not df.empty:
                parts_dfs.append(df)

    master_dist_df = (
        pd.concat(distributor_dfs, ignore_index=True)
        if distributor_dfs
        else pd.DataFrame()
    )
    master_parts_df = (
        pd.concat(parts_dfs, ignore_index=True) if parts_dfs else pd.DataFrame()
    )

    return master_dist_df, master_parts_df


raw_dist_df, raw_parts_df = read_current_disk_data()

# Process Distributor Data
clean_dist_df = pd.DataFrame()
dist_lookup_map = {}

if not raw_dist_df.empty:
    raw_dist_df = raw_dist_df.fillna("")

    c_dist = (
        get_col_by_exact_or_alias(
            raw_dist_df,
            [
                "DISTRIBUTOR NAME",
                "VENDOR NAME",
                "SUPPLIER",
                "COMPANY",
                "VENDOR",
                "DISTRIBUTOR",
                "NAME",
                "DEALER",
            ],
        )
        or raw_dist_df.columns[0]
    )
    c_loc = get_col_by_exact_or_alias(
        raw_dist_df, ["LOCATION", "CITY", "ADDRESS", "STATE", "PLACE"]
    )
    c_brand = get_col_by_exact_or_alias(
        raw_dist_df, ["BRAND", "MAKE", "MANUFACTURER"]
    )
    c_cat = get_col_by_exact_or_alias(
        raw_dist_df, ["CATEGORY", "CATEGORIES", "PRODUCT CATEGORY"]
    )
    c_avail_parts = get_col_by_exact_or_alias(
        raw_dist_df,
        ["AVAILABLE PARTS", "PARTS", "DEALS IN", "SCOPE", "ITEMS"],
    )
    c_avail_cars = get_col_by_exact_or_alias(
        raw_dist_df,
        [
            "AVAILABLE CARS",
            "AVAILABLE CAR",
            "AVAILABLE BRANDS",
            "AVAILABLE BRAND",
            "CAR BRANDS",
            "CARS",
        ],
    )
    c_origin = get_col_by_exact_or_alias(
        raw_dist_df, ["PART ORIGIN", "ORIGIN", "COUNTRY"]
    )
    c_type = get_col_by_exact_or_alias(
        raw_dist_df, ["TYPE", "PART TYPE", "OEM/OES", "QUALITY"]
    )
    c_contact = get_col_by_exact_or_alias(
        raw_dist_df,
        ["CONTACT", "PHONE", "MOBILE", "NUMBER", "CONTACT NO", "PHONE NO"],
    )

    clean_dist_df["DISTRIBUTOR NAME"] = (
        raw_dist_df[c_dist].astype(str).str.strip() if c_dist else ""
    )
    clean_dist_df["LOCATION"] = (
        raw_dist_df[c_loc].astype(str).str.strip() if c_loc else ""
    )
    clean_dist_df["BRAND"] = (
        raw_dist_df[c_brand].astype(str).str.strip() if c_brand else ""
    )
    clean_dist_df["CATEGORY"] = (
        raw_dist_df[c_cat].astype(str).str.strip() if c_cat else ""
    )
    clean_dist_df["AVAILABLE PARTS"] = (
        raw_dist_df[c_avail_parts].astype(str).str.strip()
        if c_avail_parts
        else ""
    )
    clean_dist_df["AVAILABLE CARS"] = (
        raw_dist_df[c_avail_cars].astype(str).str.strip() if c_avail_cars else ""
    )
    clean_dist_df["PART ORIGIN"] = (
        raw_dist_df[c_origin].astype(str).str.strip() if c_origin else ""
    )
    clean_dist_df["PART TYPE"] = (
        raw_dist_df[c_type].astype(str).str.strip() if c_type else ""
    )
    clean_dist_df["_CONTACT"] = (
        raw_dist_df[c_contact].astype(str).str.strip() if c_contact else ""
    )

    for idx, row in clean_dist_df.iterrows():
        key = clean_key(row["DISTRIBUTOR NAME"])
        if key and key not in dist_lookup_map:
            dist_lookup_map[key] = {
                "LOCATION": row["LOCATION"],
                "CONTACT": row["_CONTACT"],
                "PART ORIGIN": row["PART ORIGIN"],
            }

# Process Parts Data
parts_df = pd.DataFrame()
if not raw_parts_df.empty:
    raw_parts_df = raw_parts_df.fillna("")

    col_pnum = (
        get_col_by_exact_or_alias(
            raw_parts_df,
            [
                "PART NUMBER",
                "PART NO",
                "CODE",
                "ITEM NO",
                "PART_NUMBER",
                "PARTNO",
                "SKU",
            ],
        )
        or raw_parts_df.columns[0]
    )
    col_pname = get_col_by_exact_or_alias(
        raw_parts_df,
        ["PART NAME", "DESCRIPTION", "ITEM NAME", "TITLE", "PART_NAME", "NAME"],
    )
    col_pbrand = get_col_by_exact_or_alias(
        raw_parts_df, ["BRAND", "MAKE", "TAX:PRODUCT_BRAND"]
    )
    col_pdist = (
        get_col_by_exact_or_alias(
            raw_parts_df, ["DISTRIBUTOR NAME", "VENDOR", "SUPPLIER"]
        )
        or "DISTRIBUTOR NAME"
    )
    col_ploc = get_col_by_exact_or_alias(
        raw_parts_df, ["LOCATION", "CITY", "STATE", "ADDRESS"]
    )
    col_pcontact = get_col_by_exact_or_alias(
        raw_parts_df, ["CONTACT", "PHONE", "MOBILE", "PHONE NO"]
    )
    col_porigin = get_col_by_exact_or_alias(
        raw_parts_df, ["PART ORIGIN", "ORIGIN", "COUNTRY"]
    )
    col_pcat = get_col_by_exact_or_alias(
        raw_parts_df, ["CATEGORY", "CAT", "PRODUCT_CAT", "GROUP"]
    )
    col_ptype = get_col_by_exact_or_alias(
        raw_parts_df, ["TYPE", "PART TYPE", "ITEM_TYPE", "QUALITY"]
    )

    parts_df["PART NUMBER"] = (
        raw_parts_df[col_pnum].astype(str).str.strip() if col_pnum else ""
    )
    parts_df["PART NAME"] = (
        raw_parts_df[col_pname].astype(str).str.strip() if col_pname else ""
    )
    parts_df["BRAND"] = (
        raw_parts_df[col_pbrand].astype(str).str.strip() if col_pbrand else ""
    )
    parts_df["DISTRIBUTOR NAME"] = (
        raw_parts_df[col_pdist].astype(str).str.strip()
        if col_pdist in raw_parts_df.columns
        else ""
    )
    parts_df["LOCATION"] = (
        raw_parts_df[col_ploc].astype(str).str.strip() if col_ploc else ""
    )
    parts_df["CONTACT"] = (
        raw_parts_df[col_pcontact].astype(str).str.strip() if col_pcontact else ""
    )
    parts_df["PART ORIGIN"] = (
        raw_parts_df[col_porigin].astype(str).str.strip() if col_porigin else ""
    )
    parts_df["CATEGORY"] = (
        raw_parts_df[col_pcat].astype(str).str.strip() if col_pcat else ""
    )
    parts_df["PART TYPE"] = (
        raw_parts_df[col_ptype].astype(str).str.strip() if col_ptype else ""
    )

    def enrich_single_dict(row_dict):
        dist_key = clean_key(row_dict["DISTRIBUTOR NAME"])
        match_info = None

        if dist_key in dist_lookup_map:
            match_info = dist_lookup_map[dist_key]
        else:
            for k, info in dist_lookup_map.items():
                if k in dist_key or dist_key in k:
                    match_info = info
                    break

        if match_info:
            if not row_dict["LOCATION"]:
                row_dict["LOCATION"] = match_info["LOCATION"]
            if not row_dict["CONTACT"]:
                row_dict["CONTACT"] = match_info["CONTACT"]
            if not row_dict["PART ORIGIN"]:
                row_dict["PART ORIGIN"] = match_info["PART ORIGIN"]

        if not row_dict["PART ORIGIN"]:
            row_dict["PART ORIGIN"] = "OEM/OES Standard"

        return row_dict

    dicts = parts_df.to_dict("records")
    enriched_dicts = [enrich_single_dict(d) for d in dicts]
    parts_df = pd.DataFrame(enriched_dicts)


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

# Top Search Controls
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


valid_vendors = extract_field_values(
    build_filtered_df(active_base_df, exclude=["vendors"]),
    "DISTRIBUTOR NAME",
    "DISTRIBUTOR NAME",
)
valid_locations = extract_field_values(
    build_filtered_df(active_base_df, exclude=["locations"]),
    "LOCATION",
    "LOCATION",
)
valid_brands = extract_field_values(
    build_filtered_df(active_base_df, exclude=["brands"]), "BRAND", "BRAND"
)
valid_categories = extract_field_values(
    build_filtered_df(active_base_df, exclude=["categories"]),
    "CATEGORY",
    "CATEGORY",
)
valid_types = extract_field_values(
    build_filtered_df(active_base_df, exclude=["types"]), "PART TYPE", "TYPE"
)
valid_origins = extract_field_values(
    build_filtered_df(active_base_df, exclude=["origins"]),
    "PART ORIGIN",
    "PART ORIGIN",
)

# Synchronize selections
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

# Filter Selection UI Cards
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
        search_cols = [c for c in results_to_show.columns if not c.startswith("_")]
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
