# login_unieuro.py
import os, time, shutil, tempfile, re, glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===== CONFIG =====
LOGIN = "09416619116"
SENHA = "09416619116"
URL   = "https://ead.unieuro.edu.br/login/index.php"

HEADLESS = False  # MOSTRAR INTERFACE
IMPLICIT_WAIT = 5
EXPLICIT_WAIT = 20
PROFILE_DIR = None

# Caminho do seu ChromeDriver local (com .exe)
CHROMEDRIVER_PATH = r"C:\Users\aluno\Desktop\Selinium-main\Selinium-main\chromedriver\chromedriver.exe"

# Curso e arquivo a localizar
CURSO_NOME = "24 | GPSINN | PROJETO INTEGRADOR DE SISTEMAS COMPUTACIONAIS"
ARQUIVO_NOME = "globo.pdf"

# Pasta de download
DOWNLOAD_DIR = r"C:\Users\aluno\Downloads\unieuro_downloads"
DOWNLOAD_TIMEOUT = 60  # segundos para esperar o download

def create_driver(headless: bool = False):
    global PROFILE_DIR
    PROFILE_DIR = tempfile.mkdtemp(prefix="selenium_profile_")

    if not os.path.exists(CHROMEDRIVER_PATH):
        raise FileNotFoundError(f"ChromeDriver não encontrado em: {CHROMEDRIVER_PATH}")

    # Garante a pasta de download
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    options = webdriver.ChromeOptions()
    # Perfil exclusivo
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    # Preferências de download
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        # IMPORTANTÍSSIMO para PDFs: baixa em vez de abrir no viewer
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

    service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver

def esperar_download_concluir(nome_parcial, timeout=DOWNLOAD_TIMEOUT):
    """
    Espera até que um arquivo contendo 'nome_parcial' exista em DOWNLOAD_DIR
    e não tenha extensão .crdownload (indicando conclusão do download).
    """
    inicio = time.time()
    alvo_regex = re.compile(re.escape(nome_parcial), re.IGNORECASE)
    while time.time() - inicio < timeout:
        # Lista todos os arquivos da pasta
        arquivos = os.listdir(DOWNLOAD_DIR)
        # Procura arquivo finalizado que contenha nome_parcial
        for arq in arquivos:
            if alvo_regex.search(arq) and not arq.endswith(".crdownload"):
                return os.path.join(DOWNLOAD_DIR, arq)
        time.sleep(0.5)
    return None

def clicar_link_por_texto(driver, texto_procurado):
    """
    Clica no primeiro <a> cujo texto visível contenha 'texto_procurado' (case-insensitive).
    Retorna True/False.
    """
    # Tenta XPATH com contains em lower-case
    xpath = f"//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {repr(texto_procurado.lower())})]"
    try:
        el = WebDriverWait(driver, EXPLICIT_WAIT).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        el.click()
        return True
    except TimeoutException:
        return False

def try_login(driver):
    driver.get(URL)
    wait = WebDriverWait(driver, EXPLICIT_WAIT)
    try:
        # Usuário
        try:
            campo_login = wait.until(EC.presence_of_element_located((By.ID, "username")))
        except TimeoutException:
            campo_login = None
            for loc in [(By.NAME, "username"), (By.NAME, "login"), (By.ID, "login")]:
                try:
                    campo_login = driver.find_element(*loc); break
                except NoSuchElementException:
                    pass
        if not campo_login:
            print("Não encontrei o campo de usuário."); return False

        # Senha
        try:
            campo_senha = driver.find_element(By.ID, "password")
        except NoSuchElementException:
            campo_senha = None
            for loc in [(By.NAME, "password"), (By.NAME, "senha"), (By.ID, "pass")]:
                try:
                    campo_senha = driver.find_element(*loc); break
                except NoSuchElementException:
                    pass
        if not campo_senha:
            print("Não encontrei o campo de senha."); return False

        # Preencher e enviar
        campo_login.clear(); campo_login.send_keys(LOGIN)
        campo_senha.clear(); campo_senha.send_keys(SENHA)

        # Botão de login
        btn = None
        for loc in [
            (By.ID, "loginbtn"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[contains(., 'Entrar') or contains(., 'Acessar') or contains(., 'Login')]"),
            (By.XPATH, "//input[contains(@value, 'Entrar') or contains(@value, 'Login')]"),
        ]:
            try:
                btn = driver.find_element(*loc); break
            except NoSuchElementException:
                pass
        if not btn:
            try:
                btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                )
            except TimeoutException:
                print("Não encontrei o botão de login."); return False

        btn.click()

        # Indício de login OK (menu, link Sair, etc.)
        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//a[contains(., 'Sair') or contains(., 'Logout')] | //nav[@role='navigation']")
            ))
            print("Login realizado.")
            return True
        except TimeoutException:
            print("Não confirmei automaticamente. URL atual:", driver.current_url)
            return False

    except Exception as e:
        print("Erro durante tentativa de login:", e)
        return False

