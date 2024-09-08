import os
import random
import time
import re
import json
from datetime import datetime
from typing import List, Type

import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, create_model
import html2text

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from assets import USER_AGENTS, HEADLESS_OPTIONS, SYSTEM_MESSAGE, USER_MESSAGE
import google.generativeai as genai

load_dotenv()

# Set up the Chrome WebDriver options
def setup_selenium():
    options = Options()
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={user_agent}")

    for option in HEADLESS_OPTIONS:
        options.add_argument(option)

    service = Service(r"./chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html_selenium(url):
    driver = setup_selenium()
    try:
        driver.get(url)
        time.sleep(1)
        driver.maximize_window()

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        html = driver.page_source
        return html
    finally:
        driver.quit()

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup.find_all(['header', 'footer']):
        element.decompose()

    return str(soup)

def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)
    return markdown_content

def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **field_definitions)

def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))

def format_data(data, DynamicListingsContainer, DynamicListingModel):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={
        "response_mime_type": "application/json",
        "response_schema": DynamicListingsContainer
    })

    prompt = SYSTEM_MESSAGE + "\n" + USER_MESSAGE + data
    completion = model.generate_content(prompt)
    return completion.text

def save_formatted_data(formatted_data, timestamp, output_folder='output'):
    os.makedirs(output_folder, exist_ok=True)
    formatted_data_dict = json.loads(formatted_data)
    json_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.json')
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data_dict, f, indent=4)
    print(f"Formatted data saved to JSON at {json_output_path}")

    df = pd.DataFrame(next(iter(formatted_data_dict.values())) if len(formatted_data_dict) == 1 else formatted_data_dict)
    excel_output_path = os.path.join(output_folder, f'sorted_data_{timestamp}.xlsx')
    df.to_excel(excel_output_path, index=False)
    print(f"Formatted data saved to Excel at {excel_output_path}")
    return df
