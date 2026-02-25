import os
import csv
import time
from dotenv import load_dotenv
import logging
import datetime
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException



#-------------------------------------------------------------------------------------# crea el archivo log 
def create_logfile():
    date_time = datetime.datetime.today().strftime('%d-%b-%y_%H-%M-%S')  # Modificado el formato de la fecha y hora
    log_directory = 'log'
    os.makedirs(log_directory, exist_ok=True)
    logfile = os.path.join(log_directory, f'{date_time}.log')
    logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', force=True)
    logging.info(f'Log file {logfile} created')
    return logging



#-------------------------------------------------------------------------------------#
#aca creo el archivo csv donde se van a guardar los datos que voy a extraer de linkedin

def create_file(file, logging):
    # borrar el archivo si existe
    logging.info("Revisando si existe un archivo csv...")
    if os.path.exists(file):
        os.remove(file)
        logging.info(f"{file} borrado")
    else:
        logging.info(f"{file} no existe")
    
    # creo el archivo y agrego los headers
    logging.info("creando CSV diario...")
    output_dir = os.path.dirname(file)
    os.makedirs(output_dir, exist_ok=True)  # Crear directorio 'output' si no existe

    header = ['date_time', 'search_keyword', 'search_count', 'job_id', 'job_title', 
              'company', 'location', 'remote', 'update_time', 'applicants', 'job_pay',
                'job_time', 'job_position', 'company_size', 'company_industry', 'job_details']
    

    with open(file, 'w') as f:
        w = csv.writer(f)
        w.writerow(header)
        logging.info(f"{file} Creado")


#-------------------------------------------------------------------------------------#
#aca creo la funcion para loguearme en linkedin y poder hacer la busqueda de los datos que necesito extraer de linkedin y poder guardarlos en el archivo csv

def login(logging):
    url_login = os.environ.get.LINKEDIN_LOGIN_URL

   # credenciales de logueo
    LINKEDIN_USERNAME = os.environ.get.LINKEDIN_USERNAME
    LINKEDIN_PASSWORD = os.environ.get.LINKEDIN_PASSWORD

    # setup chrome to run headless
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Hacer que Chrome se ejecute en segundo plano
    chrome_options.add_argument("--window-size=1920,1080") # Tamaño de la ventana de Chrome

    # escribo en el log
    logging.info(f"LOGUEANDOME A LINKEDIN COMO {LINKEDIN_USERNAME}...")

    # seteo el driver de chrome
    driver_path = os.environ.get.DRIVER_PATH
    service = Service(driver_path)
    wd = webdriver.Chrome(service=service)

    # logueo en linkedin con las credenciales y le doy submit
    wd.get(url_login)
    wd.find_element(By.NAME, "session_key").send_keys(LINKEDIN_USERNAME)
    wd.find_element(By.NAME, "session_password").send_keys(LINKEDIN_PASSWORD)
    wd.find_element(By.XPATH, "//button[@type='submit']").click()

    # espero a que cargue la pagina y le doy click al boton de "skip" si es que aparece
    try: 
        wd.find_element(By.XPATH,"//button[@class='primary-action-new']").click()
    except:
        pass
    logging.info("Login completado. Scrapeando la data...")
    print ("Login completado. Scrapeando la data...")

    return wd


#-------------------------------------------------------------------------------------#
#aca creo la funcion para buscar los datos que necesito extraer 


