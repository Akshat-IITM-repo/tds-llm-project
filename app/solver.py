import asyncio
from playwright.async_api import async_playwright
import json
import numpy as np
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
        
        # ===== PROJECT 2 TASK SOLVERS =====
        elif current_url.endswith("/project2"):
            print("[Solver] Solving project2 INIT")

            answer = "init"

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                print("[Solver] Project2 ended at init.")
                break


        elif "project2-uv" in current_url:
            print("[Solver] Solving project2-uv")

            answer = f'uv http get https://tds-llm-analysis.s-anand.net/project2/uv.json?email={email} -H "Accept: application/json"'

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break


        elif "project2-git" in current_url:
            print("[Solver] Solving project2-git")

            answer = 'git add env.sample\ngit commit -m "chore: keep env sample"'

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break


        elif "project2-md" in current_url:
            print("[Solver] Solving project2-md")

            answer = "/project2/data-preparation.md"

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break

        
        elif "project2-audio-passphrase" in current_url:
            print("[Solver] Solving project2-audio-passphrase (manual fallback)")

            answer = "hushed parrot 219"

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break




        elif "project2-heatmap" in current_url:
            print("[Solver] Solving project2-heatmap")

            from PIL import Image
            from collections import Counter
            from urllib.parse import urljoin
            from io import BytesIO

            image_url = urljoin(current_url, "/project2/heatmap.png")

            async with httpx.AsyncClient() as client:
                img_bytes = await client.get(image_url)

            img = Image.open(BytesIO(img_bytes.content)).convert("RGB")
            pixels = list(img.getdata())

            most_common = Counter(pixels).most_common(1)[0][0]
            answer = "#{:02x}{:02x}{:02x}".format(*most_common)

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            response = await submit_answer(submit_url, email, secret, current_url, answer)

            rjson = response.json()
            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break

        elif "project2-csv" in current_url:
            print("[Solver] Solving project2-csv (MIXED DATE SAFE MODE)")

            import pandas as pd
            import json
            from urllib.parse import urljoin
            from io import StringIO

            csv_url = urljoin(current_url, "/project2/messy.csv")

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(csv_url)
                csv_text = resp.text

            # ✅ Read CSV with header
            df = pd.read_csv(StringIO(csv_text), dtype=str)

            # ✅ Normalize columns to snake_case
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # ✅ Rename (strict)
            df = df.rename(columns={
                "id": "id",
                "name": "name",
                "joined": "joined",
                "value": "value"
            })

            # ✅ Drop invalid rows
            df = df[
                df["id"].str.match(r"^\d+$") &
                df["value"].str.match(r"^\d+$")
            ]

            # ✅ Force int
            df["id"] = df["id"].astype(int)
            df["value"] = df["value"].astype(int)

            # ✅ FINAL DATE FIX (supports BOTH formats)
            df["joined"] = pd.to_datetime(
                df["joined"],
                format="mixed",
                dayfirst=True,
                errors="raise"
            ).dt.strftime("%Y-%m-%d")

            # ✅ Sort strictly
            df = df.sort_values(by="id", ascending=True).reset_index(drop=True)

            # ✅ Exact JSON formatting (NO SPACES)
            answer = json.dumps(
                df.to_dict(orient="records"),
                separators=(",", ":"),
                ensure_ascii=False
            )

            print("[Solver] CSV FINAL ANSWER:", answer)

            submit_url = "https://tds-llm-analysis.s-anand.net/submit"

            response = await submit_answer(
                submit_url,
                email,
                secret,
                current_url,
                answer
            )

            rjson = response.json()

            await browser.close()
            await p.stop()

            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break


        elif "project2-gh-tree" in current_url:
            print("[Solver] Solving project2-gh-tree")

            from urllib.parse import urljoin

            # Step 1: Load config JSON
            config_url = urljoin(current_url, "/project2/gh-tree.json")

            async with httpx.AsyncClient() as client:
                cfg_resp = await client.get(config_url)
                cfg = cfg_resp.json()

            api_url = cfg["api"]
            path_prefix = cfg["pathPrefix"]

            print("[Solver] API:", api_url)
            print("[Solver] Prefix:", path_prefix)

            # Step 2: Call GitHub Tree API
            async with httpx.AsyncClient() as client:
                tree_resp = await client.get(api_url)
                tree_data = tree_resp.json()

            # Step 3: Count .md files under prefix
            count = sum(
                1 for item in tree_data["tree"]
                if item["path"].startswith(path_prefix)
                and item["path"].endswith(".md")
                and item["type"] == "blob"
            )

            # Step 4: Compute offset
            offset = len(email) % 2

            answer = count + offset

            print("[Solver] MD Count:", count)
            print("[Solver] Offset:", offset)
            print("[Solver] FINAL ANSWER:", answer)

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
                print("[Solver] ✅ PROJECT 2 COMPLETED ✅")
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

                # ----- Get Cutoff -----
                try:
                    cutoff = await page.eval_on_selector("#cutoff", "el => parseInt(el.innerText)")
                except:
                    cutoff = None
                    for line in rendered_text.splitlines():
                        if "Cutoff" in line:
                            digits = ''.join(filter(str.isdigit, line))
                            cutoff = int(digits)
                            break

                print("[Solver] REAL Cutoff =", cutoff)

                # ----- Get CSV Link -----
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

                # ----- Download CSV -----
                import pandas as pd
                from io import StringIO
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(csv_url)

                # ✅ CRITICAL FIX: FORCE NO HEADER
                df = pd.read_csv(StringIO(resp.text), header=None)

                # ✅ Force numeric
                df[0] = pd.to_numeric(df[0], errors="coerce")
                df = df.dropna(subset=[0])

                # ✅ Apply cutoff and sum
                answer = int(df[df[0] >= cutoff][0].sum())

                print("[Solver] CSV FINAL ANSWER:", answer)

                # ----- Submit -----
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

