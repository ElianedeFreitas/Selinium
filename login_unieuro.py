# login_unieuro.py
import os, time, shutil, tempfile
from shutil import which
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===== CONFIG =====
LOGIN = "09416619116"
SENHA = "09416619116"
URL   = "https://ead.unieuro.edu.br/login/index.php"

HEADLESS = True
IMPLICIT_WAIT = 5
EXPLICIT_WAIT = 20
PROFILE_DIR = None

def _pick_browser_binary():
    # Permite forçar via env: CHROME_BINARY
    env = os.getenv("CHROME_BINARY")
    if env and os.path.exists(env):
        return env
    # Tenta Chrome, depois Chromium
    for cand in ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(cand):
            return cand
    # Tenta via PATH
    for name in ["google-chrome", "chromium", "chromium-browser"]:
        p = which(name)
        if p:
            return p
    return None

def create_driver(headless: bool = False):
    global PROFILE_DIR
    PROFILE_DIR = tempfile.mkdtemp(prefix="selenium_profile_")

    opts = webdriver.ChromeOptions()

    # Detecta binário do navegador (Chrome/Chromium); se None, Selenium tenta achar sozinho
    binary = _pick_browser_binary()
    if binary:
        opts.binary_location = binary

    # Perfil exclusivo evita "user data dir is already in use"
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")

    # Flags úteis para container/CI
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--no-first-run")
    opts.add_argument("--start-maximized")

    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")

    # >>> Sem Service, sem webdriver-manager: Selenium Manager resolve o driver <<<
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver

def try_login(driver):
    driver.get(URL)
    wait = WebDriverWait(driver, EXPLICIT_WAIT)
    try:
        # usuário
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

        # senha
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

        # preencher
        campo_login.clear(); campo_login.send_keys(LOGIN)
        campo_senha.clear(); campo_senha.send_keys(SENHA)

        # botão
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

        # pós-login
        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//a[contains(., 'Sair') or contains(., 'Logout')] | //nav[@role='navigation']")
            ))
            print("Login realizado (navegação pós-login encontrada).")
            return True
        except TimeoutException:
            print("Não confirmei automaticamente. URL atual:", driver.current_url)
            return False

    except Exception as e:
        print("Erro durante tentativa de login:", e)
        return False

def main():
    driver = None
    try:
        driver = create_driver(HEADLESS)
        ok = try_login(driver)
        if ok: time.sleep(2)
        else:  print("Login não confirmado — verifique CAPTCHA/proxy/mudança de layout.")
        if not HEADLESS:
            print("Deixando o navegador aberto por 8s..."); time.sleep(8)
    finally:
        if driver: driver.quit()
        global PROFILE_DIR
        if PROFILE_DIR and os.path.isdir(PROFILE_DIR):
            shutil.rmtree(PROFILE_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
