from flask import Flask, render_template, request, send_file
import requests
from lxml import html
from urllib.parse import urljoin, urldefrag
from docx import Document
from docx.shared import Pt, Inches
import os

app = Flask(__name__)

# ✅ Store last scraped content for preview
last_scraped_content = {}

def scrape_website(base_url):
    global last_scraped_content
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

    for link in nav_links:
        try:
            res = requests.get(link, timeout=10)
            res.raise_for_status()
            page_tree = html.fromstring(res.content)

            # Remove unnecessary tags
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
            clean_text = ' '.join(clean_text.split())

            # ✅ Only include successful pages
            if clean_text:
                all_content[link] = {"title": title, "text": clean_text}
                stats["success"] += 1
                stats["success_links"].append(link)
            else:
                stats["failed"] += 1
                stats["failed_links"].append(link)

        except Exception as e:
            # ✅ Skip adding failed pages to content
            stats["failed"] += 1
            stats["failed_links"].append(link)

    # ✅ Save only successful pages for preview
    last_scraped_content = {k: v for k, v in all_content.items() if v['text'].strip()}

        # ✅ Save successful pages only to DOCX
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.left_margin = Inches(0.4)
    section.right_margin = Inches(0.4)
    section.top_margin = Inches(0.4)
    section.bottom_margin = Inches(0.4)
    section._sectPr.xpath('./w:cols')[0].set('num', '3')

    # Add title of document
    title_para = doc.add_paragraph("Scraped Website Content")
    title_para.style = doc.styles['Normal']
    title_para.paragraph_format.space_before = Pt(0)
    title_para.paragraph_format.space_after = Pt(0)
    title_para.paragraph_format.line_spacing = 1
    for run in title_para.runs:
        run.font.size = Pt(3)
        run.bold = False

    for _, data in last_scraped_content.items():
        # ✅ Add title (as plain text, no blank lines)
        p_title = doc.add_paragraph(data['title'])
        p_title.style = doc.styles['Normal']
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(0)
        p_title.paragraph_format.line_spacing = 1
        for run in p_title.runs:
            run.font.size = Pt(3)
            run.bold = False

        # ✅ Add paragraph text (no blank lines)
        p_body = doc.add_paragraph(data['text'])
        p_body.style = doc.styles['Normal']
        p_body.paragraph_format.space_before = Pt(0)
        p_body.paragraph_format.space_after = Pt(0)
        p_body.paragraph_format.line_spacing = 1
        for run in p_body.runs:
            run.font.size = Pt(3)


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


@app.route("/preview")
def preview():
    if not last_scraped_content:
        return render_template("index.html", message="⚠️ Please scrape a website first.")
    return render_template("index.html", preview_content=last_scraped_content, download=True)


@app.route("/download")
def download_file():
    path = "scraped_content.docx"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        return "⚠️ File not found. Please scrape a website first."


if __name__ == "__main__":
    # app.run(debug=True)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

