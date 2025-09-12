from typing import Iterable, Protocol
from bs4 import BeautifulSoup
from bs4.element import Tag


class ParsedHtml(Protocol):

    @property
    def text(self) -> str: ...

    def find_byid(self, id: str) -> 'ParsedHtml': ...
    def find_byclass(self, class_: str) -> 'ParsedHtml': ...
    def find_bytext(self, text: str) -> 'ParsedHtml': ...
    def findall_byid(self, id: str) -> Iterable['ParsedHtml']: ...
    def findall_byclass(self, class_: str) -> Iterable['ParsedHtml']: ...
    def findall_bytext(self, text: str) -> Iterable['ParsedHtml']: ...

class SoupParsed(ParsedHtml):
    def __init__(
        self, html: str | Tag, parser: str = "lxml"
    ):  # parser = lxml, html.parser or html5lib
        self.soup = BeautifulSoup(html, parser) if isinstance(html, str) else html

    @property
    def text(self) -> str:
        return self.soup.get_text(strip=True)
        # return self.soup.text

    def find_byid(self, id: str) -> "SoupParsed":
        tag = self.soup.find(id=id)
        if tag is None:
            raise KeyError(f'No tag "{id}" found by id.\n "{self.soup.text}"')
        else:
            return SoupParsed(tag)  # type: ignore

    def find_byclass(self, class_: str) -> "SoupParsed":
        tag = self.soup.find(class_=class_)
        if tag is None:
            raise KeyError('No tag "{class_}" found by id.\n "{self.soup.text}"')
        return SoupParsed(tag)  # type: ignore

    def find_bytext(self, text):
        string = self.soup.find(string=text)
        if string is None:
            raise KeyError(f'No tag with text "{text}" found.\n "{self.soup.text}"')
        return SoupParsed(string.parent)  # go up to the parent tag

    def findall_byid(self, id: str) -> Iterable["SoupParsed"]:
        tags = self.soup.find_all(id=id)
        # if not tags:
            # raise KeyError('No tag "{id}" found by id.\n "{self.soup.text}"')
        return [SoupParsed(tag) for tag in tags]  # type: ignore

    def findall_byclass(self, class_: str) -> Iterable["SoupParsed"]:
        tags = self.soup.find_all(class_=class_)
        # if not tags:
            # raise KeyError('No tag "{class_}" found by id.\n "{self.soup.text}"')
        return [SoupParsed(tag) for tag in tags]  # type: ignore

    def findall_bytext(self, text: str) -> Iterable["SoupParsed"]:
        tags = self.soup.find_all(string=text)
        # if not tags:
            # raise KeyError('No tag "{text}" found by text.\n "{self.soup.text}"')
        return [SoupParsed(tag.parent) for tag in tags]  # type: ignore
    

if __name__ == "__main__":
    ...
