import asyncio
from datetime import date

from .infra.gateway.contentgateway.ce import parse_ce_content
from .infra.gateway.linksgateway.ce import get_ceara_links
from .infra.web.httpreq import AsyncHttpx


def get_links(date: date):

    links = asyncio.run(get_ceara_links(date))
    return links


def get_content(url: str):

    http = AsyncHttpx()
    resp = asyncio.run(http.get(url))

    content = parse_ce_content(resp.content)

    return content


if __name__ == "__main__":

    # d = date(2025, 9, 11)
    # print(get_links(d))
    url = "http://imagens.seplag.ce.gov.br/pdf/20250911/do20250911p06.pdf"
    content = get_content(url)
    print(content)
