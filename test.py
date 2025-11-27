import requests
from lxml import html
from urllib.parse import urljoin, urldefrag
import json

def scrape_website(base_url):
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch base page: {e}")
        return

    tree = html.fromstring(response.content)

    # Find all navigation links (skip anchors)
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

    if not nav_links:
        print("⚠️ No navigation links found.")
        return

    print(f"🔗 Found {len(nav_links)} navigation tabs.")
    all_content = {}

    for i, link in enumerate(nav_links, start=1):
        try:
            print(f"\n[{i}/{len(nav_links)}] Scraping: {link}")
            res = requests.get(link, timeout=10)
            res.raise_for_status()

            page_tree = html.fromstring(res.content)

            # Remove unwanted tags
            for bad_tag in page_tree.xpath('//script | //style | //noscript | //meta | //footer | //header'):
                bad_tag.getparent().remove(bad_tag)

            # Get title
            title = page_tree.xpath('//title/text()')
            title = title[0].strip() if title else "No title"

            # Get visible text
            visible_text = []
            for element in page_tree.xpath('//body//*[not(self::script or self::style)]/text()'):
                text = element.strip()
                if text and not text.startswith('{') and not text.startswith('var'):
                    visible_text.append(text)

            clean_text = ' '.join(visible_text)
            clean_text = ' '.join(clean_text.split())
            truncated_text = clean_text # [:3000] + "..." if len(clean_text) > 3000 else clean_text

            all_content[link] = {"title": title, "text": truncated_text}

        except Exception as e:
            print(f"⚠️ Error scraping {link}: {e}")

    # Save results as TXT
    with open("scraped_content.txt", "w", encoding="utf-8") as f:
        for url, data in all_content.items():
            f.write(f"\n=== {url} ===\n")
            f.write(f"📄 Title: {data['title']}\n\n")
            f.write(data['text'])
            f.write("\n\n" + "=" * 80 + "\n\n")

    # Save results as JSON
    with open("scraped_content.json", "w", encoding="utf-8") as jf:
        json.dump(all_content, jf, indent=4, ensure_ascii=False)

    print("\n✅ Scraping complete.")
    print("📁 Saved structured content to:")
    print("   - scraped_content.txt")
    print("   - scraped_content.json")

# Example usage
if __name__ == "__main__":
    base_website = input("Enter the base website URL (e.g. https://example.com): ").strip()
    scrape_website(base_website)
