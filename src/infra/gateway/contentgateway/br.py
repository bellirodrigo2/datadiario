from typing import Any

from ...web.htmlparser import SoupParsed


def parse_br_content(content: str) -> dict[str, Any]:

    parsed_html = SoupParsed(content)

    materia = parsed_html.find_byid("materia")  # type: ignore

    data = materia.find_byclass("publicado-dou-data")
    pagina = materia.find_byclass("secao-dou-data")
    edicao = materia.find_byclass("edicao-dou-data")
    fonte = materia.find_byclass("orgao-dou-data")

    title = materia.find_byclass("identifica")
    from_ = materia.find_byclass("titulo")
    paragraphs = materia.findall_byclass("dou-paragraph")
    edicao_num = int(edicao.text) if edicao and isinstance(edicao.text, str) else -1  # type: ignore
    pagina_num = int(pagina.text) if pagina and isinstance(pagina.text, str) else -1  # type: ignore

    return {
        # 'Url': url,
        "Data": datetime.strptime(data.text, "%d/%m/%Y") if data else None,  # type: ignore
        "Pagina": pagina_num,
        "Edicao": edicao_num,
        "Orgao": fonte.text if fonte else None,
        "Fonte": from_.text if from_ else None,
        "Titulo": title.text if title else None,
        "Texto": "\n".join([p.text for p in paragraphs]),
    }
