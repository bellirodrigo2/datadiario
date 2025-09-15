from datetime import date

from ....infra.web.htmlparser import SoupParsed
from ....infra.web.httpreq import AsyncHttpx


async def get_ceara_links(date: date) -> list[str]:

    date_str = date.strftime("%Y%m%d")
    url = f"http://pesquisa.doe.seplag.ce.gov.br/doepesquisa/sead.do?page=ultimasDetalhe&cmd=10&action=Cadernos&data={date_str}"

    http = AsyncHttpx()

    resp = await http.get(url)

    if resp.status_code != 200:
        raise Exception(
            f"Failed to get content from {url}, status code: {resp.status_code}"
        )
    soup = SoupParsed(resp.text)

    links = soup.find_all("a", href=True)

    return [str(link["href"]) for link in links if link["href"].endswith(".pdf")]
