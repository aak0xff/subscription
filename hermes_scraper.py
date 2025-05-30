import random
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
from jinja2 import Template
import shutil
import os


def send_email(new_products):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    print(new_products )

    # 生成 HTML 內容
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .greeting { font-size: 18px; margin-bottom: 20px; }
        .product { border: 1px solid #ccc; border-radius: 10px; padding: 10px; margin-bottom: 20px; display: flex; align-items: center; }
        .product img { max-width: 150px; max-height: 150px; margin-right: 20px; }
        .product-info { }
        .product-info p { margin: 4px 0; }
        .product a { text-decoration: none; color: #007bff; }
    </style>
    </head>
    <body>
        <p class="greeting">親愛的用戶您好！以下是最新的產品資訊，祝您有美好的一天！</p>

            {% for p in new_products %}
            <div class="product">
                <a href="{{ p.url }}"><img src="{{ p.image_url }}" alt="Product Image"></a>
                <div class="product-info">
                <p><strong>商品名稱：</strong>{{ p.name }}</p>
                <p><strong>商品顏色：</strong>{{ p.color }}</p>
                <p><a href="{{ p.url }}">查看商品</a></p>
                </div>
            </div>
            {% endfor %}

        <p>感謝您的支持與關注！</p>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(new_products=new_products)
    print(html_content)
    # Email 設定
    from_addr = "aak.org@gmail.com"
    to_addr = "aak.org@gmail.com"
    bcc_list = ["aak.org@gmail.com", "lisachen0610@gmail.com"]
    subject = "新品上市通知"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    # 發送 Email (以 Gmail 為例)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = from_addr
    smtp_pass = "ilrq ubae vuqc ekni"  # 注意，不是 Gmail 密碼，要產生 App Password

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr]+bcc_list, msg.as_string())

    print("Email 已發送成功！")


#send_email([{'name': 'Herbag Zip cabine拼色手提包', 'color': '風衣卡其色/風暴藍/馬鞍紅', 'url': 'https://www.hermes.com/tw/zh/content/317538-herbag-hermes-bags/', 'image_url': 'https://assets.hermes.com/is/image/hermesedito/P_11_HERBAG_PRODUIT_5?fit=wrap%2C0&wid=414&resMode=sharp2&amp;op_usm=1%2C1%2C6%2C0'}])

def human_delay(min_ms=800, max_ms=2500):
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

def handle_console(msg):
    if "Content Security Policy" not in msg.text:
        print(f"Console: {msg.text}")