def acessar_curso(driver, nome_curso):
    # Muitos Moodles mostram os cursos na página inicial pós-login (/my/ ou /dashboard).
    # Tenta clicar pelo texto do curso:
    print(f"Procurando curso: {nome_curso}")
    ok = clicar_link_por_texto(driver, nome_curso)
    if ok:
        # Pode haver carregamento/redirect
        time.sleep(1.5)
        print("Curso aberto (provavelmente).")
        return True
    else:
        print("Não consegui localizar o link do curso pelo texto fornecido.")
        return False

def baixar_recurso(driver, nome_arquivo_alvo):
    # Dentro do curso, “Recursos” (mod_resource) geralmente são <a> com o nome do arquivo
    print(f"Procurando arquivo: {nome_arquivo_alvo}")
    alvo_lower = nome_arquivo_alvo.lower()

    # XPath: qualquer link que contenha o texto alvo (case-insensitive)
    xpath_pdf = f"//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {repr(alvo_lower)})]"
    try:
        link = WebDriverWait(driver, EXPLICIT_WAIT).until(
            EC.element_to_be_clickable((By.XPATH, xpath_pdf))
        )
        # Em alguns Moodles, o link abre numa aba nova — força clicar “normal”
        link.click()
        print("Cliquei no link do PDF. Aguardando download...")
    except TimeoutException:
        # Tentativa alternativa: procurar por ícones/itens de recurso com título
        try:
            xpath_alt = "//div[contains(@class,'activity')]//a[contains(@href,'resource') and (contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'globo') or contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'globo'))]"
            link = WebDriverWait(driver, EXPLICIT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, xpath_alt))
            )
            link.click()
            print("Cliquei no link alternativo do PDF (resource). Aguardando download...")
        except TimeoutException:
            print("Não encontrei o link do PDF pelo texto.")
            return None

    # Espera o arquivo ser baixado (verificando se não há .crdownload)
    caminho = esperar_download_concluir(nome_arquivo_alvo, DOWNLOAD_TIMEOUT)
    if caminho:
        print(f"Download concluído em: {caminho}")
    else:
        print("Timeout esperando download. Verifique se abriu em outra aba ou se o site exige clique extra.")
    return caminho

def main():
    driver = None
    try:
        driver = create_driver(HEADLESS)
        if not try_login(driver):
            return
        if not acessar_curso(driver, CURSO_NOME):
            return
        caminho_pdf = baixar_recurso(driver, ARQUIVO_NOME)
        if not caminho_pdf:
            print("Não foi possível confirmar o download do PDF.")
        else:
            # Mantém a janela aberta um pouco, se você quiser ver
            if not HEADLESS:
                print("Deixando o navegador aberto por 8s para inspeção...")
                time.sleep(8)
    finally:
        if driver:
            driver.quit()
        global PROFILE_DIR
        if PROFILE_DIR and os.path.isdir(PROFILE_DIR):
            shutil.rmtree(PROFILE_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