def page_search(wd, search_location, search_keyword, search_remote, search_posted, search_page, search_count, file, logging):
    # wait time for events in seconds
    page_wait = 30
    click_wait = 5
    async_wait = 5

    # when retrying, number of attempts
    attempts = 3

    # navigate to search page

   #GEOID 92000000 ES EL CODIGO DE wolrdwide
   # f_TPR=r86400 ES EL CODIGO DE 24 HORAS
   # f_WRA=true ES EL CODIGO DE REMOTE
   # keywords=Data%20Analyst ES EL CODIGO DE LA BUSQUEDA
   # location=Worldwide ES EL CODIGO DE LA UBICACION
   # start=25 ES EL CODIGO DE LA PAGINA
   #  
    
    url_search = f"https://www.linkedin.com/jobs/search/?f_TPR={search_posted}&f_WRA={search_remote}&geoId=92000000&keywords={search_keyword}&location={search_location}&start={search_page}"
    

    
    wd.get(url_search)
    time.sleep(page_wait) # agregar un tiempo de espera para que cargue la pagina

    # find the number of results 
    search_count = wd.find_element(By.XPATH,"//small[contains(@class, 'jobs-search-results-list__text') and contains(@class, 't-normal') and contains(@class, 't-12') and contains(@class, 't-black--light')]").text
    search_count = int(search_count.split(' ')[0].replace(',', ''))  # get number before space & remove comma (ex. "1,245 results")
    logging.info(f"Loading page {round(search_page/25) + 1} of {round(search_count/25)} for {search_keyword}'s {search_count} results...")

    # get all the job_id's for xpath for current page to click each element
    # running into errors with slow load (11-Aug)
    for attempt in range(attempts):
        try:
            search_results = wd.find_element(By.XPATH,"//ul[@class='jobs-search-results__list list-style-none']").find_element(By.TAG_NAME,("li"))
            
            result_ids = [result.get_attribute('id') for result in search_results if result.get_attribute('id') != '']
            print (result_ids)
            break
        except:
            time.sleep(click_wait) # wait a few attempts, if not throw an exception and then skip to next page

    # cycle through each job_ids and steal the job data...muhahaha!
    list_jobs = [] #initate a blank list to append each page to
    for id in result_ids:
        try:
            job = wd.find_element(By.ID,(id)) 
            job_id = job.get_attribute("data-occludable-entity-urn").split(":")[-1]
            # select a job and start extracting information
            wd.find_element(By.XPATH,f"//div[@data-job-id={job_id}]").click()
        except:
            continue
            # exception likely to job deleteing need to go to next id

        for attempt in range(attempts):
            try:
                # from analysis 3 attempts at 5 second waits gets job titles 99.99% of time (11-Aug)
                job_title = wd.find_element(By.XPATH,"//h2[@class='t-24 t-bold']") # keep having issues with finding element
                job_title = job_title.text
                break
            except:
                job_title = ''
                time.sleep(click_wait)
        
        # Having issues finding xpath of company (Added 11-Aug)
        for attempt in range(attempts):
            try:
                job_top_card1 = wd.find_element(By.XPATH,"//span[@class='jobs-unified-top-card__subtitle-primary-grouping mr2 t-black']").find_elements_by_tag_name("span")
                company = job_top_card1[0].text
                location = job_top_card1[1].text
                if len(job_top_card1) > 2: # only displays remote if selected, otherwise only 2 elements in list
                    remote = job_top_card1[2].text
                else:
                    remote = ''
                break
            except:
                company = ''
                location = ''
                remote = ''
                time.sleep(click_wait)
        
        for attempt in range(attempts):
            try:
                #multiple issues with job_top_card2 loading
                job_top_card2 = wd.find_element(By.XPATH,"//span[@class='jobs-unified-top-card__subtitle-secondary-grouping t-black--light']").find_elements_by_tag_name("span")
                update_time = job_top_card2[0].text
                applicants = job_top_card2[1].text.split(' ')[0]
                break
            except: 
                update_time = '' # after #attempts leave as blank and move on
                applicants = '' # after #attempts leave as blank and move on
                time.sleep(click_wait)

        # Due to (slow) ASYNCHRONOUS updates, need wait times to get job_info
        job_time = '' # assigning as blanks as not important info and can skip if not obtained below
        job_position = ''
        job_pay = ''
        for attempt in range(attempts):
            try:
                # 1 - make sure HTML element is loaded
                element = WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@class='mt5 mb2']/div[1]")))
                # 2 - make sure text is loaded
                try:
                    job_info = element.text
                    if job_info != '':
                        # seperate job information on time requirements and position
                        job_info = job_info.split(" · ")
                        if len(job_info) == 1: # only one item means its job _time
                            job_pay = ''
                            job_time = job_info[0]
                            job_position = ''
                        elif (len(job_info) >= 2) and ("$" in job_info[0]): # if has money symbol then seperate
                            job_pay = job_info[0]
                            job_time = job_info[1]
                            if(len(job_info)>= 3): # check if job_info is required
                                job_position = job_info[2]
                            else:
                                job_position = ''
                        else: # else condition satisifies the last condition
                            job_time = job_info[0]
                            job_position = job_info[1]
                            job_pay = ''
                        break
                    else:
                        time.sleep(async_wait)
                except:
                    # error means page didn't load so try again
                    time.sleep(async_wait)
            except:
                # error means page didn't load so try again
                time.sleep(async_wait)

        # get company details and seperate on size and industry
        company_size = '' # assigning as blanks as not important info and can skip if not obtained below
        company_industry = ''
        job_details = ''      
        for attempt in range(attempts):
            try:
                company_details = wd.find_element(By.XPATH,"//div[@class='mt5 mb2']/div[2]").text
                if " · " in company_details:
                    company_size = company_details.split(" · ")[0]
                    company_industry = company_details.split(" · ")[1]
                else:
                    company_size = company_details
                    company_industry = ''
                job_details = wd.find_element(By.NAME,("job-details")).text.replace("\n", " ")
                break
            except: 
                time.sleep(click_wait)

        # append (a) line to file
        date_time = datetime.datetime.now().strftime("%d%b%Y-%H:%M:%S")
        search_keyword = search_keyword.replace("%20", " ")
        list_job = [date_time, search_keyword, search_count, job_id, job_title, company,
                     location, remote, update_time, applicants, job_pay, job_time, job_position,
                       company_size, company_industry, job_details]
        
        list_jobs.append(list_job)

    with open(file, "a") as f:
        w = csv.writer(f)
        w.writerows(list_jobs)
        list_jobs = []
    
    logging.info(f"Page {round(search_page/25) + 1} of {round(search_count/25)} loaded for {search_keyword}")
    search_page += 25

    return search_page, search_count, url_search
