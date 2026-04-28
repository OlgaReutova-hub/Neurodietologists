import json
import base64
from pathlib import Path

import fitz
import streamlit as st


st.set_page_config(
    page_title="Нейродиетолог",
    page_icon="🥗",
    layout="wide",
)


MEAL_TYPE_MAP = {
    "Офисное меню": "office",
    "Домашнее меню": "home",
    "Перекус в городе": "city_snack",
}

INDICATOR_COLORS = {
    "green": "#4CAF50",
    "yellow": "#F4B400",
    "red": "#DB4437",
}

SEX_OPTIONS = ["Женщина", "Мужчина"]
KCAL_OPTIONS = [1200, 1300, 1400, 1500]
MEAL_TYPE_OPTIONS = ["Офисное меню", "Домашнее меню", "Перекус в городе"]


@st.cache_data
def load_data() -> dict:
    data_path = Path(__file__).parent / "data" / "menus.json"
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_scenario(data: dict, kcal: int, meal_type: str) -> dict | None:
    for scenario in data.get("scenarios", []):
        if scenario.get("kcal") == kcal and scenario.get("meal_type") == meal_type:
            return scenario
    return None


def render_deficit_item(name: str, percent: int, indicator: str) -> None:
    color = INDICATOR_COLORS.get(indicator, "#9CA3AF")
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                <span style="font-weight:600; color:#111827;">{name}</span>
                <span style="display:flex; align-items:center; gap:10px; font-weight:700; color:#111827; font-size:1.4rem;">
                    {percent}%
                    <span style="
                        width:12px;
                        height:12px;
                        border-radius:50%;
                        display:inline-block;
                        background:{color};
                    "></span>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    .mvp-section-title {
        margin-top: 0.1rem;
        margin-bottom: 0.5rem;
    }
    .deficit-vertical-center {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 8px;
    }
    .memo-btn-wrap {
        margin-top: 26px;
        margin-bottom: 8px;
    }
    .memo-btn-wrap .stButton > button {
        font-weight: 700;
        font-size: 1rem;
        padding: 0.62rem 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.18);
    }
    @media (max-width: 1024px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Нейродиетолог")

data = load_data()
project_root = Path(__file__).parent
memo_dir = project_root / "data"


def get_memo_pdf_path_for_kcal(kcal: int) -> Path | None:
    prefix = f"{kcal} "
    for pdf_path in memo_dir.glob("*.pdf"):
        if pdf_path.name.startswith(prefix):
            return pdf_path
    return None


@st.cache_data
def load_memo_pdf_base64(pdf_path: str, file_mtime_ns: int) -> str:
    _ = file_mtime_ns
    pdf_bytes = Path(pdf_path).read_bytes()
    return base64.b64encode(pdf_bytes).decode("utf-8")


@st.cache_data
def render_pdf_pages_as_png(pdf_path: str, file_mtime_ns: int) -> list[bytes]:
    _ = file_mtime_ns
    pages: list[bytes] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            pages.append(pix.tobytes("png"))
    return pages


@st.dialog("Памятка для пациента", width="large")
def show_pdf_memo_dialog(kcal: int) -> None:
    memo_pdf_path = get_memo_pdf_path_for_kcal(kcal)
    if memo_pdf_path is None or not memo_pdf_path.exists():
        st.error(f"Файл памятки для {kcal} ккал не найден.")
        return

    pdf_base64 = load_memo_pdf_base64(
        str(memo_pdf_path),
        memo_pdf_path.stat().st_mtime_ns,
    )
    st.caption("Предпросмотр отображается как изображения страниц для совместимости с браузерами.")
    page_images = render_pdf_pages_as_png(
        str(memo_pdf_path),
        memo_pdf_path.stat().st_mtime_ns,
    )
    for i, image_bytes in enumerate(page_images, start=1):
        st.image(image_bytes, caption=f"Страница {i}", use_container_width=True)
    st.download_button(
        "Скачать PDF",
        data=base64.b64decode(pdf_base64),
        file_name=memo_pdf_path.name,
        mime="application/pdf",
        use_container_width=True,
    )

if "applied_sex" not in st.session_state:
    st.session_state.applied_sex = "Женщина"
if "applied_kcal" not in st.session_state:
    st.session_state.applied_kcal = 1300
if "applied_meal_type" not in st.session_state:
    st.session_state.applied_meal_type = "office"
if "show_result" not in st.session_state:
    st.session_state.show_result = False

with st.container():
    st.markdown("<h3 class='mvp-section-title'>Параметры</h3>", unsafe_allow_html=True)
    input_col1, input_col2, input_col3, input_col4 = st.columns([1.0, 1.0, 1.2, 0.8])

    with input_col1:
        selected_sex = st.radio(
            "Пол",
            options=SEX_OPTIONS,
            index=SEX_OPTIONS.index(st.session_state.applied_sex),
            horizontal=True,
        )

    with input_col2:
        kcal_label_options = [f"{k} ккал" for k in KCAL_OPTIONS]
        selected_kcal_label = st.selectbox(
            "Дневная калорийность",
            kcal_label_options,
            index=KCAL_OPTIONS.index(st.session_state.applied_kcal),
        )
        selected_kcal = int(selected_kcal_label.split()[0])

    with input_col3:
        default_meal_type_label = next(
            label for label, value in MEAL_TYPE_MAP.items() if value == st.session_state.applied_meal_type
        )
        selected_meal_type_label = st.selectbox(
            "Тип питания",
            MEAL_TYPE_OPTIONS,
            index=MEAL_TYPE_OPTIONS.index(default_meal_type_label),
        )
        selected_meal_type = MEAL_TYPE_MAP[selected_meal_type_label]

    with input_col4:
        st.write("")
        st.write("")
        show_button = st.button("Показать рацион", type="primary", use_container_width=True)

if show_button:
    st.session_state.applied_sex = selected_sex
    st.session_state.applied_kcal = selected_kcal
    st.session_state.applied_meal_type = selected_meal_type
    st.session_state.show_result = True

if st.session_state.show_result:
    scenario = find_scenario(
        data,
        st.session_state.applied_kcal,
        st.session_state.applied_meal_type,
    )

    if scenario is None:
        st.error("Сценарий с такими параметрами не найден.")
    else:
        sex_key = "female" if st.session_state.applied_sex == "Женщина" else "male"
        deficits = scenario["deficits"]
        symptoms = scenario["symptoms"]

        left_col, right_col = st.columns([1.2, 1])

        with left_col:
            with st.container(border=True):
                st.subheader("Меню на день")
                st.markdown(f"**Калорийность:** {st.session_state.applied_kcal} ккал")
                st.markdown("**Завтрак**")
                for item in scenario["meals"]["breakfast"]:
                    st.markdown(f"- {item}")

                st.markdown("**Обед**")
                for item in scenario["meals"]["lunch"]:
                    st.markdown(f"- {item}")

                st.markdown("**Перекус**")
                for item in scenario["meals"]["snack"]:
                    st.markdown(f"- {item}")

                st.markdown("**Ужин**")
                for item in scenario["meals"]["dinner"]:
                    st.markdown(f"- {item}")

        with right_col:
            with st.container(border=True):
                st.subheader("Дефицит микронутриентов")
                st.markdown("Поступление микронутриентов - % от суточной нормы")
                fiber_percent = deficits["fiber"][f"{sex_key}_percent"]
                fiber_indicator = deficits["fiber"][f"{sex_key}_indicator"]
                iron_percent = deficits["iron"][f"{sex_key}_percent"]
                iron_indicator = deficits["iron"][f"{sex_key}_indicator"]

                st.markdown('<div class="deficit-vertical-center">', unsafe_allow_html=True)
                render_deficit_item("Пищевые волокна", fiber_percent, fiber_indicator)
                render_deficit_item("Железо", iron_percent, iron_indicator)
                st.markdown("</div>", unsafe_allow_html=True)

            with st.container(border=True, height=540):
                st.subheader("Возможные проявления дефицита")
                st.markdown("**Пищевые волокна**")
                fiber_items = [item for item in symptoms["fiber"] if item != "Чувство, что не наедаешься"][:3]
                for item in fiber_items:
                    if item != "Чувство, что не наедаешься":
                        st.markdown(f"- {item}")

                st.markdown("**Железо**")
                iron_items = [item for item in symptoms["iron"] if item != "Снижение энергии"][:3]
                for item in iron_items:
                    if item != "Снижение энергии":
                        st.markdown(f"- {item}")

        st.info(scenario["summary"][sex_key])

st.markdown('<div class="memo-btn-wrap">', unsafe_allow_html=True)
spacer_left, memo_col, spacer_right = st.columns([1.6, 1.2, 1.6])
with memo_col:
    if st.button("Памятка для пациента", use_container_width=False, type="primary"):
        show_pdf_memo_dialog(st.session_state.applied_kcal)
st.markdown("</div>", unsafe_allow_html=True)
