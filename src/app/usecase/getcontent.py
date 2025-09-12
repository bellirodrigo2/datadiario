from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Any, Callable, Mapping, Optional

from rich.console import Console

from ...domain.entity.link import LinksEntry
from ..gateway.httpreq import IHTTPRequest
from ..repo.content_repo import IContentRepo
from ..repo.links_repo import ILinksRepo
from ..usecase.usecase import UseCase

console = Console()


def build_document(
    le: LinksEntry, link: str, content: dict[str, Any]
) -> dict[str, Any]:
    return {
        "header": {
            "entity": le.entity,
            "group": le.group,
            "date": le.date,
            "link": link,
        },
        "body": content,
    }


@dataclass
class ContentCollector(UseCase):

    parsers: Mapping[str, Callable[[str], dict[str, Any]]]
    http_client: IHTTPRequest
    links_repo: ILinksRepo
    content_repo: IContentRepo
    logger: Logger
    n_batch: int = 10

    async def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: Optional[date],
        commit: Optional[bool],
        status_filter: Optional[str] = "pending",
    ) -> dict[date, Any]:

        if end is None:
            end = start

        registry_key = f"{entity_name.upper()}:{group.upper()}"
        parser = self.parsers[registry_key]

        pendings = await self.links_repo.get_pending_range(
            entity_name=entity_name, group=group, start=start, end=end
        )
        return_dict = {}
        for linkentry in pendings:
            async for responses in self.http_client.get_many(
                linkentry.links_str, self.n_batch
            ):
                for resp in responses:
                    print(resp.text)

                loop_ret = {
                    "entity": entity_name,
                    "group": group,
                    "date": linkentry.date,
                    "processed": len(linkentry.links),
                }
                ok_responses = [r for r in responses if r.status_code in (200, 201)]
                loop_ret["http_ok"] = ok_responses
                nok_responses = [
                    r for r in responses if r.status_code not in (200, 201)
                ]
                loop_ret["http_failed"] = [str(r.url) for r in nok_responses]

                self.logger.debug(
                    f"Fetched {len(ok_responses)} OK and {len(nok_responses)} NOK for {linkentry.entity} {linkentry.group} {linkentry.date}"
                )

                docs: list[dict[str, Any]] = []
                complete_links: list[str] = []
                parser_failed: list[str] = []
                for resp in ok_responses:

                    try:
                        doc = parser(resp.text)
                    except Exception as e:
                        self.logger.error(f"Error parsing {str(resp.url)}: {e}")
                        parser_failed.append(str(resp.url))
                        continue

                    content = build_document(linkentry, str(resp.url), doc)
                    docs.append(content)
                    complete_links.append(str(resp.url))

                loop_ret["parser_failed"] = parser_failed
                return_dict[linkentry.date] = loop_ret

                if commit:
                    await self.content_repo.insert_content(
                        entity_name=linkentry.entity,
                        group=linkentry.group,
                        date=linkentry.date,
                        contents=docs,
                    )
                    # VER AQUI COMO RETORNAR OS ERROS DE INSERÇÃO
                    loop_ret["committed"] = len(docs)
                    await self.links_repo.mark_as_done(
                        entity_name=linkentry.entity,
                        group=linkentry.group,
                        date=linkentry.date,
                        links=complete_links,
                    )
                    # OQUE FAZER AQUI SE DER ERRO?

                for resp in nok_responses:
                    self.logger.error(f"Error fetching {str(resp.url)}: {resp.text}")
        return {}
