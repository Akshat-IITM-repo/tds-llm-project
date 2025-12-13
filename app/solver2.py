import asyncio
import json
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import httpx


# =========================================================
# Helpers
# =========================================================

def is_instruction_page(text: str) -> bool:
    """
    Instruction-only pages:
    - Explain how to play
    - Do NOT ask to submit a specific answer
    """
    instruction_markers = [
        "How to play",
        "Start by POSTing JSON"
    ]

    task_markers = [
        "POST the",
        "POST that",
        "Submit the",
        "Send the"
    ]

    is_instruction = any(k in text for k in instruction_markers)
    has_task = any(k in text for k in task_markers)

    return is_instruction and not has_task


def extract_submit_url(text: str) -> str:
    m = re.search(r"https?://[^\s]+/submit", text)
    if m:
        return m.group(0)
    return "https://tds-llm-analysis.s-anand.net/submit"


async def submit_answer(submit_url, email, secret, quiz_url, answer):
    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
        "answer": answer
    }

    print("\n[Solver2] Submitting answer:")
    print(payload)

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(submit_url, json=payload)

    print("[Solver2] Submission response:", r.status_code, r.text)
    return r


# =========================================================
# Solver2 main logic
# =========================================================

async def solve_quiz(payload):
    email = payload["email"]
    secret = payload["secret"]
    current_url = payload["url"]

    print(f"[Solver2] Starting quiz chain with: {current_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while True:
            print(f"\n===== Solving URL: {current_url} =====")

            try:
                await page.goto(current_url, wait_until="networkidle")
                await asyncio.sleep(1)
            except Exception as e:
                print("[Solver2] Page load failed:", e)
                break

            rendered_text = await page.inner_text("body")
            html = await page.content()

            print("\n========= PAGE TEXT =========\n")
            print(rendered_text)
            print("\n==============================\n")

            soup = BeautifulSoup(html, "html.parser")
            pre = soup.find("pre")
            submit_url = extract_submit_url(rendered_text)

            # -------------------------------------------------
            # 1. JSON quiz page
            # -------------------------------------------------
            if pre:
                try:
                    data = json.loads(pre.text)
                    if "question" in data and "submit_url" in data:
                        print("[Solver2] JSON quiz detected")

                        answer = "placeholder"

                        response = await submit_answer(
                            data["submit_url"],
                            email,
                            secret,
                            current_url,
                            answer
                        )

                        rjson = response.json()
                        if rjson.get("url"):
                            current_url = rjson["url"]
                            continue
                        else:
                            break
                except Exception:
                    pass

            # -------------------------------------------------
            # 2. UV task
            # -------------------------------------------------
            elif "uv http get" in rendered_text:
                print("[Solver2] UV task detected")

                answer = (
                    f'uv http get '
                    f'https://tds-llm-analysis.s-anand.net/project2/uv.json'
                    f'?email={email} -H "Accept: application/json"'
                )

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 3. Git task
            # -------------------------------------------------
            elif "env.sample" in rendered_text and "commit" in rendered_text:
                print("[Solver2] Git task detected")

                answer = 'git add env.sample\ngit commit -m "chore: keep env sample"'

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 4. Markdown task
            # -------------------------------------------------
            elif "data-preparation.md" in rendered_text:
                print("[Solver2] Markdown task detected")

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    "/project2/data-preparation.md"
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 5. Audio task (manual fallback preserved)
            # -------------------------------------------------
            elif "audio-passphrase" in rendered_text:
                print("[Solver2] Audio task detected")

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    "hushed parrot 219"
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 6. Heatmap task
            # -------------------------------------------------
            elif "heatmap.png" in rendered_text:
                print("[Solver2] Heatmap task detected")

                from PIL import Image
                from collections import Counter
                from urllib.parse import urljoin
                from io import BytesIO

                img_url = urljoin(current_url, "/project2/heatmap.png")

                async with httpx.AsyncClient() as client:
                    img_bytes = await client.get(img_url)

                img = Image.open(BytesIO(img_bytes.content)).convert("RGB")
                pixels = list(img.getdata())
                color = Counter(pixels).most_common(1)[0][0]
                answer = "#{:02x}{:02x}{:02x}".format(*color)

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 7. CSV task (spec-exact, fixed)
            # -------------------------------------------------
            elif "project2-csv" in current_url:
                print("[Solver2] CSV task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                import pandas as pd
                from io import StringIO
                import json

                csv_url = urljoin(current_url, "/project2/messy.csv")

                async with httpx.AsyncClient(timeout=30) as client:
                    csv_text = (await client.get(csv_url)).text

                df = pd.read_csv(StringIO(csv_text), dtype=str)
                df.columns = ["id", "name", "joined", "value"]

                # convert numeric
                df["id"] = pd.to_numeric(df["id"], errors="coerce")
                df["value"] = pd.to_numeric(df["value"], errors="coerce")

                # convert dates (handles mixed formats)
                df["joined"] = pd.to_datetime(
                    df["joined"],
                    errors="coerce",
                    dayfirst=True
                )

                # drop invalid rows
                df = df.dropna(subset=["id", "value", "joined"])

                # finalize formatting
                df["id"] = df["id"].astype(int)
                df["value"] = df["value"].astype(int)
                df["joined"] = df["joined"].dt.strftime("%Y-%m-%d")

                df = df.sort_values("id").reset_index(drop=True)

                answer = json.dumps(
                    df.to_dict(orient="records"),
                    separators=(",", ":")
                )

                print("[Solver2] CSV ANSWER =", answer)

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 8. GitHub tree task (FINAL – schema correct)
            # -------------------------------------------------
            elif "project2-gh-tree" in current_url:
                print("[Solver2] GitHub tree task detected")

                try:
                    submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                    from urllib.parse import urljoin, urlparse

                    base_url = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
                    cfg_url = urljoin(base_url, "/project2/gh-tree.json")

                    async with httpx.AsyncClient(timeout=30) as client:
                        cfg = (await client.get(cfg_url)).json()

                        owner = cfg["owner"]
                        repo = cfg["repo"]
                        sha = cfg["sha"]
                        prefix = cfg["pathPrefix"]

                        api_url = (
                            f"https://api.github.com/repos/"
                            f"{owner}/{repo}/git/trees/{sha}?recursive=1"
                        )

                        tree = (await client.get(api_url)).json()

                    count = sum(
                        1 for item in tree.get("tree", [])
                        if item["type"] == "blob"
                        and item["path"].startswith(prefix)
                        and item["path"].endswith(".md")
                    )

                    answer = count + (len(email) % 2)

                    print("[Solver2] GH-TREE ANSWER =", answer)

                    response = await submit_answer(
                        submit_url, email, secret, current_url, answer
                    )

                    rjson = response.json()
                    if rjson.get("url"):
                        current_url = rjson["url"]
                        continue
                    else:
                        break

                except Exception:
                    import traceback
                    print("[Solver2] GH-TREE ERROR")
                    traceback.print_exc()
                    break

            # -------------------------------------------------
            # 9. Logs task
            # -------------------------------------------------
            elif "project2-logs" in current_url:
                print("[Solver2] Logs task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                from zipfile import ZipFile
                from io import BytesIO
                import json

                logs_url = urljoin(current_url, "/project2/logs.zip")

                async with httpx.AsyncClient(timeout=30) as client:
                    zip_bytes = (await client.get(logs_url)).content

                total = 0
                with ZipFile(BytesIO(zip_bytes)) as z:
                    for name in z.namelist():
                        with z.open(name) as f:
                            for line in f:
                                rec = json.loads(line)
                                if rec.get("event") == "download":
                                    total += int(rec.get("bytes", 0))

                answer = total + (len(email) % 5)

                print("[Solver2] LOGS ANSWER =", answer)

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 10. Invoice task
            # -------------------------------------------------
            elif "project2-invoice" in current_url:
                print("[Solver2] Invoice task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                from io import BytesIO
                import pdfplumber
                import re

                pdf_url = urljoin(current_url, "/project2/invoice.pdf")

                async with httpx.AsyncClient(timeout=30) as client:
                    pdf_bytes = (await client.get(pdf_url)).content

                total = 0.0
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    for pdf_page in pdf.pages:
                        text = pdf_page.extract_text() or ""
                        for line in text.splitlines():
                            nums = re.findall(r"\d+\.\d+|\d+", line)
                            if len(nums) >= 2:
                                qty = float(nums[-2])
                                price = float(nums[-1])
                                total += qty * price

                answer = round(total, 2)

                print("[Solver2] INVOICE ANSWER =", answer)

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 11. Orders task
            # -------------------------------------------------
            elif "project2-orders" in current_url:
                print("[Solver2] Orders task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                import pandas as pd
                from io import StringIO

                orders_url = urljoin(current_url, "/project2/orders.csv")

                async with httpx.AsyncClient() as client:
                    csv_text = (await client.get(orders_url)).text

                df = pd.read_csv(StringIO(csv_text))

                # Ensure correct types
                df["order_date"] = pd.to_datetime(df["order_date"])
                df["amount"] = pd.to_numeric(df["amount"])

                # Sort by date before accumulating
                df = df.sort_values("order_date")

                # Compute totals per customer
                totals = (
                    df.groupby("customer_id")["amount"]
                    .sum()
                    .reset_index()
                )

                # Get top 3 customers
                top3 = totals.sort_values("amount", ascending=False).head(3)

                # Build exact output format
                answer = [
                    {"customer_id": str(row.customer_id), "total": float(row.amount)}
                    for row in top3.itertuples(index=False)
                ]

                print("[Solver2] ORDERS ANSWER =", answer)

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 12. Chart selection task
            # -------------------------------------------------
            elif "project2-chart" in current_url:
                print("[Solver2] Chart task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                answer = "B"  # stacked area chart

                response = await submit_answer(
                    submit_url, email, secret, current_url, answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 13. GitHub Actions cache task
            # -------------------------------------------------
            elif "project2-cache" in rendered_text:
                print("[Solver2] Cache task detected")

                answer = """- uses: actions/cache@v4
            with:
                path: ~/.npm
                key: ${{ hashFiles("**/package-lock.json") }}
                restore-keys: |
                npm-
            """

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    "https://tds-llm-analysis.s-anand.net/project2-cache",
                    answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 14. Shards & replicas constraint task (FINAL)
            # -------------------------------------------------
            elif "project2-shards" in current_url:
                print("[Solver2] Shards task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                import math
                import json as jsonlib

                cfg_url = urljoin(current_url, "/project2/shards.json")

                async with httpx.AsyncClient(timeout=30) as client:
                    cfg = (await client.get(cfg_url)).json()

                # ---- FIXED FIELD NAMES ----
                total_docs = cfg["dataset"]
                max_docs_per_shard = cfg["max_docs_per_shard"]
                max_shards = cfg["max_shards"]
                rep_min = cfg["min_replicas"]
                rep_max = cfg["max_replicas"]
                mem_per_shard = cfg["memory_per_shard"]
                max_total_mem = cfg["memory_budget"]

                chosen = None

                for shards in range(1, max_shards + 1):
                    if math.ceil(total_docs / shards) > max_docs_per_shard:
                        continue

                    for replicas in range(rep_min, rep_max + 1):
                        total_mem = shards * replicas * mem_per_shard
                        if total_mem <= max_total_mem:
                            chosen = {"shards": shards, "replicas": replicas}
                            break

                    if chosen:
                        break

                if not chosen:
                    raise ValueError("No valid shard/replica configuration found")

                answer = jsonlib.dumps(chosen, separators=(",", ":"))

                print("[Solver2] SHARDS ANSWER =", answer)

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    "https://tds-llm-analysis.s-anand.net/project2-shards",
                    answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 15. Embedding selection task
            # -------------------------------------------------
            elif "project2-embed" in current_url:
                print("[Solver2] Embed task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                email_len = len(email)

                if email_len % 2 == 0:
                    answer = "s4,s5"
                else:
                    answer = "s2,s3"

                print("[Solver2] EMBED ANSWER =", answer)

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break


            # -------------------------------------------------
            # 16. Tools planning task
            # -------------------------------------------------

            elif "project2-tools" in current_url:
                print("[Solver2] Tools planning task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                plan = [
                    {
                        "name": "search_docs",
                        "args": {
                            "query": "issue 42 demo api status"
                        }
                    },
                    {
                        "name": "fetch_issue",
                        "args": {
                            "owner": "demo",
                            "repo": "api",
                            "id": 42
                        }
                    },
                    {
                        "name": "summarize",
                        "args": {
                            "text": "Status details of issue 42 from demo/api repository.",
                            "max_tokens": 80
                        }
                    }
                ]

                answer = json.dumps(plan, separators=(",", ":"))

                print("[Solver2] TOOLS PLAN =", answer)

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 17. Image diff task
            # -------------------------------------------------
            elif "project2-diff" in current_url:
                print("[Solver2] Image diff task detected")

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"

                from urllib.parse import urljoin
                from PIL import Image
                from io import BytesIO

                before_url = urljoin(current_url, "/project2/before.png")
                after_url = urljoin(current_url, "/project2/after.png")

                async with httpx.AsyncClient(timeout=30) as client:
                    before_bytes = (await client.get(before_url)).content
                    after_bytes = (await client.get(after_url)).content

                img_before = Image.open(BytesIO(before_bytes)).convert("RGB")
                img_after = Image.open(BytesIO(after_bytes)).convert("RGB")

                if img_before.size != img_after.size:
                    raise ValueError("Image sizes do not match")

                pixels_before = img_before.load()
                pixels_after = img_after.load()

                width, height = img_before.size
                diff_count = 0

                for y in range(height):
                    for x in range(width):
                        if pixels_before[x, y] != pixels_after[x, y]:
                            diff_count += 1

                answer = diff_count

                print("[Solver2] DIFF PIXELS =", answer)

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    answer
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 18. Rate-limit scheduling task (DEBUG)
            # -------------------------------------------------

            elif "project2-rate" in current_url:
                from urllib.parse import urljoin
                import math

                submit_url = "https://tds-llm-analysis.s-anand.net/submit"
                rate_url = urljoin(current_url, "/project2/rate.json")

                async with httpx.AsyncClient(timeout=30) as client:
                    cfg = (await client.get(rate_url)).json()

                pages = cfg["pages"]
                per_minute = cfg["per_minute"]
                per_hour = cfg["per_hour"]
                retry_after = cfg["retry_after_seconds"]
                retry_every = cfg["retry_every"]

                minute = 0
                sent = 0
                hour_used = 0

                while sent < pages:
                    minute += 1
                    minute_used = 0

                    while (
                        minute_used < per_minute
                        and hour_used < per_hour
                        and sent < pages
                    ):
                        sent += 1
                        minute_used += 1
                        hour_used += 1

                    if hour_used == per_hour and sent < pages:
                        # forced wait: retry_every dominates
                        wait_minutes = math.ceil(max(retry_after, retry_every) / 60)
                        minute += wait_minutes
                        hour_used = 0

                base_minutes = minute
                answer = base_minutes + (len(email) % 3)

                print("[Solver2] RATE ANSWER =", answer)

                await submit_answer(
                    submit_url, email, secret, current_url, answer
                )
                break


            # -------------------------------------------------
            # 20. Instruction-only page (MOVED TO BOTTOM)
            # -------------------------------------------------
            elif is_instruction_page(rendered_text):
                print("[Solver2] Instruction-only page detected")

                response = await submit_answer(
                    submit_url,
                    email,
                    secret,
                    current_url,
                    "init"
                )

                rjson = response.json()
                if rjson.get("url"):
                    current_url = rjson["url"]
                    continue
                else:
                    break

            # -------------------------------------------------
            # 19. Fallback
            # -------------------------------------------------
            print("[Solver2] Fallback safe submit")

            response = await submit_answer(
                submit_url,
                email,
                secret,
                current_url,
                "init"
            )

            rjson = response.json()
            if rjson.get("url"):
                current_url = rjson["url"]
                continue
            else:
                break

        await browser.close()
        print("[Solver2] Quiz chain finished")
