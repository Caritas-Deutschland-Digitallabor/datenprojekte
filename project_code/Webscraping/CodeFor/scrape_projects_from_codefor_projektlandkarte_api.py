import requests

# The target URL
url = 'https://www.civic-coding.de/mapapi/detail'

# Query parameters extracted from the URL
params = {
    'cms_ids': '14,44,84,47,98,55,92,93,73,1'
}

# Browser-like headers
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Referer': 'https://www.civic-coding.de/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

# Cookies extracted from your -b flag
cookies = {
    'PHPSESSID': '9de975ghvriaob9netlgqlv8ks',
    'fe_typo_user': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZGVudGlmaWVyIjoiNTY5MDg5N2E1ZmE1YjJkNDZhZTEyMDk4OWU1NjM2OTAiLCJ0aW1lIjoiMjAyNi0wMy0yNVQxMzo1NToyOCswMTowMCIsInNjb3BlIjp7ImRvbWFpbiI6Ind3dy5jaXZpYy1jb2RpbmcuZGUiLCJob3N0T25seSI6dHJ1ZSwicGF0aCI6Ii8ifX0.5XC01u6UJ77f9gWnBdhMs_GLgX_twFYXC-HnUVSAnAI',
    '__Secure-typo3nonce_B1IYIunIYO3sJ0Q5Lnq7SQ': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJub25jZSI6InpmRkRlYUxVb1B1clpCVkgyVW9Dd1Q5c3pzamtYVVNDRW9sOUZNZG5KZlExX2thNlpHX2c1QSIsInRpbWUiOiIyMDI2LTAzLTI1VDE0OjExOjE4KzAxOjAwIn0.AMixg6AexMfh6FR-h0k5aEonHPKvh3rhT6grdiuJSkc',
    '__Secure-typo3nonce_sxEbXufMBijbgnc1arRqpg': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJub25jZSI6InFsTFpmM2tKYUpnTEFFbmloZXduTTUwX0NjYnNod0NDemRpMFlYNllfTzNjV0FjNUtLX1JqQSIsInRpbWUiOiIyMDI2LTAzLTI1VDE0OjExOjI2KzAxOjAwIn0.6Bx3jeJ_ZoaTV54sOWoktofZrTdMX5S9ElRJZ9MqWmY',
    '__Secure-typo3nonce_YeOH2gGJrNqAePPzklQyCQ': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJub25jZSI6IkR1NnZNMDZfSG9zTFc3NER2LUgwRFlSWjhVbWhVU1lnZUE1WGdDR1FQSF9KTTE4T3RUZkkzUSIsInRpbWUiOiIyMDI2LTAzLTI1VDE0OjExOjI3KzAxOjAwIn0.txWC3c33ee0Tt3KvLssQM4y52VI9s7hF4aMKH_YJqyQ',
    '__Secure-typo3nonce_NyNBgjvaBBKM0pvyKe1Wlg': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJub25jZSI6IlhHR1FJVDRBX2RGdjRMeHItUHB0TmplaVJuczVaaktZOTRHVFFPZWk3YlpGOEhvb2pEdjdzdyIsInRpbWUiOiIyMDI2LTAzLTI1VDE0OjEyOjAzKzAxOjAwIn0.jDJkKxSu0BasM9OBO6PcYMP0IG5t1C35jICYJ6cun3A',
    '__Secure-typo3nonce_CpTWjQYVspGW1QwGjp8ddg': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJub25jZSI6IlhPTHA5eGp0UV9VeldTVC1LQlFHTVh1X1JZUmpIT3RaekFXNk43LUt0TDQxTFhHdFpNc2hWZyIsInRpbWUiOiIyMDI2LTAzLTI1VDE0OjEyOjA0KzAxOjAwIn0.2RvUhNdeWw4dPMaRdhxFLcSGX0ljXKv1_KmXH4rPquE',
}

try:
    response = requests.get(url, params=params, headers=headers, cookies=cookies)
    
    # Check if the request was successful
    response.raise_for_status()
    
    # Print the output (JSON or Text)
    print(response.json()) 
    
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")