import streamlit as st
from datetime import date
from dotenv import load_dotenv
from utils.minutes_generator import generate_minutes

load_dotenv()

st.set_page_config(
    page_title="Google Recorder 議事録ジェネレーター",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Google Recorder 議事録ジェネレーター")
st.caption("Google Recorder の文字起こしテキストを貼り付けて、議事録を自動生成します。")

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("会議情報")

    meeting_title = st.text_input(
        "議題 / 会議名",
        placeholder="例：週次チームミーティング",
    )

    meeting_date = st.date_input(
        "日時",
        value=date.today(),
    )

    participants = st.text_input(
        "参加者",
        placeholder="例：山田、鈴木、田中",
    )

    additional_notes = st.text_area(
        "補足情報（任意）",
        placeholder="プロジェクト名、背景情報など",
        height=80,
    )

with col2:
    st.subheader("文字起こしテキスト")
    transcript = st.text_area(
        "Google Recorder からコピーしたテキストを貼り付けてください",
        height=300,
        placeholder="ここにテキストを貼り付け...",
        label_visibility="collapsed",
    )
    char_count = len(transcript)
    st.caption(f"{char_count:,} 文字")

st.divider()

generate_button = st.button(
    "議事録を生成",
    type="primary",
    use_container_width=True,
    disabled=not (meeting_title and participants and transcript),
)

if not meeting_title or not participants:
    st.info("議題と参加者を入力してください。")
elif not transcript:
    st.info("文字起こしテキストを貼り付けてください。")

if generate_button:
    with st.spinner("議事録を生成中..."):
        try:
            minutes = generate_minutes(
                transcript=transcript,
                title=meeting_title,
                meeting_date=meeting_date.strftime("%Y年%m月%d日"),
                participants=participants,
                additional_notes=additional_notes,
            )

            st.session_state["minutes"] = minutes
            st.session_state["meeting_title"] = meeting_title
            st.session_state["meeting_date"] = meeting_date

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

if "minutes" in st.session_state:
    st.divider()
    st.subheader("生成された議事録")

    tab1, tab2 = st.tabs(["プレビュー", "Markdown ソース"])

    with tab1:
        st.markdown(st.session_state["minutes"])

    with tab2:
        st.code(st.session_state["minutes"], language="markdown")

    filename = (
        f"議事録_{st.session_state['meeting_title']}_"
        f"{st.session_state['meeting_date'].strftime('%Y%m%d')}.md"
    )

    st.download_button(
        label="Markdown でダウンロード",
        data=st.session_state["minutes"],
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
    )
