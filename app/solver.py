import asyncio
from playwright.async_api import async_playwright
import json
from bs4 import BeautifulSoup
import httpx
import re

async def submit_answer(submit_url, email, secret, quiz_url, answer):
    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
        "answer": answer
    }

    print("\n[Solver] Submitting answer...")
    print(payload)

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(submit_url, json=payload)

    print("[Solver] Submission response:", r.status_code, r.text)
    return r



async def fetch_page_text(url: str):
    """Open page and return text, html, and an active page object WITHOUT closing browser."""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    print(f"[Solver] Opening page: {url}")
    await page.goto(url, wait_until="networkidle")
    await asyncio.sleep(1)

    text = await page.inner_text("body")
    html = await page.content()

    # Do NOT close anything here
    return text, html, page, browser, p



async def solve_quiz(payload):
    email = payload["email"]
    secret = payload["secret"]
    current_url = payload["url"]

    print(f"[Solver] Starting quiz chain with: {current_url}")

    while True:
        print(f"\n\n===== Solving URL: {current_url} =====")
        try:
            rendered_text, html, page, browser, p = await fetch_page_text(current_url)

        except Exception as e:
            print("[Solver] ERROR loading page:", e)
            break

        print("\n========= PAGE TEXT (Rendered) =========\n")
        print(rendered_text)
        print("\n========================================\n")

        soup = BeautifulSoup(html, "html.parser")
        pre_tag = soup.find("pre")

        # Case 1: Real quiz page (must contain question + submit_url)
        if pre_tag and "\"question\"" in pre_tag.text and "\"submit_url\"" in pre_tag.text:

            try:
                quiz_json = json.loads(pre_tag.text)

                question = quiz_json["question"]
                submit_url = quiz_json["submit_url"]

                print("[Solver] REAL QUIZ QUESTION:", question)
                print("[Solver] REAL SUBMIT URL:", submit_url)

                # For now answer is placeholder; we'll improve soon
                answer = "demo_answer"

                response = await submit_answer(
                    submit_url=submit_url,
                    email=email,
                    secret=secret,
                    quiz_url=current_url,
                    answer=answer
                )

                rjson = response.json()
                
                await browser.close()
                await p.stop()

                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    print("[Solver] Quiz complete!")
                    break

            except Exception as e:
                print("[Solver] Error in real quiz parsing:", e)
                await browser.close()
                await p.stop()
                break

        # Case 2: Demo mode page
        elif "POST this JSON to" in rendered_text:
            try:
                line = [l for l in rendered_text.splitlines() if "POST this JSON to" in l][0]
                submit_url = line.replace("POST this JSON to", "").strip()

                print("[Solver] DEMO PAGE: Found submit URL:", submit_url)

                response = await submit_answer(
                    submit_url=submit_url,
                    email=email,
                    secret=secret,
                    quiz_url=current_url,
                    answer="hello_from_solver"
                )

                rjson = response.json()
                await browser.close()
                await p.stop()

                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    print("[Solver] Demo quiz complete!")
                    break

            except Exception as e:
                print("[Solver] Demo parsing error:", e)
                await browser.close()
                await p.stop()
                break

        # Case 3: Scrape quiz page
        elif "Scrape" in rendered_text and "relative to this page" in rendered_text:
            try:
                print("[Solver] SCRAPE QUIZ DETECTED")

                lines = rendered_text.splitlines()
                scrape_line = [l for l in lines if "Scrape" in l][0]

                relative_url = scrape_line.replace("Scrape", "").replace("(relative to this page).", "").strip()

                from urllib.parse import urljoin
                target_url = urljoin(current_url, relative_url)

                print("[Solver] Scraping via browser:", target_url)

                # Use Playwright – fetch page and keep browser open
                secret_text, _, page2, browser2, p2 = await fetch_page_text(target_url)
                match = re.search(r"\d+", secret_text)
                secret_code = match.group(0)

                secret_code = secret_code.strip()

                print("[Solver] SECRET CODE FOUND:", secret_code)

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                response = await submit_answer(
                    submit_url=submit_url,
                    email=email,
                    secret=secret,
                    quiz_url=current_url,
                    answer=secret_code
                )

                # Close browser for scrape
                await browser2.close()
                await p2.stop()

                rjson = response.json()
                
                await browser.close()
                await p.stop()

                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    print("[Solver] Scrape quiz complete!")
                    break

            except Exception as e:
                print("[Solver] Error in scrape quiz:", e)
                await browser.close()
                await p.stop()
                break

                # Case 4: CSV quiz
        elif "CSV file" in rendered_text or "CSV" in rendered_text:
            try:
                print("[Solver] CSV QUIZ DETECTED")

                # Extract REAL cutoff using browser (JS-rendered)
                try:
                    cutoff = await page.eval_on_selector("#cutoff", "el => parseInt(el.innerText)")
                except:
                    # fallback to text parsing
                    cutoff = None
                    for line in rendered_text.splitlines():
                        if "Cutoff" in line:
                            digits = ''.join(filter(str.isdigit, line))
                            cutoff = int(digits)
                            break

                print("[Solver] REAL Cutoff =", cutoff)

                # Extract CSV link using browser
                csv_links = await page.eval_on_selector_all(
                    "a", "els => els.map(e => e.href)"
                )
                csv_links = [
                    link for link in csv_links
                    if link.lower().endswith(".csv") or "csv" in link.lower()
                ]

                if not csv_links:
                    print("[Solver] No CSV link found.")
                    await browser.close()
                    await p.stop()
                    break

                csv_url = csv_links[0]
                print("[Solver] Downloading CSV from:", csv_url)

                # Download CSV
                import pandas as pd
                from io import StringIO
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(csv_url)

                df = pd.read_csv(StringIO(resp.text))

                # Compute SUM of values > cutoff
                col = df.columns[0]
                answer = int(df[df[col] >= cutoff][col].sum())

                print("[Solver] CSV answer:", answer)

                # Submit
                submit_url = "https://tds-llm-analysis.s-anand.net/submit"
                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()

                await browser.close()
                await p.stop()

                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    print("[Solver] CSV quiz complete!")
                    break

            except Exception as e:
                print("[Solver] Error in CSV quiz:", e)
                await browser.close()
                await p.stop()
                break


        else:
            print("[Solver] No recognizable quiz format.")
            break

    print("[Solver] Finished solving all quiz tasks.")

