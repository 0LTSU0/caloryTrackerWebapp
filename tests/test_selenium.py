import pytest
import os
import shutil
import subprocess
import sys
import time
import threading
import random
import string
import json
import platform

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

TEST_USERNAME = "testuser_1"
TEST_PASSWORD = "=3fF?5]'Fj13'ed]yHY&FK{CBM65I3gn" # need to use some "strong" password to prevent google pwd check from fucking everything up

class TestClass:
    @classmethod
    def setup_class(cls):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        cls.workdir = os.path.join(dir_path, "tmp")
        cls.ct_data_path = os.path.join(cls.workdir, "data")
        cls.ct_config_path = os.path.join(cls.workdir, "config")


        if os.path.exists(cls.workdir):
            shutil.rmtree(cls.workdir)
        os.mkdir(cls.workdir)
        os.mkdir(cls.ct_data_path)
        os.mkdir(cls.ct_config_path)
        if os.path.exists(os.path.join(dir_path, "..", "pfoauth.json")):
            shutil.copy(os.path.join(dir_path, "..", "pfoauth.json"), cls.ct_config_path)
        else:
            j = {"client_id": "123456789", "client_secret": "qwertyuiopå"}
            with open(os.path.join(cls.ct_config_path, "pfoauth.json"), "w") as f:
                json.dump(j, f)

        os.environ["ct_config_path"] = cls.ct_config_path
        os.environ["ct_data_path"] = cls.ct_data_path
        from server import app

        def run_app():
            app.run(host="0.0.0.0",
                    port=5001,
                    debug=False)
            
        cls.server_thread = threading.Thread(target=run_app)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # ---- Start Selenium ----
        chrome_options = Options()
        if "Linux" in platform.platform():
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = f"http://127.0.0.1:5001"
        cls.driver.get(cls.base_url)


    @classmethod
    def teardown_class(cls):
        #shutil.rmtree(cls.workdir) cannot be done as the app is still running at this point
        cls.driver.quit()
        print("Class teardown done")


    def get_element_css(self, css_selector):
        return WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    

    def check_elem_exists_css(self, css_selector):
        try:
            self.get_element_css(css_selector)
            return True
        except Exception as e:
            return False


    def is_user_logged_in(self):
        return self.check_elem_exists_css("#navbarText")
    
    def is_user_logged_out(self):
        return self.check_elem_exists_css("#username")


    def test_1_create_user(self):
        self.get_element_css("body > div > form > button.btn.btn-secondary").click()
        self.get_element_css("#username").click()
        self.get_element_css("#username").send_keys(TEST_USERNAME)
        self.get_element_css("#password").click()
        self.get_element_css("#password").send_keys(TEST_PASSWORD)
        self.get_element_css("#repassword").click()
        self.get_element_css("#repassword").send_keys(TEST_PASSWORD)
        self.get_element_css("#registerButt").click()
        assert self.is_user_logged_in()


    def test_2_login_invalid_credentials(self):
        if self.is_user_logged_in():
            self.get_element_css("#navbarText > ul.navbar-nav.ms-auto > li > a").click()
        assert self.is_user_logged_out()
        self.get_element_css("#username").click()
        self.get_element_css("#username").send_keys(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
        self.get_element_css("#password").click()
        self.get_element_css("#password").send_keys(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20)))
        self.get_element_css("body > div > form > button.btn.btn-primary").click()
        assert not self.is_user_logged_in() # check for login to make sure request is processed
        assert "Login failed. Account doesn't exist or username/password is incorrect" in self.driver.page_source
        self.get_element_css("#username").click()
        self.get_element_css("#username").send_keys(TEST_USERNAME)
        self.get_element_css("#password").click()
        self.get_element_css("#password").send_keys(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20)))
        self.get_element_css("body > div > form > button.btn.btn-primary").click()
        assert not self.is_user_logged_in() # check for login to make sure request is processed
        assert "Login failed. Account doesn't exist or username/password is incorrect" in self.driver.page_source
        self.get_element_css("#username").click()
        self.get_element_css("#username").send_keys(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
        self.get_element_css("#password").click()
        self.get_element_css("#password").send_keys(TEST_PASSWORD)
        self.get_element_css("body > div > form > button.btn.btn-primary").click()
        assert not self.is_user_logged_in() # check for login to make sure request is processed
        assert "Login failed. Account doesn't exist or username/password is incorrect" in self.driver.page_source


    def test_3_login_valid_credentials(self):
        if self.is_user_logged_in():
            self.get_element_css("#navbarText > ul.navbar-nav.ms-auto > li > a").click()
        assert self.is_user_logged_out()
        self.get_element_css("#username").click()
        self.get_element_css("#username").send_keys(TEST_USERNAME)
        self.get_element_css("#password").click()
        self.get_element_css("#password").send_keys(TEST_PASSWORD)
        self.get_element_css("body > div > form > button.btn.btn-primary").click()
        assert self.is_user_logged_in()

    #navbarText > ul.navbar-nav.ms-auto > li > a