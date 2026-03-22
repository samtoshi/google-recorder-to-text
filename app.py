import streamlit as st
from datetime import date, datetime
from dotenv import load_dotenv
from utils.text_corrector import correct_transcript
from utils.minutes_generator import generate_minutes
from utils.html_generator import generate_meeting_html, generate_index_html
from utils.drive_manager import DriveManager
from utils.recorder_fetcher import fetch_recorder_page

load_dotenv()

st.set_page_config(
    page_title="Google Recorder 議事録ジェネレーター",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Google Recorder 議事録ジェネレーター")
st.caption("Google Recorder の URL を入力するか、文字起こしを貼り付けて議事録を自動生成します。")

# --- ステップ管理 ---
if "step" not in st.session_state:
    st.session_state.step = 1

def reset():
    for key in ["step", "corrected_text", "corrections", "minutes", "meeting_html"]:
        st.session_state.pop(key, None)

# ==============================
# STEP 1: 入力
# ==============================
if st.session_state.step >= 1:
    with st.expander("STEP 1：会議情報と文字起こしの入力", expanded=(st.session_state.step == 1)):

        # --- URL 自動取得 ---
        st.subheader("Google Recorder URL から自動取得（任意）")
        url_col, btn_col = st.columns([4, 1])
        with url_col:
            recorder_url = st.text_input(
                "URL",
                placeholder="https://recorder.google.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                label_visibility="collapsed",
                key="recorder_url",
            )
        with btn_col:
            fetch_btn = st.button("取得", use_container_width=True, disabled=not recorder_url)

        if fetch_btn and recorder_url:
            with st.spinner("ブラウザで取得中...（初回はログインが必要です）"):
                try:
                    fetched = fetch_recorder_page(recorder_url)
                    st.session_state["_fetched"] = fetched
                    st.success("✅ 取得完了！下のフォームに自動入力しました。")
                except Exception as e:
                    st.error(f"取得エラー: {e}")

        fetched = st.session_state.get("_fetched", {})
        st.divider()

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("会議情報")
            meeting_title = st.text_input(
                "議題 / 会議名", placeholder="例：週次チームミーティング",
                value=fetched.get("title", ""), key="title",
            )
            # 日付
            _default_date = date.today()
            if fetched.get("date"):
                try:
                    _default_date = datetime.strptime(fetched["date"], "%Y-%m-%d").date()
                except Exception:
                    pass
            meeting_date = st.date_input("日付", value=_default_date, key="date")

            # 時刻
            _default_time = datetime.now().replace(second=0, microsecond=0).time()
            if fetched.get("time"):
                try:
                    _default_time = datetime.strptime(fetched["time"], "%H:%M").time()
                except Exception:
                    pass
            meeting_time = st.time_input("時刻", value=_default_time, key="time")

            participants = st.text_input("参加者", placeholder="例：山田、鈴木、田中", key="participants")
            additional_notes = st.text_area("補足情報（任意）", placeholder="プロジェクト名、背景など", height=80, key="notes")

        with col2:
            st.subheader("文字起こしテキスト")
            transcript = st.text_area(
                "Google Recorder からコピーしたテキストを貼り付け",
                height=320,
                placeholder="ここにテキストを貼り付け...",
                label_visibility="collapsed",
                value=fetched.get("transcript", ""),
                key="transcript",
            )
            st.caption(f"{len(transcript):,} 文字")

        can_proceed = meeting_title and participants and transcript
        if st.button("文字起こしを修正する →", type="primary", disabled=not can_proceed):
            with st.spinner("文字起こしを校正中..."):
                try:
                    corrected, corrections = correct_transcript(transcript)
                    st.session_state.corrected_text = corrected
                    st.session_state.corrections = corrections
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")

# ==============================
# STEP 2: 修正確認
# ==============================
if st.session_state.step >= 2:
    with st.expander("STEP 2：修正箇所の確認", expanded=(st.session_state.step == 2)):
        corrections = st.session_state.get("corrections", [])

        if corrections:
            st.success(f"✅ {len(corrections)} 箇所を修正しました")
            st.subheader("修正箇所リスト")

            for i, c in enumerate(corrections, 1):
                cols = st.columns([2, 0.3, 2, 3])
                cols[0].markdown(f"<span style='color:#c62828'>{c['original']}</span>", unsafe_allow_html=True)
                cols[1].markdown("→")
                cols[2].markdown(f"<span style='color:#2e7d32'>**{c['corrected']}**</span>", unsafe_allow_html=True)
                cols[3].caption(c['reason'])
        else:
            st.info("修正箇所はありませんでした。")

        with st.expander("修正済みテキストを確認"):
            st.text_area("", value=st.session_state.get("corrected_text", ""), height=200, disabled=True, key="corrected_preview")

        if st.button("議事録を生成する →", type="primary"):
            with st.spinner("議事録を生成中..."):
                try:
                    minutes = generate_minutes(
                        transcript=st.session_state.corrected_text,
                        title=st.session_state.title,
                        meeting_date=st.session_state.date.strftime("%Y年%m月%d日"),
                        participants=st.session_state.participants,
                        additional_notes=st.session_state.get("notes", ""),
                    )
                    st.session_state.minutes = minutes
                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")

# ==============================
# STEP 3: 議事録確認 & 保存
# ==============================
if st.session_state.step >= 3:
    with st.expander("STEP 3：議事録の確認と保存", expanded=(st.session_state.step == 3)):
        tab1, tab2 = st.tabs(["プレビュー", "Markdown"])
        with tab1:
            st.markdown(st.session_state.minutes)
        with tab2:
            st.code(st.session_state.minutes, language="markdown")

        st.divider()
        col_dl, col_drive = st.columns(2)

        # ローカルダウンロード
        with col_dl:
            metadata = {
                "title": st.session_state.title,
                "date": st.session_state.date.strftime("%Y年%m月%d日"),
                "time": st.session_state.time.strftime("%H:%M"),
                "participants": st.session_state.participants,
            }
            html_content = generate_meeting_html(
                minutes_md=st.session_state.minutes,
                corrected_transcript=st.session_state.corrected_text,
                corrections=st.session_state.corrections,
                metadata=metadata,
            )
            filename = (
                f"議事録_{st.session_state.title}_"
                f"{st.session_state.date.strftime('%Y%m%d')}.html"
            )
            st.download_button(
                "HTMLでダウンロード",
                data=html_content,
                file_name=filename,
                mime="text/html",
                use_container_width=True,
            )

        # Google Drive 保存
        with col_drive:
            if st.button("Google Drive に保存して index を更新", type="primary", use_container_width=True):
                with st.spinner("Google Drive に保存中..."):
                    try:
                        drive = DriveManager()

                        dt = datetime.combine(st.session_state.date, st.session_state.time)
                        drive_filename = f"{dt.strftime('%Y%m%d_%H%M')}_{st.session_state.title}.html"

                        drive_meta = {
                            "title": st.session_state.title,
                            "date": st.session_state.date.strftime("%Y-%m-%d"),
                            "time": st.session_state.time.strftime("%H:%M"),
                            "participants": st.session_state.participants,
                        }

                        # 議事録HTML を保存
                        entry = drive.save_meeting(html_content, drive_filename, drive_meta)

                        # meetings.json を更新
                        meetings = drive.load_meetings()
                        # 同じIDがあれば更新、なければ追加
                        meetings = [m for m in meetings if m["id"] != entry["id"]]
                        meetings.append(entry)
                        meetings.sort(key=lambda m: (m["date"], m["time"]), reverse=True)
                        drive.save_metadata(meetings)

                        # index.html を更新
                        index_html = generate_index_html(meetings)
                        index_url = drive.update_index(index_html)

                        st.success("✅ Google Drive に保存しました！")
                        st.markdown(f"**議事録ファイル:** [{entry['title']}]({entry['web_url']})")
                        st.markdown(f"**カレンダー index:** [index.html を開く]({index_url})")

                    except Exception as e:
                        st.error(f"エラー: {e}")

        st.button("最初からやり直す", on_click=reset)
