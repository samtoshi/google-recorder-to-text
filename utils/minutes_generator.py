import anthropic
from typing import Generator


SYSTEM_PROMPT = """あなたは優秀な議事録作成アシスタントです。
会議の文字起こしテキストを受け取り、構造化された日本語の議事録を作成します。

以下のフォーマットで議事録を作成してください：

---
# 議事録

## 基本情報
- **日時**: {date}
- **参加者**: {participants}
- **議題**: {title}

## 議論の要点
（会議で話し合われた主な内容を箇条書きで）

## 決定事項
（会議で決まったことを箇条書きで）

## アクションアイテム
| 内容 | 担当者 | 期限 |
|------|--------|------|
| ... | ... | ... |

## 次回予定
（次回の会議や確認事項があれば記載）

## その他・備考
（特筆事項があれば記載）
---

文字起こしに担当者や期限の情報がない場合は「未定」と記載してください。
情報が不足している項目は「記録なし」と記載してください。
"""


def generate_minutes(
    transcript: str,
    title: str,
    meeting_date: str,
    participants: str,
    additional_notes: str = "",
) -> Generator[str, None, None]:
    client = anthropic.Anthropic()

    user_message = f"""以下の会議の文字起こしから議事録を作成してください。

【会議情報】
- 議題: {title}
- 日時: {meeting_date}
- 参加者: {participants}
{"- 補足情報: " + additional_notes if additional_notes else ""}

【文字起こしテキスト】
{transcript}
"""

    system = SYSTEM_PROMPT.format(
        date=meeting_date,
        participants=participants,
        title=title,
    )

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text
