from datetime import date
from typing import Any

from ...app.repo.content_repo import IContentRepo


class FileContentRepoAdapter(IContentRepo):

    async def insert_content(
        self, entity_name: str, group: str, date: date, contents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Insert content documents into a file-based repository"""
        import json
        from pathlib import Path

        # Create directory structure if it doesn't exist
        dir = f"data/{entity_name}/{group}"
        dir_path = Path(dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Define file path
        file_path = dir_path / f"{date.isoformat()}.json"

        # Write contents to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(contents, f, ensure_ascii=False, indent=4)

        return {
            "inserted_count": len(contents),
            "file_path": file_path,
            "entity": entity_name,
            "group": group,
            "date": date.isoformat(),
        }

    async def read_content(
        self, entity_name: str, group: str, query: dict[str, Any]
    ) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        dir = f"data/{entity_name}/{group}"
        dir_path = Path(dir)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        results = []
        for file in dir_path.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                contents = json.load(f)
                for content in contents:
                    match = True
                    for key, value in query.items():
                        if content.get(key) != value:
                            match = False
                            break
                    if match:
                        results.append(content)

        return results
