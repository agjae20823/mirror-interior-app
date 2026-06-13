import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import base64
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ===========================
# 기본 설정
# ===========================
st.set_page_config(page_title="원목 거울 인테리어", layout="wide")

MIRROR_TYPES = {
    "전신거울": "full_length",
    "벽거울(원형)": "wall_round",
    "벽거울(사각)": "wall_rect",
    "탁상거울": "table",
}

COLORS = {
    "멀바우": "melbau",
    "오크": "oak",
    "블랙": "black",
    "화이트": "white",
}

# 거울 이미지가 들어있는 폴더 (app.py와 같은 위치에 있어야 함)
MIRROR_DIR = "사진들"


# ===========================
# 유틸 함수
# ===========================
def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def search_naver_shopping(query: str, max_items: int = 6):
    """
    다나와 검색 결과를 셀레니움으로 크롤링.
    """
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    results = []

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.danawa.com/dsearch.php?query={encoded_query}"
        driver.get(url)
        time.sleep(3)

        # 디버깅용
        driver.save_screenshot("debug_danawa.png")
        with open("debug_danawa.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        items = driver.find_elements(By.CSS_SELECTOR, "ul.product_list > li.prod_item")[:max_items]

        for item in items:
            try:
                title_el = item.find_element(By.CSS_SELECTOR, "p.prod_name a")
                title = title_el.text.strip()
                href = title_el.get_attribute("href")
            except Exception:
                continue

            try:
                price = item.find_element(By.CSS_SELECTOR, "p.price_sect strong").text.strip()
                price = price + "원"
            except Exception:
                price = "가격 정보 없음"

            try:
                image = item.find_element(By.CSS_SELECTOR, "a.thumb_link img").get_attribute("src")
            except Exception:
                image = None

            if title:
                results.append({"title": title, "price": price, "link": href, "image": image})

    finally:
        driver.quit()

    return results


# ===========================
# 화면 구성
# ===========================
st.title("🪞 나만의 원목 거울 인테리어")
st.caption("내 공간 사진에 거울을 배치해보고, 마음에 드는 종류는 추천 상품으로 바로 비교해요.")

uploaded_file = st.file_uploader("1. 인테리어(공간) 사진을 업로드하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.session_state["bg_image_bytes"] = uploaded_file.getvalue()

if "bg_image_bytes" not in st.session_state:
    st.info("먼저 인테리어 사진을 업로드해주세요.")
    st.stop()

import io
bg_image = Image.open(io.BytesIO(st.session_state["bg_image_bytes"])).convert("RGBA")
MAX_WIDTH = 800
if bg_image.width > MAX_WIDTH:
    ratio = MAX_WIDTH / bg_image.width
    bg_image = bg_image.resize((MAX_WIDTH, int(bg_image.height * ratio)))

st.subheader("2. 거울 종류 / 색상 선택")
col1, col2 = st.columns(2)
with col1:
    mirror_type_kr = st.selectbox("거울 종류", list(MIRROR_TYPES.keys()))
with col2:
    color_kr = st.selectbox("색상 (멀바우 / 오크 / 블랙 / 화이트)", list(COLORS.keys()))

mirror_type = MIRROR_TYPES[mirror_type_kr]
color = COLORS[color_kr]
mirror_path = f"{MIRROR_DIR}/{mirror_type}_{color}.png"

try:
    mirror_img = Image.open(mirror_path)
except FileNotFoundError:
    st.error(f"거울 이미지 파일을 찾을 수 없습니다: {mirror_path}")
    st.stop()

mirror_b64 = img_to_base64(mirror_path)

st.subheader("3. 거울을 드래그 / 크기조절 / 회전해서 배치해보세요")
st.caption("이미지를 클릭하면 모서리 핸들이 나옵니다. 드래그로 이동, 모서리로 크기/회전 조절이 가능해요.")

bg_buffer = io.BytesIO()
bg_image.convert("RGB").save(bg_buffer, format="PNG")
bg_b64 = base64.b64encode(bg_buffer.getvalue()).decode()

init_drawing = {
    "version": "4.4.0",
    "objects": [
        {
            "type": "image",
            "version": "4.4.0",
            "left": 0,
            "top": 0,
            "width": bg_image.width,
            "height": bg_image.height,
            "scaleX": 1,
            "scaleY": 1,
            "angle": 0,
            "selectable": False,
            "evented": False,
            "src": f"data:image/png;base64,{bg_b64}",
            "crossOrigin": "anonymous",
        },
        {
            "type": "image",
            "version": "4.4.0",
            "left": 100,
            "top": 100,
            "width": mirror_img.width,
            "height": mirror_img.height,
            "scaleX": 0.3,
            "scaleY": 0.3,
            "angle": 0,
            "src": f"data:image/png;base64,{mirror_b64}",
            "crossOrigin": "anonymous",
        },
    ],
}

canvas_result = st_canvas(
    initial_drawing=init_drawing,
    drawing_mode="transform",
    height=bg_image.height,
    width=bg_image.width,
    key=f"canvas_{mirror_type}_{color}",
)

st.divider()

st.subheader("4. 이 거울 종류로 상품 추천받기")
if st.button("추천 상품 검색하기"):
    search_query = f"{mirror_type_kr} {color_kr} 원목"
    with st.spinner(f"'{search_query}' 검색 중... (셀레니움 구동에 시간이 좀 걸릴 수 있어요)"):
        results = search_naver_shopping(search_query)

    if results:
        st.success(f"'{search_query}' 검색 결과 {len(results)}개")
        cols = st.columns(3)
        for idx, item in enumerate(results):
            with cols[idx % 3]:
                if item["image"]:
                     st.image(item["image"], use_column_width=True)
                st.markdown(f"**{item['title']}**")
                st.markdown(f"💰 {item['price']}")
                st.markdown(f"[상품 보러가기]({item['link']})")
    else:
        st.warning(
            "검색 결과를 가져오지 못했습니다. "
            "다나와 페이지 구조가 변경되어 CSS 선택자를 다시 확인해야 할 수 있습니다."
        )