import time

def access_page_with_retry(page: object, url: str):
    for attempt in range(3):
        try:
            page.goto(url, timeout=60000)
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Attempt {attempt + 1} failed, retrying in 10s...")
            time.sleep(10)

    return page