def fetch_bag_links():
    all_products = {}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]  # 取現有的 context
        page = context.new_page()
        page.goto("https://www.hermes.com/tw/zh/content/311199-hermes-iconic-bag-lines/")

        page.wait_for_load_state("networkidle")
        print('page loaded')
        page.wait_for_selector("div.block-media")
        page.wait_for_selector("a[href]", timeout=0)
        print('selector loaded')
        human_delay(3000, 10000)


        for _ in range(3):
            print('scrolling down')
            page.mouse.wheel(0, random.randint(500, 1500))
            print('scrolling done')
            human_delay(2000, 4000)

        links = page.query_selector_all("a[href]")
        bag_keywords = ["包", "手提包", "肩背包", "birkin", "kelly", "lindy", "roulis", "picotin", "herbag", "constance"]

        category_url = []
        for link in links:
            href = link.get_attribute("href")
            text = link.inner_text().strip().lower()
            if not href or not text:
                continue
            if any(kw in text for kw in bag_keywords):
                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = "https://www.hermes.com" + href
                print(f"{text} → {full_url}")
                category_url.append(full_url)
        print(f"Total bag links found: {len(category_url)}")

        for url in category_url[2:]:
            print(f"Processing link {url}...")
            page.wait_for_timeout(3000)
            print('go to url', url)
            with page.expect_navigation(timeout=15000):
                page.goto(url)
                print('waiting for product selector')
                try :
                    page.wait_for_selector('[data-swiper-slide-index]', state="attached", timeout=15000)
                    for _ in range(3):
                        page.mouse.wheel(0, random.randint(500, 1500))
                        human_delay(300, 1000)

                    slides = page.query_selector_all('[data-swiper-slide-index]')
                    next_btn = page.query_selector('button.pagination-previous-slide')
                    product_count = len(slides)//3
                    print(f"Found {product_count} products on this page.")

                    for ii in range(3):
                        retry = False
                        for i in range(product_count):
                            slide = page.query_selector('div.swiper-slide-active')
                            if not slide:
                                print(f"No active slide found for {i + 1}/{product_count} on {url}.")
                                retry = True
                                continue

                            source = slide.query_selector('source[media="(min-width: 320px) and (max-width: 414px)"]')
                            if not source:
                                print(f"No source found for {i + 1}/{product_count} on {url}.")
                                retry = True
                                continue

                            image_url = source.get_attribute('srcset')
                            if not image_url:
                                print(f"No image URL found for {i + 1}/{product_count} on {url}.")
                                retry = True
                                continue
                            if image_url.startswith('//'):
                                image_url = 'https:' + image_url

                            product_name_handle = slide.query_selector('p[data-testid="caption"]')
                            if product_name_handle:
                                product_name = product_name_handle.text_content().strip()
                                print(f"Product Name: {product_name}")
                            else:
                                print(f"No product name found for {i + 1}/{product_count} on {url}.")
                                product_name = f'no_name-{len(all_products)+1}'

                            product_color_handle = slide.query_selector('p[data-testid="credits"]')
                            if product_color_handle:
                                product_color = product_color_handle.text_content().strip()
                                print(f"Product Color: {product_color}")
                            else:
                                print(f"No product color found")
                                product_color = f'no_color-{len(all_products)+1}'

                            all_products[ f'{product_name}-{product_color}'] = {
                                'name': product_name,
                                'color': product_color,
                                'url': url,
                                'image_url': image_url
                            }

                            next_btn.click()
                            human_delay(800, 2000)
                        if not retry:
                            break
                        
                    human_delay(2000, 4000)
                except Exception as e:
                    print(f"Error loading products on {url}: {e}")
                    continue


        page.close()
    return all_products


def scrape_hermes():

    count = 0

    while True:

        current_products = None
        try:
            with open('products.json', 'r', encoding='ascii') as f:
                current_products = json.load(f)
            print("Existing products loaded from products.json", len(current_products))
        except:
            print("No existing products.json found, starting fresh.")

        all_products = fetch_bag_links()
        print(f"Total products collected: {len(all_products)}")
        # Save JSON as ASCII (no UTF-8 BOM or binary)

        new_products = []
        product_diff = False
        if current_products:
            for key, value in all_products.items():
                if key not in current_products:
                    print(f"New product found: {value['name']} - {value['color']}")
                    new_products.append(value)
                    product_diff = True

            for key, value in current_products.items():
                if key not in all_products:
                    print(f"Product removed: {value['name']} - {value['color']}")
                    product_diff = True
        else:
            product_diff = True

        if product_diff:
            # if products.json exists, mv to products.json.count
            if os.path.exists('products.json'):
                print(f"products.json exists, moving to products.json.{count}")
                shutil.move('products.json', f'products.json.{count}')
            print("Saving all products to products.json")

            output_path = os.path.join('/tmp', 'products.json')
            with open(output_path, 'w', encoding='ascii') as f:
                json.dump(all_products, f, indent=2, ensure_ascii=True)


        if( len(new_products) ):
            print(f"New products found: {len(new_products)}", "sending email...")
            send_email(new_products)

        if current_products:
            print(f"Previous products loaded: {len(current_products)}")
        print(count, " Done! Good Job.", len(all_products), len(new_products))
        print("Waiting for the next check...")
        print("\n\n\n\n\n")

        count += 1
        human_delay(60000, 120000)  # 每隔1-2分鐘重新抓取一次
