#!/usr/bin/env python3
"""トヨタレンタカー「片道GO!」の新着車両を検知して ntfy でスマホに通知する（GitHub Actions 用）．"""
import html, json, os, re, sys, urllib.request
from datetime import datetime
from pathlib import Path

URL = "https://cp.toyota.jp/rentacar/"
DIR = Path(__file__).resolve().parent
STATE = DIR / "seen.json"
LOG = DIR / "new_items.log"


def text(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def field(block, cls):
    m = re.search(r'class="%s">(.*?)</div>' % re.escape(cls), block, re.S)
    if not m:
        return ""
    return re.sub(r"^(出発 店舗|返却 店舗|車種|車両条件)\s*", "", text(m.group(1)))


def fetch_items():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    # 出発側リストだけを見る（到着側リストは同じ車両の並べ替え）
    start = page.split('id="service-items-shop-type-return"')[0]
    items = {}
    for block in re.findall(r'<li class="service-item".*?</li>', start, re.S):
        it = {
            "from": field(block, "service-item__shop-start"),
            "to": field(block, "service-item__shop-return"),
            "car": field(block, "service-item__info__car-type"),
            "cond": field(block, "service-item__info__condition"),
            "date": text(re.search(r'service-item__date">(.*?)</div>', block, re.S).group(1)).replace("出発期間", "").strip(),
            "tel": field(block, "service-item__reserve-tel"),
        }
        key = "|".join([it["from"], it["to"], it["car"], it["date"]])
        items[key] = it
    return items


def notify(title, msg):
    push(title, msg)


def push(title, msg):
    """ntfy.sh 経由でスマホに通知する（環境変数 NTFY_TOPIC があるときだけ）．"""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    body = json.dumps({"topic": topic, "title": title, "message": msg, "click": URL}).encode()
    req = urllib.request.Request("https://ntfy.sh/", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"ntfy 送信失敗: {e}", file=sys.stderr)


def main():
    items = fetch_items()
    if not items:
        notify("片道GO! 監視エラー", "車両が1件も取得できませんでした（ページ構造が変わった可能性）")
        sys.exit(1)
    first_run = not STATE.exists()
    seen = set() if first_run else set(json.loads(STATE.read_text()))
    new = [items[k] for k in items if k not in seen]
    STATE.write_text(json.dumps(sorted(set(items) | seen), ensure_ascii=False, indent=1))
    if first_run:
        print(f"初回実行: {len(items)} 件を既知として登録")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with LOG.open("a") as f:
        for it in new:
            f.write(f"{now}\t{it['from']} → {it['to']}\t{it['car']}\t{it['cond']}\t{it['date']}\t{it['tel']}\n")
    for it in new[:5]:
        notify("片道GO! 新着", f"{it['car']}\n{it['from']} → {it['to']}\n{it['date']}")
    if len(new) > 5:
        notify("片道GO! 新着", f"ほか {len(new) - 5} 件．{URL}")
    print(f"{now} 新着 {len(new)} 件 / 掲載 {len(items)} 件")


if __name__ == "__main__":
    main()
