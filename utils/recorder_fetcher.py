import re
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BROWSER_DATA_DIR = str(Path(__file__).parent.parent / "browser_data")


def fetch_recorder_page(url: str) -> dict:
    """
    Google Recorder のページから文字起こし・タイトル・日時を取得する。
    初回はブラウザウィンドウが開くので、Googleアカウントにログインしてください。

    Returns: { "transcript": str, "title": str, "date": str, "time": str }
    """
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,
            args=["--no-first-run", "--no-default-browser-check"],
            locale="ja-JP",
        )
        page = ctx.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # ログインリダイレクトの場合は待機
            if "accounts.google.com" in page.url:
                print("Googleアカウントにログインしてください...")
                page.wait_for_url("**/recorder.google.com/**", timeout=120000)

            # ページの描画を待つ
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)  # JS レンダリング待ち

            title = _extract_title(page)
            date_str, time_str = _extract_datetime(page)
            transcript = _extract_transcript(page)

            return {
                "transcript": transcript,
                "title": title,
                "date": date_str,
                "time": time_str,
            }
        finally:
            ctx.close()


def _extract_title(page) -> str:
    candidates = [
        "h1",
        "[data-recording-title]",
        "input[aria-label*='タイトル']",
        "input[aria-label*='title']",
        ".recording-title",
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                text = (loc.get_attribute("value") or loc.inner_text(timeout=2000)).strip()
                if text and "Recorder" not in text and len(text) > 1:
                    return text
        except Exception:
            pass

    # ページタイトルから
    try:
        title = page.title().replace(" - Google Recorder", "").strip()
        if title and title != "Google Recorder":
            return title
    except Exception:
        pass

    return "会議録音"


def _extract_datetime(page) -> tuple[str, str]:
    today = datetime.today()
    date_str = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%H:%M")

    try:
        body_text = page.inner_text("body", timeout=5000)

        # 日本語日付: 2024年3月21日
        m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", body_text)
        if m:
            y, mo, d = m.groups()
            date_str = f"{y}-{int(mo):02d}-{int(d):02d}"

        # 英語日付: March 21, 2024 / 2024-03-21
        if date_str == today.strftime("%Y-%m-%d"):
            m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", body_text)
            if m2:
                date_str = m2.group(0)

        # 時刻: 10:30
        m3 = re.search(r"\b(\d{1,2}):(\d{2})\b", body_text)
        if m3:
            h, mi = m3.groups()
            if 0 <= int(h) <= 23:
                time_str = f"{int(h):02d}:{mi}"
    except Exception:
        pass

    return date_str, time_str


def _extract_transcript(page) -> str:
    # 戦略1: タイムスタンプ付きのテキストブロックを収集
    transcript = _try_timestamped_blocks(page)
    if transcript:
        return transcript

    # 戦略2: 大きなテキストコンテナを探す
    transcript = _try_large_text_container(page)
    if transcript:
        return transcript

    # 戦略3: body 全体からテキスト抽出
    try:
        return page.inner_text("body", timeout=5000)
    except Exception:
        return ""


def _try_timestamped_blocks(page) -> str:
    """タイムスタンプ(0:00 形式)のある行を含むテキストブロックを探す"""
    try:
        result = page.evaluate("""() => {
            const TIME_RE = /^\\d{1,2}:\\d{2}/;
            const allEls = document.querySelectorAll('div, p, span, li');
            let best = '';

            for (const el of allEls) {
                // 子要素がないか、テキストのみの要素
                const directText = Array.from(el.childNodes)
                    .filter(n => n.nodeType === Node.TEXT_NODE)
                    .map(n => n.textContent.trim())
                    .join('');
                if (!directText) continue;

                if (TIME_RE.test(directText)) {
                    // タイムスタンプ要素の親から全テキストを取得
                    const parent = el.closest('[class]') || el.parentElement;
                    if (parent && parent.innerText.length > best.length) {
                        best = parent.innerText;
                    }
                }
            }
            return best;
        }""")
        if result and len(result) > 100:
            return _clean_transcript(result)
    except Exception:
        pass
    return ""


def _try_large_text_container(page) -> str:
    """最も多くのテキストを含む要素を探す"""
    try:
        result = page.evaluate("""() => {
            const candidates = document.querySelectorAll(
                'main, article, [role="main"], .transcript, ' +
                '[class*="transcript"], [class*="content"], [class*="body"]'
            );
            let best = '';
            for (const el of candidates) {
                if (el.innerText && el.innerText.length > best.length) {
                    best = el.innerText;
                }
            }
            if (best.length < 100) {
                // フォールバック: 最大テキスト要素
                const divs = document.querySelectorAll('div');
                for (const d of divs) {
                    if (d.children.length < 20 && d.innerText && d.innerText.length > best.length) {
                        best = d.innerText;
                    }
                }
            }
            return best;
        }""")
        if result and len(result) > 100:
            return _clean_transcript(result)
    except Exception:
        pass
    return ""


def _clean_transcript(text: str) -> str:
    """UI のノイズを除去し、本文テキストを整形する"""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        # 極端に短い行（UI ボタンなど）を除外
        if not line or len(line) <= 1:
            continue
        # ナビゲーション系の除外
        if line in {"メニュー", "検索", "戻る", "共有", "削除", "編集",
                    "Menu", "Search", "Back", "Share", "Delete", "Edit"}:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
