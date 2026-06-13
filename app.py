import streamlit as st
from PIL import Image
import base64
import time
import io
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
def compose_image(bg: Image.Image, mirror: Image.Image, x_pct: int, y_pct: int,
                   scale_pct: int, angle: int) -> Image.Image:
    """배경 이미지 위에 거울 이미지를 위치/크기/회전 적용해서 합성"""
    bg2 = bg.convert("RGBA").copy()

    mw, mh = mirror.size
    new_w = max(1, int(mw * scale_pct / 100))
    new_h = max(1, int(mh * scale_pct / 100))
    resized = mirror.resize((new_w, new_h))
    rotated = resized.rotate(angle, expand=True)

    cx = int(bg2.width * x_pct / 100)
    cy = int(bg2.height * y_pct / 100)
    x = cx - rotated.width // 2
    y = cy - rotated.height // 2

    bg2.paste(rotated, (x, y), rotated)
    return bg2


def search_naver_shopping(query: str, max_items: int = 6):
    """
    다나와 검색 결과를 셀레니움으로 크롤링.
    """
    import shutil

    options = Options()
    options.add_argument("--headless=new")
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

    # Streamlit Cloud(Linux)에 apt로 설치된 chromium 사용
    chromium_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chromium_path:
        options.binary_location = chromium_path

    chromedriver_path = shutil.which("chromedriver")
    if chromedriver_path:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    else:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    results = []

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.danawa.com/dsearch.php?query={encoded_query}"
        driver.get(url)
        time.sleep(3)

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
    mirror_img = Image.open(mirror_path).convert("RGBA")
except FileNotFoundError:
    st.error(f"거울 이미지 파일을 찾을 수 없습니다: {mirror_path}")
    st.stop()

st.subheader("3. 거울 위치 / 크기 / 회전 조절")

col_a, col_b = st.columns([1, 2])

with col_a:
    x_pct = st.slider("가로 위치 (%)", 0, 100, 50)
    y_pct = st.slider("세로 위치 (%)", 0, 100, 50)
    scale_pct = st.slider("크기 (%)", 5, 100, 30)
    angle = st.slider("회전 (도)", -180, 180, 0)

with col_b:
    composed = compose_image(bg_image, mirror_img, x_pct, y_pct, scale_pct, angle)
    st.image(composed, use_column_width=True)

st.divider()

st.subheader("4. 이 거울 종류로 상품 추천받기")
if st.button("추천 상품 검색하기"):
    search_query = f"{mirror_type_kr} {color_kr} 원목"
    with st.spinner(f"'{search_query}' 검색 중... "):
        try:
            results = search_naver_shopping(search_query)
        except Exception as e:
            results = []
            st.error(f"크롤링 중 오류가 발생했습니다: {e}")

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
