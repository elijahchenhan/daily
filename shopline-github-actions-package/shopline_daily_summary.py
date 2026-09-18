#!/usr/bin/env python3
"""
彙整飛航模飾 Shopline 訂單業績（可統計「昨天整天」或「今天截至目前」），並透過 LINE Messaging API 廣播訊息。

與 Claude 排程版本的差異：
- Token 一律從環境變數讀取（SHOPLINE_TOKEN / LINE_TOKEN），不寫死在檔案裡，
  請在 GitHub repo 的 Settings > Secrets and variables > Actions 設定同名的 Secrets。
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SHOPLINE_TOKEN = os.environ.get("SHOPLINE_TOKEN")
LINE_TOKEN = os.environ.get("LINE_TOKEN")

if not SHOPLINE_TOKEN or not LINE_TOKEN:
    sys.exit("錯誤：找不到環境變數 SHOPLINE_TOKEN 或 LINE_TOKEN，請確認 GitHub Actions Secrets 已設定。")

SHOPLINE_API = "https://open.shopline.io/v1/orders"
LINE_BROADCAST_API = "https://api.line.me/v2/bot/message/broadcast"

TAIPEI = timezone(timedelta(hours=8))


def fetch_orders(created_after, created_before):
    items = []
    page = 1
    while True:
        params = {
            "per_page": 100,
            "page": page,
            "created_after": created_after,
            "created_before": created_before,
        }
        url = SHOPLINE_API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {SHOPLINE_TOKEN}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        batch = data.get("items", [])
        items.extend(batch)
        pagination = data.get("pagination", {})
        total_pages = pagination.get("total_pages", 1)
        if page >= total_pages or not batch:
            break
        page += 1
    return items


def compute_stats(items):
    confirmed = [o for o in items if o.get("status") == "confirmed"]
    refunded = [o for o in items if o.get("order_payment", {}).get("status") == "refunded"]
    pending = [o for o in items if o.get("status") == "pending"]

    net_revenue = sum(o["total"]["dollars"] for o in confirmed)
    net_order_count = len(confirmed)
    aov = (net_revenue / net_order_count) if net_order_count else 0

    refunded_count = len(refunded)
    refunded_amount = sum(o["total"]["dollars"] for o in refunded)

    prod_rev = defaultdict(float)
    prod_qty = defaultdict(int)
    for o in confirmed:
        for it in o.get("subtotal_items", []):
            title = it.get("title_translations", {}).get("zh-hant") or it.get("sku") or "未命名商品"
            prod_rev[title] += it.get("total", {}).get("dollars", 0)
            prod_qty[title] += it.get("quantity", 0)
    top5 = sorted(prod_rev.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "net_revenue": net_revenue,
        "net_order_count": net_order_count,
        "aov": aov,
        "refunded_count": refunded_count,
        "refunded_amount": refunded_amount,
        "pending_count": len(pending),
        "top5": [(name, rev, prod_qty[name]) for name, rev in top5],
    }


def money(n):
    return f"NT$ {n:,.0f}"


def metric_row(label, value, value_color="#1A1A2E", value_weight="bold"):
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": label, "size": "sm", "color": "#8A8FA3", "flex": 4},
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "color": value_color,
                "weight": value_weight,
                "align": "end",
                "flex": 5,
                "wrap": True,
            },
        ],
    }


def separator():
    return {"type": "separator", "margin": "md", "color": "#EAEAF0"}


def build_flex_message(stats, day_label, title="📊 業績日報"):
    body_contents = [
        metric_row("淨營業額", money(stats["net_revenue"]), value_color="#1DB446", value_weight="bold"),
        separator(),
        metric_row("淨訂單數", f"{stats['net_order_count']} 筆"),
        metric_row("平均客單價", money(stats["aov"])),
        separator(),
        metric_row(
            "退款",
            f"{stats['refunded_count']} 筆／{money(stats['refunded_amount'])}",
            value_color="#E63946",
        ),
    ]

    if stats["pending_count"]:
        body_contents.append(
            {
                "type": "text",
                "text": f"另有 {stats['pending_count']} 筆待付款，未列入以上統計",
                "size": "xxs",
                "color": "#B0B4C0",
                "margin": "sm",
            }
        )

    body_contents.append(separator())
    body_contents.append(
        {"type": "text", "text": "🔥 熱賣 TOP5（依營收排序）", "weight": "bold", "size": "md", "margin": "md"}
    )

    if stats["top5"]:
        for i, (name, rev, qty) in enumerate(stats["top5"], 1):
            body_contents.append(
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{i}. {name}",
                            "size": "sm",
                            "wrap": True,
                            "weight": "bold",
                            "color": "#1A1A2E",
                        },
                        {
                            "type": "text",
                            "text": f"{money(rev)}（{qty} 件）",
                            "size": "xs",
                            "color": "#8A8FA3",
                            "margin": "xs",
                        },
                    ],
                }
            )
    else:
        body_contents.append({"type": "text", "text": "（昨日無成立訂單）", "size": "sm", "color": "#8A8FA3"})

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#2E3A59",
            "paddingAll": "20px",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": title, "color": "#FFFFFF", "size": "xl", "weight": "bold"},
                {
                    "type": "text",
                    "text": f"Shopline ・ {day_label}",
                    "color": "#B8C4E0",
                    "size": "sm",
                    "margin": "sm",
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "20px",
            "contents": body_contents,
        },
    }

    clean_title = title.split(" ", 1)[-1] if " " in title else title
    alt_text = f"飛航模飾{clean_title} {day_label}｜淨營業額 {money(stats['net_revenue'])}"
    return {"type": "flex", "altText": alt_text, "contents": bubble}


def send_line_broadcast(flex_message):
    body = json.dumps({"messages": [flex_message]}).encode("utf-8")
    req = urllib.request.Request(
        LINE_BROADCAST_API,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8")


def main():
    dry_run = "--dry-run" in sys.argv
    period = "today" if "--period" in sys.argv and sys.argv[sys.argv.index("--period") + 1] == "today" else "yesterday"

    now_taipei = datetime.now(TAIPEI)

    if period == "today":
        today = now_taipei.date()
        start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=TAIPEI)
        end = now_taipei
        day_label = f"{today.strftime('%Y/%m/%d')} 截至 {now_taipei.strftime('%H:%M')}"
        title = "📈 今日即時業績"
    else:
        yesterday = (now_taipei - timedelta(days=1)).date()
        start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=TAIPEI)
        end = start + timedelta(days=1)
        day_label = yesterday.strftime("%Y/%m/%d")
        title = "📊 業績日報"

    created_after = start.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    created_before = end.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    items = fetch_orders(created_after, created_before)
    stats = compute_stats(items)
    flex_message = build_flex_message(stats, day_label, title=title)

    print(f"{title} ({day_label})")
    print(f"淨營業額：{money(stats['net_revenue'])}")
    print(f"淨訂單數：{stats['net_order_count']} 筆")
    print(f"平均客單價：{money(stats['aov'])}")
    print(f"退款：{stats['refunded_count']} 筆／{money(stats['refunded_amount'])}")
    if stats["pending_count"]:
        print(f"（另有 {stats['pending_count']} 筆待付款，未列入以上統計）")
    print("熱賣 TOP5：")
    for i, (name, rev, qty) in enumerate(stats["top5"], 1):
        print(f"  {i}. {name}｜{money(rev)}（{qty} 件）")

    if dry_run:
        print("\n[dry-run] 未送出 LINE 訊息")
        return

    status, resp_body = send_line_broadcast(flex_message)
    print(f"\nLINE broadcast HTTP status: {status}")
    print(resp_body)


if __name__ == "__main__":
    main()
