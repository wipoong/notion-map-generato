from flask import Flask, send_file, redirect
import pandas as pd
import folium
import requests
from notion_client import Client
import os
from datetime import datetime

app = Flask(__name__)

# 🔐 환경 변수 불러오기
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 🎨 일차별 색상 설정
day_colors = {
    "1일차": "yellow",
    "2일차": "red",
    "3일차": "orenge",
    "4일차": "blue"
}

# 📍 지오코딩 함수
def geocode_place(place_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&key={GOOGLE_API_KEY}"
    resp = requests.get(url).json()
    if resp['status'] == 'OK':
        loc = resp['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    return None, None

# 📊 Notion DB 데이터 불러오기
def fetch_data():
    notion = Client(auth=NOTION_TOKEN)
    results = notion.databases.query(database_id=DATABASE_ID)
    rows = []
    for page in results['results']:
        props = page['properties']
        name = props['이름']['title'][0]['plain_text'] if props['이름']['title'] else ''
        kind = props['종류']['select']['name'] if props['종류']['select'] else ''
        day = props['일차']['select']['name'] if props['일차']['select'] else ''
        if not day:
            continue
        rows.append([name, kind, day])
    return pd.DataFrame(rows, columns=["이름", "종류", "일차"])

# 🗺️ 지도 생성 함수
def generate_map():
    df = fetch_data()
    m = folium.Map(location=[33.38, 126.53], zoom_start=10)

    for _, row in df.iterrows():
        lat, lng = geocode_place(row["이름"])
        if lat and lng:
            popup_html = f"<b>{row['이름']}</b><br><i>{row['종류']}</i>"
            day_number = row['일차'].replace("일차", "")
            color = day_colors.get(row['일차'], '#555')
            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.DivIcon(
                    icon_size=(28, 28),
                    icon_anchor=(14, 14),
                    html=f"""
                    <div style="
                        background-color: {color};
                        color: white;
                        font-size: 12px;
                        font-weight: bold;
                        border-radius: 50%;
                        width: 28px;
                        height: 28px;
                        text-align: center;
                        line-height: 28px;">
                        {day_number}
                    </div>
                    """
                )
            ).add_to(m)

    m.save("notion_jeju_map.html")

# 🔁 지도 재생성 + 캐시 우회용 redirect
@app.route("/map")
def trigger_and_redirect():
    generate_map()
    ts = datetime.utcnow().timestamp()
    return redirect(f"/map-static?t={ts}", code=302)

# 🌐 정적 지도 서빙 (Notion Embed용)
@app.route("/map-static")
def serve_map():
    return send_file("notion_jeju_map.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)