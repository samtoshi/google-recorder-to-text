import anthropic
import json
import re


CORRECTION_SYSTEM = """あなたは音声文字起こしの校正専門家です。
Google Recorderの自動文字起こしテキストを受け取り、以下の観点で修正してください：

- 同音異義語の誤変換（例：「意向」→「移行」）
- 文脈から明らかな誤認識（例：「きかい」が文脈上「機械」なのに「機会」になっている）
- 言葉の区切りの誤り
- 固有名詞の誤変換

修正しないもの：
- 話し言葉特有の表現（「えーと」「なんか」など）
- 文法的に不完全でも意味が通じるもの
- 確信が持てないもの

必ず以下のJSON形式のみで返答してください（他のテキストは不要）：
{
  "corrected_text": "修正後の全文",
  "corrections": [
    {
      "original": "元のテキスト",
      "corrected": "修正後のテキスト",
      "reason": "修正理由"
    }
  ]
}
"""


def correct_transcript(transcript: str) -> tuple[str, list[dict]]:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        system=CORRECTION_SYSTEM,
        messages=[{"role": "user", "content": transcript}],
    )

    raw = message.content[0].text.strip()

    # JSON部分を抽出（余分なテキストがあっても対応）
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    data = json.loads(raw)
    return data["corrected_text"], data.get("corrections", [])
