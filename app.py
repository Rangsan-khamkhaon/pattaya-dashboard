import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
import plotly.express as px
import streamlit.components.v1 as components

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ (Page Config)
# ==========================================
st.set_page_config(page_title="Pattaya 4D Dashboard", page_icon="🗺️", layout="wide")

# 🔥 CSS Hack: ย่อส่วน + บีบช่องว่างให้แน่นสุดๆ
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        header, footer { display: none !important; }
        
        h2 { font-size: 1.2rem !important; padding-bottom: 0 !important; margin-bottom: -10px !important; }
        h3 { font-size: 0.9rem !important; padding-bottom: 0 !important; margin-bottom: -10px !important; }
        p, .stSlider label, .stSelectbox label, .stCheckbox label { font-size: 0.8rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
        [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }
        
        /* 💡 บีบช่องว่างของเส้นคั่น (Divider) ให้บางเฉียบ */
        hr { margin: 0.5em 0px !important; }
        
        /* 💡 ลดช่องว่างด้านล่างสุดของบล็อกแผนที่และกราฟ */
        .element-container { margin-bottom: :0.5rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ 2. โหลดข้อมูล (Data Prep)
# ==========================================
@st.cache_data
def load_and_prep_data():
    # ⚠️ อย่าลืมแก้ Path เป็นไฟล์ของมึงนะ
    FILE_PATH = 'Google_Place_Pattaya_AI_Refined_New.csv'
    df = pd.read_csv(FILE_PATH)
    if 'latitude' not in df.columns:
        df.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'}, inplace=True)
    df = df.dropna(subset=['latitude', 'longitude'])
    
    def get_hours(sub_cat):
        sub_cat = str(sub_cat).lower()
        if 'nightlife' in sub_cat or 'bars' in sub_cat: return 18, 2
        elif 'cafes' in sub_cat or 'coffee' in sub_cat: return 8, 20
        elif 'fast food' in sub_cat or 'convenience' in sub_cat: return 0, 24
        elif 'shopping' in sub_cat or 'mall' in sub_cat: return 10, 22
        elif 'office' in sub_cat or 'gov' in sub_cat: return 8, 17
        elif 'parks' in sub_cat or 'beach' in sub_cat: return 5, 20
        else: return 9, 21
        
    df['open_hour'], df['close_hour'] = zip(*df['Sub-Category'].apply(get_hours))
    return df

df = load_and_prep_data()

# ==========================================
# 🏗️ 3. โซนบน: แบ่งหน้าจอ (ซ้าย: แผนที่ 7.5 | ขวา: แผงควบคุม 2.5)
# ==========================================
map_col, panel_col = st.columns([7.5, 2.5], gap="small")

# ==========================================
# 🎛️ 4. แผงควบคุม (ฝั่งขวา)
# ==========================================
with panel_col:
    st.markdown("<h2>Pattaya 4D Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray;'>ระบบวิเคราะห์พลวัตเมือง (Day/Night Economy)</p>", unsafe_allow_html=True)
    st.divider()

    st.subheader("⚙️ CONTROLLER")
    
    selected_hour = st.slider("⏰ เวลา (ชั่วโมง):", 0, 23, 14, format="%02d:00 น.")
    all_main_cats = ["All"] + sorted(df['Main Category'].astype(str).unique().tolist())
    selected_main = st.selectbox("📌 หมวดหมู่หลัก:", all_main_cats)
    traffic_mode = st.checkbox("🚦 โหมดวิเคราะห์รถติด (Heatmap สีแดง)", value=True)
    
    cat_df = df[df['Main Category'] == selected_main] if selected_main != "All" else df
    
    def is_open(row, h):
        o, c = row['open_hour'], row['close_hour']
        if o == 0 and c == 24: return True
        if o <= c: return o <= h < c
        else: return h >= o or h < c
        
    active_df = cat_df[cat_df.apply(lambda r: is_open(r, selected_hour), axis=1)]
    closing_soon_df = cat_df[cat_df['close_hour'] == selected_hour]

    st.divider()

    st.subheader("📊 REAL-TIME STATS")
    st.metric(f"✅ เปิดบริการ ({selected_hour:02d}:00 น.)", f"{len(active_df):,}", delta="สถานที่ Active")
    st.metric(f"🚨 กำลังจะปิด (เสี่ยงรถติด)", f"{len(closing_soon_df):,}", delta="คนเตรียมเดินทาง", delta_color="inverse")
    
    st.divider()

    st.subheader("📈 TOP ACTIVE")
    if len(active_df) > 0:
        sub_counts = active_df['Sub-Category'].value_counts().reset_index()
        sub_counts.columns = ['Sub-Category', 'Count']
        fig = px.bar(sub_counts.head(5), x='Count', y='Sub-Category', orientation='h', color='Count', color_continuous_scale='Viridis')
        fig.update_layout(height=180, margin=dict(l=0, r=0, t=0, b=0), yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        fig.update_yaxes(tickfont=dict(size=10)) 
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่มีสถานที่เปิดในเวลานี้")

# ==========================================
# 🗺️ 5. แผนที่ (ฝั่งซ้าย) ด้วยเทคโนโลยี Pydeck (Deck.gl) โคตรลื่นและไม่กินแรม!
# ==========================================
with map_col:
    # 1. จัดเตรียมข้อมูลสำหรับพล็อต (พังเพราะ RAM ต้องคุมให้อยู่)
    plot_df = active_df.copy()
    if len(plot_df) > 0:
        # รวมชื่อไทย/อังกฤษ ไว้โชว์ใน Tooltip
        plot_df['name_show'] = plot_df['Display Name (TH)'].fillna(plot_df['Display Name (EN)'])
    
    # 2. ตั้งค่ามุมกล้องเริ่มต้น (เอียงกล้อง 45 องศาให้ดูเป็น 3D เท่ๆ)
    view_state = pdk.ViewState(
        latitude=12.9236,
        longitude=100.8825,
        zoom=12,
        pitch=45,
    )

    layers = []

    # 3. เลเยอร์ที่ 1: จุดสถานที่กำลังเปิด (ใช้ ScatterplotLayer ทำงานไวมาก)
    if len(plot_df) > 0:
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=plot_df,
            get_position='[longitude, latitude]',
            get_color='[46, 204, 113, 200]', # สีเขียวนีออน
            get_radius=40, # รัศมีวงกลม (เมตร)
            pickable=True, # ให้เอาเมาส์ชี้ได้
        )
        layers.append(scatter_layer)

    # 4. เลเยอร์ที่ 2: Heatmap จุดรถติด (ถ้าเปิดโหมดไว้)
    if traffic_mode and len(closing_soon_df) > 0:
        heat_layer = pdk.Layer(
            "HeatmapLayer",
            data=closing_soon_df,
            get_position='[longitude, latitude]',
            opacity=0.8,
            get_weight=1,
            radiusPixels=30, # ขนาดความฟุ้งของ Heatmap
        )
        layers.append(heat_layer)

    # 5. วาดแผนที่! (ใช้ map_style ธีมมืดให้เข้ากับแสงสีพัทยา)
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v9",
        tooltip={"html": "<b>{name_show}</b><br>หมวดหมู่: {Sub-Category}"}
    )
    
    # โชว์บน Streamlit
    st.pydeck_chart(r, use_container_width=True)

# ==========================================
# 📋 6. โซนล่างสุด: ตารางข้อมูลดิบ
# ==========================================
# ถอด st.divider() ออก เพื่อลดช่องว่าง
st.subheader("📋 RAW DATA EXPLORER (รายชื่อสถานที่ที่กำลังเปิด)")

if len(active_df) > 0:
    show_cols = ['Display Name (TH)', 'Display Name (EN)', 'Main Category', 'Sub-Category', 'open_hour', 'close_hour']
    display_df = active_df[show_cols].copy()
    display_df['ชื่อสถานที่'] = display_df['Display Name (TH)'].fillna(display_df['Display Name (EN)'])
    display_df = display_df[['ชื่อสถานที่', 'Main Category', 'Sub-Category', 'open_hour', 'close_hour']]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.write("ไม่มีข้อมูลสถานที่ในเวลานี้")
