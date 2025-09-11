from collections.abc import Callable
from typing import Any, Literal, Protocol, runtime_checkable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@runtime_checkable
class ScrapperElement(Protocol):
    def click(self) -> None: ...
    def send_keys(self, value: str) -> None: ...
    def clear(self) -> None: ...
    def submit(self) -> None: ...
    def get_attribute(self, name: str) -> str: ...
    def text(self) -> str: ...
    def tag_name(self) -> str: ...
    def location(self) -> tuple[int, int]: ...
    def size(self) -> tuple[int, int]: ...
    def rect(self) -> dict[Any, Any]: ...
    def is_displayed(self) -> bool: ...
    def is_enabled(self) -> bool: ...
    def is_selected(self) -> bool: ...
    def screenshot(self, filename: str) -> None: ...
    def find_element(self, by: str, value: str): ...
    def find_elements(self, by: str, value: str): ...


def get_headless_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ativa o modo headless
    chrome_options.add_argument(
        "--disable-gpu"
    )  # Desabilita a GPU (necessário em alguns sistemas)
    chrome_options.add_argument("--no-sandbox")  # Necessário em alguns sistemas

    # Suppress Chrome logs
    chrome_options.add_argument(
        "--log-level=3"
    )  # Suppress INFO, WARNING, and ERROR logs
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # Suppress Selenium logs
    import logging

    # logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(
        logging.ERROR
    )
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

    # driver = webdriver.Chrome(chrome_options)
    service = Service(log_path="NUL")  # No Windows (ou '/dev/null' no Linux/Mac)

    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


byclause = Literal[
    "id",
    "class name",
    "xpath",
    "name",
    "css selector",
    "tag name",
    "link text",
    "partial link text",
]
waitclause = Literal["onDOM", "visible", "selected", "clickable", "all elements"]


class WebScrapper:
    wait_map = {
        "onDOM": EC.presence_of_element_located,
        "visible": EC.visibility_of_element_located,
        "selected": EC.element_to_be_selected,
        "clickable": EC.element_to_be_clickable,
        "all elements": EC.visibility_of_all_elements_located,
    }

    def __init__(self, url: str | None, timeout: int):
        self.driver = get_headless_driver()
        self.timeout = timeout
        if url:
            self.get_url(url)

    def close(self):
        self.driver.quit()

    def get_url(self, url: str):
        self.driver.get(url)

    def get_element_wait(
        self,
        by: byclause,
        label: str,
        timeout: int = -1,
        wait_condition: waitclause = "visible",
    ) -> ScrapperElement:
        func = self.wait_map[wait_condition]
        timeout = self.timeout if timeout == -1 else timeout
        return WebDriverWait(self.driver, timeout).until(func((by, label)))  # type: ignore

    def get_element(
        self, by: byclause, label: str, timeout: int = -1
    ) -> ScrapperElement:
        timeout = self.timeout if timeout == -1 else timeout
        return self.driver.find_element(by, label)

    def get_elements(
        self, by: byclause, label: str, timeout: int = -1
    ) -> list[ScrapperElement]:
        timeout = self.timeout if timeout == -1 else timeout
        return self.driver.find_elements(by, label)

    def wait(self, timeout: int = -1):
        timeout = self.timeout if timeout == -1 else timeout
        self.driver.implicitly_wait(timeout)

    def wait_until(self, predicate: Callable[[Any], bool], timeout: int = -1):
        timeout = self.timeout if timeout == -1 else timeout
        WebDriverWait(self.driver, timeout).until(predicate)


if __name__ == "__main__":
    ...
