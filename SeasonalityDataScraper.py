from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

def get_top_season(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("div.tw-rating-card", timeout=15000)
        time.sleep(2)

        soup = BeautifulSoup(page.content(), "html.parser")

        card = None
        for c in soup.find_all("div", class_="tw-rating-card"):
            label = c.find("span", class_="tw-rating-card-label")
            if label and "When To Wear" in label.text:
                card = c
                break

        if not card:
            return None

        season_votes = {}
        for sdiv in card.select("div.flex.flex-col.items-center.cursor-pointer"):
            spans = sdiv.find_all("span")
            season_name, votes = None, 0
            for span in spans:
                classes = span.get("class", [])
                if "font-medium" in classes and season_name is None:
                    season_name = span.text.strip().lower()
                if "tabular-nums" in classes:
                    try:
                        votes = int(span.text.strip())
                    except ValueError:
                        pass
            if season_name:
                season_votes[season_name] = votes

        SEASONS = {"winter", "spring", "summer", "fall"}
        return max(
            {k: v for k, v in season_votes.items() if k in SEASONS},
            key=season_votes.get
        ) if any(k in SEASONS for k in season_votes) else "none"
    except Exception as e:
        print(f"  Error on {url}: {e}")
        return "none"

def main():
    df = pd.read_csv("./data/fra_cleaned.csv", sep=';', decimal=',', encoding='cp1252')

    if "top_season" not in df.columns:
        df["top_season"] = None

    urls = df["url"].tolist()
    total = len(urls)

    start_index = 0
    for i in range(total):
        if pd.isna(df.at[i, "top_season"]):
            start_index = i
            break

    remaining = total - start_index
    print(f"Total: {total} | Resuming from: {start_index} | Remaining: {remaining}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()

        for i in range(start_index, total):
            url = urls[i]
            print(f"[{i+1}/{total}] {url}")

            season = get_top_season(page, url)
            df.at[i, "top_season"] = season
            print(f"top season:{season}")

            if (i + 1) % 50 == 0:
                df.to_csv("./data/fra_with_season.csv", index=False)
                print(f"Progress saved at {i+1}/{total}")

            time.sleep(random.uniform(3, 5)) # get past the cloudfare... hopefully

        browser.close()

    df.to_csv("./data/fra_with_season.csv", index=False)
    print("Finished Scraping Data")

if __name__ == "__main__":
    main()