import os
import time

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
from bs4 import BeautifulSoup
import urllib

def clean_csv_string(s):
    """
    Remove characters that can break CSV format from a string.

    Args:
    s (str): The input string.

    Returns:
    str: The cleaned string.
    """
    # Characters to be removed
    characters_to_remove = [',', '"', '\n', '\r']

    # Remove the characters from the string
    for char in characters_to_remove:
        s = s.replace(char, '')

    return s

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
def append_to_dataframe(df, status, name, abstract, keywords, primary_area, url):
    """
    Append a row to a pandas DataFrame.

    Args:
    df (DataFrame): The DataFrame to which the row is appended.
    status (str): The status of the paper.
    name (str): The name of the paper.
    abstract (str): The abstract of the paper.
    url (str): The URL of the paper.
    """
    df_append = pd.DataFrame({'status': status,
                    'Name': name,
                    'Abstract': abstract,
                    'Keywords': keywords,
                    'Primary Area': primary_area,
                    'URL': url}, index=[1])
    
    df = pd.concat([df,df_append], ignore_index=True)
    
    return df

def parsing_papers(base_url, save_dir, df, target_paper_status):
    """
    Args:
    base_url (str): The base URL of the conference.
    save_dir (str): The directory where the papers are saved.
    df (DataFrame): The DataFrame to which the paper information is appended.
    target_paper_status (str): The paper status to download.
    """

    driver = webdriver.Chrome(service= Service(ChromeDriverManager().install()))

    driver.get(base_url)

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # wait for the select element to become visible
    wait = WebDriverWait(driver, 120)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "tab-content")))
    nav_tab_elems = driver.find_elements(By.CSS_SELECTOR, "li[role='presentation']")
    nav_tab_elems_a = [elem.find_element(By.TAG_NAME,'a') for elem in nav_tab_elems]
       
    for elem in nav_tab_elems_a:
        tab_name = elem.get_attribute('aria-controls')
        if tab_name == target_paper_status:
            elem.click()
            WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.ID, tab_name)))
            
            print("Parsing papers from " + tab_name)
            tab_elems = driver.find_element(By.ID, tab_name)
            pagination_elems = tab_elems.find_element(By.CSS_SELECTOR, "ul[class='pagination']")
            right_arrows = pagination_elems.find_elements(By.CSS_SELECTOR, "li[class='right-arrow']")
            
            page_num=1
            while True:
              
                print("Parsing papers from " + tab_name + " page " + str(page_num))             
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                tab_elems = soup.find(id=tab_name)
                divs = tab_elems.find_all('div',class_='note')
                
                for paper in divs:
                    anchor = paper.find_all('a')[0]
                    name = clean_csv_string(anchor.text)
                    href = anchor.get('href')
                    url = urllib.parse.urljoin(base_url,href)
                    details = paper.find_all('strong', class_='note-content-field disable-tex-rendering')
                    for detail in details:
                        if 'Abstract' in detail.text:
                            try:
                                abstract = detail.find_next_sibling('div').text
                                abstract = clean_csv_string(abstract)
                            except:
                                abstract = 'x'
                                print('Abstract not found')
                        elif 'Keywords' in detail.text:
                            try:
                                keywords = detail.find_next_sibling('span').text
                                keywords = clean_csv_string(keywords)
                            except:
                                keywords = 'x'
                                print('Keywords not found')
                        elif 'Primary Area' in detail.text:
                            try:
                                primary_area = detail.find_next_sibling('span').text
                                primary_area = clean_csv_string(primary_area)
                            except:
                                primary_area = 'x'
                                print('Primary Area not found')
                                
                    if abstract == 'x' or keywords == 'x' or primary_area == 'x':
                        retry = True
                        break
                    else:
                        retry = False
                        df = append_to_dataframe(df, tab_name, name, abstract, keywords, primary_area, url)
                
                if retry:
                    continue
                else:
                    page_num += 1
                    if len(right_arrows) == 0:
                        break
                    else:
                        right_arrows[0].find_element(By.TAG_NAME,'a').click()
                        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.ID, tab_name)))
                        driver.implicitly_wait(10)
                        tab_elems = driver.find_element(By.ID, tab_name)
                        pagination_elems = tab_elems.find_element(By.CSS_SELECTOR, "ul[class='pagination']")
                        right_arrows = pagination_elems.find_elements(By.CSS_SELECTOR, "li[class='right-arrow']")
                        
    driver.close()
    return df

def download_pdf(url, name):
    r = requests.get(url, stream=True)

    with open('%s.pdf' % name, 'wb') as f:
        for chunck in r.iter_content(1024):
            f.write(chunck)
    r.close()




if __name__ == '__main__':
    import pandas as pd
    import gc
    
    
    base_url = 'https://openreview.net/group?id=ICLR.cc/2024/Conference#tab-accept-oral'
    save_dir = '/Users/genie/Downloads/ICLR2024'
    
    columns = ['status', 'Name', 'Abstract', 'Keywords', 'Primary Area', 'URL']

    # Create an empty DataFrame with these columns
    status_list = ['accept-oral', 'accept-spotlight', 'accept-poster']
    # status_list = ['accept-poster']
    
    for status in status_list:
        df = pd.DataFrame(columns=columns)
        df = parsing_papers(base_url, save_dir, df, status)
        df.to_csv(status+'.csv', index=False)
        del df
        gc.collect()