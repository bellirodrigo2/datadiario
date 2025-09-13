from dataclasses import dataclass
from datetime import date
from logging import Logger
from re import L
from typing import Any, Callable, Mapping, Optional, cast

from rich.console import Console

from ...domain.entity.link import LinksEntry
from ..gateway.httpreq import IHTTPRequest, IResponse
from ..repo.content_repo import IContentRepo
from ..repo.links_repo import ILinksRepo
from .usecase import UseCase

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

        pendings = await self.links_repo.get_pending_range(
            entity_name=entity_name, group=group, start=start, end=end
        )
        return_dict = {}
        for linkentry in pendings:
            loop_ret = await self.collect_single_day(linkentry)
            return_dict[linkentry.date] = loop_ret

            if commit:
                docs: list[dict[str, Any]] = loop_ret["docs"]
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
                    links=loop_ret["complete_links"],
                )
                # OQUE FAZER AQUI SE DER ERRO
        return {}

    def _parse(
        self,
        entity_name: str,
        group: str,
        linkentry: LinksEntry,
        resp: IResponse,
    ) -> dict[str, Any]:

        registry_key = f"{entity_name.upper()}:{group.upper()}"
        parser = self.parsers[registry_key]

        try:
            doc = parser(resp.text)
            content = build_document(linkentry, str(resp.url), doc)
            return content
        except Exception as e:
            self.logger.error(f"Error parsing {str(resp.url)}: {e}")
            return {"error": str(e)}

    async def collect_single_day(
        self,
        linkentry: LinksEntry,
    ) -> dict[str, Any]:

        loop_ret: dict[str, Any] = {
            "entity": linkentry.entity,
            "group": linkentry.group,
            "date": linkentry.date,
            "processed": len(linkentry.links),
            "docs": [],
            "complete_links": [],
            "parser_failed": [],
        }

        async for responses_ in self.http_client.get_many(
            linkentry.links_str, self.n_batch
        ):
            responses = cast(list[IResponse], responses_)

            loop_ret["http_ok"] = [r for r in responses if r.status_code in (200, 201)]
            ok_responses = loop_ret["http_ok"]
            loop_ret["http_failed"] = [
                str(r.url) for r in responses if r.status_code not in (200, 201)
            ]

            self.logger.debug(
                f"Fetched {len(ok_responses)} OK and {len(loop_ret['http_failed'])} NOK for {linkentry.entity} {linkentry.group} {linkentry.date}"
            )

            for resp in ok_responses:
                doc = self._parse(linkentry.entity, linkentry.group, linkentry, resp)
                if "error" in doc:
                    loop_ret["parser_failed"].append(str(resp.url))
                    continue
                loop_ret["docs"].append(doc)
                loop_ret["complete_links"].append(str(resp.url))
        return loop_ret
