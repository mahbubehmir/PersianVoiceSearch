import streamlit as st
import speech_recognition as sr
import re
import time
import tempfile
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import unquote
import logging
from colorama import init
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')
init(autoreset=True)

# تنظیمات logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# تنظیمات صفحه Streamlit
st.set_page_config(
    page_title="دستیار صوتی جستجو",
    page_icon="🔍",
    layout="wide"
)

# اضافه کردن CSS سفارشی برای بهبود ظاهر صفحه
custom_css = """
<style>
body {
    background-color: #f5f7fa;
    font-family: 'Helvetica Neue', sans-serif;
}
header, .css-18e3th9 {
    background-color: #ffffff !important;
    border-bottom: 1px solid #eaeaea;
}
.stButton>button {
    background-color: #4CAF50;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 10px 24px;
    cursor: pointer;
}
.stButton>button:hover {
    background-color: #45a049;
}
.result-box {
    background-color: #ffffff;
    border: 1px solid #eaeaea;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 10px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# قرار دادن توضیحات در Sidebar
st.sidebar.title("راهنمای استفاده")
st.sidebar.info(
    """
    این سیستم به شما امکان می‌دهد تا به صورت صوتی دستور جستجو را وارد کنید.
    **مراحل کار به صورت زیر است:**
    1. بر روی دکمه **"شروع جستجو"** کلیک کنید.
    2. فرمان صوتی خود را بیان کنید.
    3. نتایج جستجو در صفحه اصلی نمایش داده می‌شوند.
    
    توجه: از اتصال اینترنت مطمئن باشید.
    """
)

class VoiceAssistant:
    def __init__(self, use_vosk=False):
        self.recognizer = sr.Recognizer()
        self.use_vosk = use_vosk
        self.mic_index = self.select_microphone()
        self.temp_dirs = {
            '1': tempfile.mkdtemp(prefix='chrome_profile_1_'),
            '2': tempfile.mkdtemp(prefix='chrome_profile_2_')
        }
        
        self.recognizer.energy_threshold = 3000
        self.recognizer.pause_threshold = 1.0
        self.recognizer.dynamic_energy_threshold = True
        
        if use_vosk:
            try:
                from vosk import Model, KaldiRecognizer
                self.vosk_model = Model("model-fa")
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
            except Exception as e:
                logging.error("خطا در بارگذاری مدل Vosk: %s", e)
                self.use_vosk = False

    def select_microphone(self):
        mic_list = sr.Microphone.list_microphone_names()
        for idx, name in enumerate(mic_list):
            if 'mic' in name.lower():
                logging.info("میکروفون انتخاب شده: %s", name)
                return idx
        logging.info("میکروفون پیش‌فرض انتخاب شد.")
        return 0

    def create_driver(self, profile_key='1'):
        try:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("detach", True)
            options.add_argument(f"--user-data-dir={self.temp_dirs[profile_key]}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--start-maximized")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-infobars")
            options.add_argument("--lang=fa")
            options.add_argument("--force-device-scale-factor=1")

            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logging.info("مرورگر با موفقیت ایجاد شد.")
            return driver
        except Exception as e:
            logging.error("خطا در ایجاد مرورگر: %s", e)
            return None

    def google_listen(self):
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                st.info("در حال گوش دادن...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio, language='fa-IR')
                logging.info("متن تشخیص داده شده: %s", text)
                return text.lower()
        except Exception as e:
            logging.error("خطا در دریافت فرمان صوتی: %s", e)
            return None

    def process_command(self, text):
        if not text:
            return False
        pattern = r'^\s*(جستجو|پیدا|گردآوری|سرچ|search|موضوع|درباره|چرا|کی|چه|چطور|چجوری)\s*(کن|بکن|نمایش|نماييد)?\s*'
        cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        logging.info("متن پردازش شده: %s", cleaned_text)
        return cleaned_text if cleaned_text else False

    def human_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.12))

    def perform_search(self, query, profile_key='1'):
        try:
            driver = self.create_driver(profile_key)
            if not driver:
                st.error("خطا در ایجاد مرورگر.")
                return None

            driver.get("https://www.google.com/ncr")
            logging.info("صفحه اصلی گوگل باز شد.")
            
            search_box = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            
            search_box.click()
            time.sleep(0.5)
            search_box.clear()
            self.human_type(search_box, query)
            time.sleep(0.3)
            search_box.send_keys(Keys.ENTER)
            logging.info("درخواست جستجو ارسال شد: %s", query)
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search'))
            )
            logging.info("نتایج جستجو بارگذاری شدند.")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = []
            for result in soup.select('div.g, div[data-snf]'):
                link = result.find('a', href=True)
                if link and link['href'].startswith('/url?q='):
                    href = unquote(link['href'].split('/url?q=')[1].split('&')[0])
                    title_elem = result.find(['h3', 'div'], {'role': 'heading'}) or result.find('div', class_='MBeuO')
                    if title_elem and href.startswith('http'):
                        results.append({'title': title_elem.get_text().strip(), 'url': href})
                        if len(results) >= 5:
                            break
            logging.info("تعداد نتایج استخراج شده: %d", len(results))
            return results
        except Exception as e:
            logging.error("خطا در انجام جستجو: %s", e)
            return None

# عنوان اصلی صفحه
st.title("سیستم جستجوی هوشمند با دستیار صوتی 🔍")

assistant = VoiceAssistant(use_vosk=False)

# دکمه شروع جستجو به همراه توضیحات و progress bar
if st.button('شروع جستجو'):
    st.write("🎤 لطفا بگویید...")
    
    # نمایش progress bar در زمان گوش دادن
    with st.spinner("در حال گوش دادن ..."):
        command = assistant.google_listen()
    
    if command:
        st.success(f"فرمان دریافت شد: {command}")
        processed_query = assistant.process_command(command)
        if processed_query:
            st.info(f"🔍 جستجو در حال انجام برای: **{processed_query}**")
            
            # نمایش progress bar برای عملیات جستجو
            with st.spinner("در حال جستجو..."):
                results = assistant.perform_search(processed_query)
                time.sleep(1)  # شبیه‌سازی زمان پردازش
                
            if results:
                st.markdown("### 📚 نتایج جستجو:")
                for idx, result in enumerate(results, 1):
                    st.markdown(f"""
                    <div class="result-box">
                        <h4>{idx}. {result['title']}</h4>
                        <p>🔗 <a href="{result['url']}" target="_blank">{result['url']}</a></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ عملیات جستجو ناموفق بود")
        else:
            st.warning("⚠️ لطفا دستور را واضح بیان کنید")
    else:
        st.error("⚠️ لطفا دوباره امتحان کنید")
