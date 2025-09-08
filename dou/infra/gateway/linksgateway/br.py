import json
from datetime import datetime
from typing import Generator

from dou.infra.web.webscrapper import WebScrapper


def get_br_dou1_links(date: datetime) -> list[str]:
    return _get_br_links("dou1", date)


def get_br_dou2_links(date: datetime) -> list[str]:
    return _get_br_links("dou2", date)


def get_br_dou3_links(date: datetime) -> list[str]:
    return _get_br_links("dou3", date)


def _get_br_links(group: str, date: datetime) -> list[str]:
    url = f'https://www.in.gov.br/leiturajornal?secao={group}&data={date.strftime("%d-%m-%Y")}'
    links = _get_links(url)
    return list([link for link in links])


def _get_links(url: str) -> Generator[str, None, None]:
    scrapper = WebScrapper(url, 2)
    try:
        treelabel = "viewMenuOptionTree"
        # listlabel = "viewMenuOptionList"

        btntree = scrapper.get_element_wait("id", treelabel)
        # btnlist = scrapper.get_element("id", listlabel)
        if btntree.is_displayed():
            try:
                btntree.click()
            except Exception:
                pass
        tree_mode = btntree.is_displayed() == False

        cont = True
        while cont:
            div_conteudo = "hierarchy_content"
            conteudo = scrapper.get_element_wait("id", div_conteudo)
            links = conteudo.find_elements("xpath", ".//a[@href]")
            if links is None:
                raise ValueError("No links found on the page")
            for link in links:
                yield link.get_attribute("href")
            cont = False if tree_mode else pagination(scrapper)

    finally:
        scrapper.close()


def pagination(scrapper: WebScrapper):

    cls = "pagination-button"

    def get_active():
        active = scrapper.get_element("css selector", f".{cls}.active")
        return active.text if active else None

    def get_next():
        elements = scrapper.get_elements("class name", cls)
        next_word = "Próximo"
        return next(
            (b for b in elements if next_word in b.text),
            None,
        )

    next_button = get_next()
    active_button = get_active()
    # print(active_button)
    if next_button:
        next_button.click()
        scrapper.wait_until(lambda _: get_active() != active_button)
        return True
    return False


if __name__ == "__main__":

    c = 0
    url = "https://www.in.gov.br/leiturajornal?secao=dou2&data=12-02-2025"
    links_entry = {"entity": "br_federal", "group": "dou2", "links": []}
    links = links_entry["links"]
    for link in _get_links(url):
        links.append(link)
        # print(link)
        # print(c)
        c += 1
    with open("links.txt", "w") as f:
        json.dump(links_entry, f, indent=4)
    print(f"Total links: {c}")
