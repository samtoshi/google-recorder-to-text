import json
from datetime import datetime
import markdown


def generate_meeting_html(
    minutes_md: str,
    corrected_transcript: str,
    corrections: list[dict],
    metadata: dict,
) -> str:
    minutes_html = markdown.markdown(minutes_md, extensions=["tables"])

    corrections_html = ""
    if corrections:
        rows = "".join(
            f"""<tr>
              <td class="orig">{c['original']}</td>
              <td class="arrow">→</td>
              <td class="fixed">{c['corrected']}</td>
              <td class="reason">{c['reason']}</td>
            </tr>"""
            for c in corrections
        )
        corrections_html = f"""
        <section class="corrections">
          <h2>修正箇所 ({len(corrections)}件)</h2>
          <table>
            <thead><tr>
              <th>元のテキスト</th><th></th><th>修正後</th><th>理由</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>"""

    transcript_escaped = corrected_transcript.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{metadata['title']} - {metadata['date']}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Meiryo, sans-serif; background: #f5f7fa; color: #333; }}
    .header {{
      background: linear-gradient(135deg, #1a1a2e, #16213e);
      color: white; padding: 24px 40px;
    }}
    .header h1 {{ font-size: 22px; font-weight: 600; }}
    .header .meta {{ margin-top: 8px; font-size: 14px; opacity: 0.8; }}
    .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
    section {{ background: white; border-radius: 12px; padding: 28px; margin-bottom: 24px;
               box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
    h2 {{ font-size: 16px; font-weight: 600; color: #1a1a2e;
          border-bottom: 2px solid #e8f0fe; padding-bottom: 10px; margin-bottom: 18px; }}
    .minutes h2 {{ font-size: 20px; }}
    .minutes h3 {{ font-size: 16px; color: #333; margin: 18px 0 8px; }}
    .minutes ul, .minutes ol {{ padding-left: 20px; margin: 8px 0; }}
    .minutes li {{ margin: 4px 0; line-height: 1.7; }}
    .minutes table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    .minutes th {{ background: #f0f4ff; padding: 8px 12px; text-align: left;
                   border: 1px solid #dde3f0; font-size: 13px; }}
    .minutes td {{ padding: 8px 12px; border: 1px solid #dde3f0; font-size: 13px; }}
    .minutes p {{ line-height: 1.8; margin: 8px 0; }}
    table.corrections-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .corrections table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .corrections th {{ background: #fff3e0; padding: 8px 12px; text-align: left;
                       border: 1px solid #ffe0b2; }}
    .corrections td {{ padding: 8px 12px; border: 1px solid #f0f0f0; vertical-align: top; }}
    .corrections .orig {{ color: #c62828; }}
    .corrections .fixed {{ color: #2e7d32; }}
    .corrections .arrow {{ color: #999; text-align: center; }}
    .corrections .reason {{ color: #666; font-size: 12px; }}
    .transcript {{ background: #fafafa; }}
    .transcript pre {{ white-space: pre-wrap; word-break: break-all; font-size: 13px;
                       line-height: 1.8; color: #444; font-family: Meiryo, sans-serif; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>📝 {metadata['title']}</h1>
    <div class="meta">
      📅 {metadata['date']} &nbsp;|&nbsp; 👥 {metadata['participants']}
    </div>
  </div>
  <div class="container">
    <section class="minutes">
      {minutes_html}
    </section>
    {corrections_html}
    <section class="transcript">
      <h2>修正済み文字起こし</h2>
      <pre>{transcript_escaped}</pre>
    </section>
  </div>
</body>
</html>"""


def generate_index_html(meetings: list[dict]) -> str:
    meetings_json = json.dumps(meetings, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>議事録ライブラリ</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Meiryo, sans-serif; display: flex;
            height: 100vh; overflow: hidden; background: #f5f7fa; color: #333; }}

    /* Left panel */
    .left-panel {{
      width: 280px; min-width: 280px;
      background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
      color: white; overflow-y: auto; padding: 20px 16px;
    }}
    .panel-title {{ font-size: 16px; font-weight: 600; margin-bottom: 20px;
                    padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.15); }}

    /* Calendar */
    .calendar-month {{ margin-bottom: 24px; }}
    .month-header {{ display: flex; justify-content: space-between; align-items: center;
                     margin-bottom: 10px; }}
    .month-label {{ font-size: 14px; font-weight: 600; }}
    .month-nav {{ background: none; border: 1px solid rgba(255,255,255,0.3);
                  color: white; width: 24px; height: 24px; border-radius: 4px;
                  cursor: pointer; font-size: 12px; }}
    .month-nav:hover {{ background: rgba(255,255,255,0.15); }}
    .day-names {{ display: grid; grid-template-columns: repeat(7, 1fr);
                  gap: 2px; margin-bottom: 4px; }}
    .day-name {{ text-align: center; font-size: 10px; opacity: 0.6; padding: 2px 0; }}
    .days-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }}
    .day {{
      text-align: center; padding: 5px 2px; font-size: 12px;
      border-radius: 6px; cursor: default; line-height: 1.2;
    }}
    .day.has-meeting {{
      background: rgba(74,144,226,0.25); cursor: pointer;
      border: 1px solid rgba(74,144,226,0.5);
    }}
    .day.has-meeting:hover {{ background: rgba(74,144,226,0.5); }}
    .day.selected {{ background: #4a90e2 !important; border-color: #4a90e2 !important; }}
    .day .day-num {{ font-weight: 600; }}
    .day .day-time {{ font-size: 9px; opacity: 0.8; }}
    .day.today .day-num {{ color: #ffd700; }}
    .empty-day {{ padding: 5px; }}

    /* Meeting list for days with multiple */
    .meeting-list {{ margin-top: 12px; }}
    .meeting-item {{
      background: rgba(255,255,255,0.08); border-radius: 6px;
      padding: 8px 10px; margin-bottom: 6px; cursor: pointer; font-size: 12px;
    }}
    .meeting-item:hover {{ background: rgba(255,255,255,0.15); }}
    .meeting-item.active {{ background: #4a90e2; }}
    .meeting-item .m-time {{ font-size: 11px; opacity: 0.8; margin-bottom: 2px; }}
    .meeting-item .m-title {{ font-weight: 500; }}

    /* Right panel */
    .right-panel {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
    .right-header {{
      background: white; padding: 14px 24px; border-bottom: 1px solid #e0e0e0;
      display: flex; align-items: center; gap: 12px;
    }}
    .right-header h2 {{ font-size: 16px; font-weight: 600; flex: 1; }}
    .open-btn {{
      background: #4a90e2; color: white; border: none; padding: 6px 14px;
      border-radius: 6px; cursor: pointer; font-size: 13px; text-decoration: none;
      display: inline-block;
    }}
    .open-btn:hover {{ background: #357abd; }}
    iframe {{ flex: 1; border: none; width: 100%; }}
    .welcome {{
      flex: 1; display: flex; align-items: center; justify-content: center;
      flex-direction: column; gap: 12px; color: #999;
    }}
    .welcome-icon {{ font-size: 48px; }}
    .welcome-text {{ font-size: 16px; }}
  </style>
</head>
<body>
  <div class="left-panel">
    <div class="panel-title">📅 議事録ライブラリ</div>
    <div id="calendar"></div>
    <div class="meeting-list" id="meeting-list"></div>
  </div>
  <div class="right-panel">
    <div class="right-header" id="right-header" style="display:none;">
      <h2 id="selected-title"></h2>
      <a id="open-link" class="open-btn" href="#" target="_blank">新しいタブで開く ↗</a>
    </div>
    <div class="welcome" id="welcome">
      <div class="welcome-icon">📋</div>
      <div class="welcome-text">カレンダーから日付を選択してください</div>
    </div>
    <iframe id="preview-frame" style="display:none;"></iframe>
  </div>

  <script>
    const meetings = {meetings_json};

    // Build lookup: date → [meeting, ...]
    const byDate = {{}};
    meetings.forEach(m => {{
      if (!byDate[m.date]) byDate[m.date] = [];
      byDate[m.date].push(m);
    }});

    const today = new Date();
    let currentYear = today.getFullYear();
    let currentMonth = today.getMonth();

    function renderCalendar() {{
      const cal = document.getElementById('calendar');
      cal.innerHTML = '';

      // Find months that have meetings
      const months = new Set(meetings.map(m => m.date.substring(0, 7)));
      // Show current month + months with data
      const allMonths = new Set([...months, `${{currentYear}}-${{String(currentMonth+1).padStart(2,'0')}}`]);
      const sortedMonths = [...allMonths].sort().reverse();

      sortedMonths.forEach(ym => {{
        const [y, mo] = ym.split('-').map(Number);
        renderMonth(cal, y, mo - 1);
      }});
    }}

    function renderMonth(container, year, month) {{
      const div = document.createElement('div');
      div.className = 'calendar-month';

      const label = `${{year}}年${{month+1}}月`;
      div.innerHTML = `<div class="month-header"><div class="month-label">${{label}}</div></div>`;

      const dayNames = div.appendChild(document.createElement('div'));
      dayNames.className = 'day-names';
      ['日','月','火','水','木','金','土'].forEach(d => {{
        const dn = document.createElement('div');
        dn.className = 'day-name';
        dn.textContent = d;
        dayNames.appendChild(dn);
      }});

      const grid = div.appendChild(document.createElement('div'));
      grid.className = 'days-grid';

      const firstDay = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();

      for (let i = 0; i < firstDay; i++) {{
        const empty = document.createElement('div');
        empty.className = 'empty-day';
        grid.appendChild(empty);
      }}

      for (let d = 1; d <= daysInMonth; d++) {{
        const dateStr = `${{year}}-${{String(month+1).padStart(2,'0')}}-${{String(d).padStart(2,'0')}}`;
        const dayDiv = document.createElement('div');
        dayDiv.className = 'day';

        const isToday = (year === today.getFullYear() && month === today.getMonth() && d === today.getDate());
        if (isToday) dayDiv.classList.add('today');

        if (byDate[dateStr]) {{
          dayDiv.classList.add('has-meeting');
          const times = byDate[dateStr].map(m => m.time).join(' ');
          dayDiv.innerHTML = `<div class="day-num">${{d}}</div><div class="day-time">${{times}}</div>`;
          dayDiv.dataset.date = dateStr;
          dayDiv.addEventListener('click', () => selectDate(dateStr, dayDiv));
        }} else {{
          dayDiv.innerHTML = `<div class="day-num">${{d}}</div>`;
        }}
        grid.appendChild(dayDiv);
      }}

      container.appendChild(div);
    }}

    let selectedDayEl = null;

    function selectDate(dateStr, dayEl) {{
      // Remove previous selection
      if (selectedDayEl) selectedDayEl.classList.remove('selected');
      dayEl.classList.add('selected');
      selectedDayEl = dayEl;

      const ms = byDate[dateStr];
      const list = document.getElementById('meeting-list');
      list.innerHTML = `<div style="font-size:12px;opacity:0.7;margin-bottom:8px;">${{dateStr}}</div>`;

      ms.forEach((m, i) => {{
        const item = document.createElement('div');
        item.className = 'meeting-item';
        item.innerHTML = `<div class="m-time">${{m.time}}</div><div class="m-title">${{m.title}}</div>`;
        item.addEventListener('click', () => {{
          document.querySelectorAll('.meeting-item').forEach(el => el.classList.remove('active'));
          item.classList.add('active');
          showMeeting(m);
        }});
        list.appendChild(item);
        if (ms.length === 1) {{
          item.classList.add('active');
          showMeeting(m);
        }}
      }});
    }}

    function showMeeting(m) {{
      document.getElementById('welcome').style.display = 'none';
      document.getElementById('right-header').style.display = 'flex';
      document.getElementById('selected-title').textContent = `${{m.date}} ${{m.time}} - ${{m.title}}`;
      document.getElementById('open-link').href = m.preview_url;
      const frame = document.getElementById('preview-frame');
      frame.style.display = 'block';
      frame.src = m.preview_url;
    }}

    renderCalendar();
  </script>
</body>
</html>"""
