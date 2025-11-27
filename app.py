from flask import Flask, render_template, request, send_file
import requests
from lxml import html
from urllib.parse import urljoin, urldefrag
from docx import Document
import os

app = Flask(__name__)

def scrape_website(base_url):
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "success_links": [],
        "failed_links": []
    }

    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return None, {"error": f"❌ Failed to fetch base page: {e}"}

    tree = html.fromstring(response.content)
    nav_links = []
    navbars = tree.xpath('//nav | //ul[contains(@class,"nav")] | //div[contains(@class,"nav")]')

    for nav in navbars:
        links = nav.xpath('.//a/@href')
        for href in links:
            if not href or href.startswith("#"):
                continue
            full_url = urljoin(base_url, href)
            full_url, _ = urldefrag(full_url)
            if full_url not in nav_links and base_url in full_url:
                nav_links.append(full_url)

    stats["total"] = len(nav_links)
    if not nav_links:
        return None, {"error": "⚠️ No navigation links found."}

    all_content = {}

    for i, link in enumerate(nav_links, start=1):
        try:
            res = requests.get(link, timeout=10)
            res.raise_for_status()
            page_tree = html.fromstring(res.content)

            # Remove unwanted tags
            for bad_tag in page_tree.xpath('//script | //style | //noscript | //meta | //footer | //header'):
                bad_tag.getparent().remove(bad_tag)

            title = page_tree.xpath('//title/text()')
            title = title[0].strip() if title else "No title"

            visible_text = []
            for element in page_tree.xpath('//body//*[not(self::script or self::style)]/text()'):
                text = element.strip()
                if text and not text.startswith('{') and not text.startswith('var'):
                    visible_text.append(text)

            clean_text = ' '.join(visible_text)
            all_content[link] = {"title": title, "text": clean_text}

            stats["success"] += 1
            stats["success_links"].append(link)

        except Exception as e:
            all_content[link] = {"title": "Error", "text": f"⚠️ Error scraping {link}: {e}"}
            stats["failed"] += 1
            stats["failed_links"].append(link)

    # ✅ Save to DOCX
    doc = Document()
    doc.add_heading("Scraped Website Content", level=1)
    for url, data in all_content.items():
        doc.add_heading(data['title'], level=2)
        doc.add_paragraph(f"URL: {url}", style='Intense Quote')
        doc.add_paragraph(data['text'])
        doc.add_paragraph("\n" + "-" * 80 + "\n")

    output_path = "scraped_content.docx"
    doc.save(output_path)

    return output_path, stats


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if not url:
            return render_template("index.html", message="⚠️ Please enter a valid URL.")

        result, stats = scrape_website(url)
        if result and os.path.exists(result):
            return render_template(
                "index.html",
                message="✅ Scraping complete!",
                download=True,
                stats=stats
            )
        else:
            return render_template("index.html", message=stats.get("error", "⚠️ Scraping failed."))

    return render_template("index.html")


@app.route("/download")
def download_file():
    path = "scraped_content.docx"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return "⚠️ File not found. Please scrape a website first."


if __name__ == "__main__":
    app.run(debug=True)