# create logging file
logging = create_logfile()

# create daily csv file
date = datetime.date.today().strftime('%d-%b-%y')
file = f"output/{date}.csv"
create_file(file, logging)

# login to linkedin and assign webdriver to variable
wd = login(logging)

# URL search terms focusing on what type of skills are required for Data Analyst & Data Scientist
search_keywords = ['Data Analyst', 'Data Scientist', 'Data Engineer']
    # Titles to remove as search is too long
    # ['Business Analyst', 'Operations Analyst', 'Marketing Analyst', 'Product Analyst',
    # 'Analytics Consultant', 'Business Intelligence Analyst', 'Quantitative Analyst',  'Data Architect',
    # 'Data Engineer', 'Machine Learning Engineer', 'Machine Learning Scientist']
search_location = "Worldwide"
search_remote = "true" # filter for remote positions
search_posted = "r86400" # filter for past 24 hours

# Counting Exceptions
exception_first = 0
exception_second = 0

for search_keyword in search_keywords:
    search_keyword = search_keyword.lower().replace(" ", "%20")

# Loop through each page and write results to csv
    search_page = 0 # start on page 1
    search_count = 1 # initiate search count until looks on page
    while (search_page < search_count) and (search_page != 1000):
        # Search each page and return location after each completion
        try:
            search_page, search_count, url_search = page_search(wd, search_location, search_keyword, search_remote, search_posted, search_page, search_count, file, logging)
        except Exception as e:
            logging.error(f'(1) FIRST exception for {search_keyword} on {search_page} of {search_count}, retrying...')
            logging.error(f'Current URL: {url_search}')
            logging.error(e)
            logging.exception('Traceback ->')
            exception_first += 1
            time.sleep(5) 
            try:
                search_page, search_count, url_search = page_search(wd, search_location, search_keyword, search_remote, search_posted, search_page, search_count, file, logging)
                logging.warning(f'Solved Exception for {search_keyword} on {search_page} of {search_count}')
            except Exception as e:
                logging.error(f'(2) SECOND exception remains for {search_keyword}. Skipping to next page...')
                logging.error(f'Current URL: {url_search}')
                logging.error(e)
                logging.exception('Traceback ->')
                search_page += 25 # skip to next page to avoid entry
                exception_second += 1
                logging.error(f'Skipping to next page for {search_keyword}, on {search_page} of {search_count}...')

# close browser
wd.quit()

logging.info(f'LinkedIn data scraping complete with {exception_first} first and {exception_second} second exceptions')
logging.info(f'Regard all further alarms...')