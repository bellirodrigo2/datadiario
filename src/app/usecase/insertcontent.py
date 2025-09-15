from dataclasses import dataclass
from datetime import date
from logging import Logger
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
        "metadata": {
            "entity": le.entity,
            "group": le.group,
            "date": le.date.strftime("%d-%m-%Y"),
            "link": link,
        },
        "doc": content,
    }


class ParserError(Exception):
    pass


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

        pendings = self.links_repo.get_pending_range(
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
                self.links_repo.mark_as_done(
                    entity_name=linkentry.entity,
                    group=linkentry.group,
                    date=linkentry.date,
                    links=loop_ret["complete_links"],
                )
                # OQUE FAZER AQUI SE DER ERRO
        return return_dict

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
            raise ParserError

    async def collect_single_day(
        self,
        linkentry: LinksEntry,
    ) -> dict[str, Any]:

        loop_ret: dict[str, Any] = {
            "entity": linkentry.entity,
            "group": linkentry.group,
            "date": linkentry.date,
            "docs": [],
            "complete_links": [],
            "http_failed": [],
            "parser_failed": [],
        }
        i = 0
        async for responses_ in self.http_client.get_many(
            linkentry.links_str, self.n_batch
        ):
            responses = cast(list[IResponse], responses_)
            loop_ret["http_ok"] = [r for r in responses if r.is_success]

            ok_responses = loop_ret["http_ok"]
            failed_responses = [r for r in responses if not r.is_success]
            loop_ret["http_failed"].extend([str(r.url) for r in failed_responses])

            self.logger.debug(
                f"{i}-Fetched {len(ok_responses)} OK and {len(failed_responses)} NOK for {linkentry.entity} {linkentry.group} {linkentry.date}"
            )
            i += 1

            for resp in ok_responses:
                try:
                    doc = self._parse(
                        linkentry.entity, linkentry.group, linkentry, resp
                    )
                except ParserError:
                    loop_ret["parser_failed"].append(str(resp.raw_url))
                    continue

                loop_ret["docs"].append(doc)
                loop_ret["complete_links"].append(str(resp.raw_url))

                if str(resp.raw_url) not in linkentry.links_str:
                    print(str(resp.raw_url))
        return loop_ret
