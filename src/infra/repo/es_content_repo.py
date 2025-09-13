from datetime import date
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import AsyncDocument, AsyncIndex, Date, Object, connections


class ContentDocument(AsyncDocument):
    """Base document for content storage"""

    date = Date()
    content = Object()  # Flexible object to store parsed JSON content

    class Index:
        # This will be set dynamically based on entity_name and group
        name = None

    @classmethod
    def get_index_name(cls, entity_name: str, group: str) -> str:
        """Generate index name based on entity and group"""
        return f"dou-{entity_name.lower()}-{group.lower().replace(' ', '-')}"


class ESContentRepoAdapter:

    def __init__(self, elasticsearch_url: str = "http://localhost:9200"):
        self.client = AsyncElasticsearch([elasticsearch_url])
        connections.add_connection("default", self.client)

    async def insert_content(
        self, entity_name: str, group: str, date: date, contents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Insert content documents into Elasticsearch"""

        index_name = ContentDocument.get_index_name(entity_name, group)

        # Ensure index exists with proper mapping
        await self._ensure_index_exists(index_name)

        # Prepare documents for bulk insert
        docs_to_insert = []
        for content_data in contents:
            doc = ContentDocument(date=date, content=content_data)
            doc.meta.index = index_name
            docs_to_insert.append(doc)

        # Bulk insert documents
        results = []
        for doc in docs_to_insert:
            result = await doc.save()
            results.append(result)

        return {
            "inserted_count": len(results),
            "index": index_name,
            "entity": entity_name,
            "group": group,
            "date": date.isoformat(),
        }

    async def read_content(
        self, entity_name: str, group: str, query: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Read content documents from Elasticsearch"""

        index_name = ContentDocument.get_index_name(entity_name, group)

        # Check if index exists
        if not await self._index_exists(index_name):
            return []

        # Build Elasticsearch query
        es_query = self._build_elasticsearch_query(query)

        # Execute search
        search = ContentDocument.search(index=index_name)
        search = search.query(es_query)

        # Get results
        response = await search.execute()

        # Convert to list of dictionaries
        results = []
        for hit in response:
            doc_dict = {
                "date": hit.date,
                "content": (
                    hit.content.to_dict()
                    if hasattr(hit.content, "to_dict")
                    else hit.content
                ),
                "_id": hit.meta.id,
                "_score": hit.meta.score,
            }
            results.append(doc_dict)

        return results

    async def _ensure_index_exists(self, index_name: str) -> None:
        """Ensure index exists with proper mapping"""
        if not await self._index_exists(index_name):
            # Create index with mapping
            index = AsyncIndex(index_name)
            index.document(ContentDocument)
            await index.create()

    async def _index_exists(self, index_name: str) -> bool:
        """Check if index exists"""
        return await self.client.indices.exists(index=index_name)

    def _build_elasticsearch_query(self, query: dict[str, Any]) -> dict[str, Any]:
        """Convert query dict to Elasticsearch query"""
        if not query:
            return {"match_all": {}}

        # Basic query builder - can be extended based on your needs
        must_clauses = []

        for key, value in query.items():
            if key == "date_range":
                # Handle date range queries
                date_query = {"range": {"date": value}}
                must_clauses.append(date_query)
            elif key == "text_search":
                # Handle text search in content
                text_query = {
                    "multi_match": {
                        "query": value,
                        "fields": ["content.*"],
                        "type": "best_fields",
                    }
                }
                must_clauses.append(text_query)
            else:
                # Handle exact matches in content fields
                term_query = {"term": {f"content.{key}": value}}
                must_clauses.append(term_query)

        if must_clauses:
            return {"bool": {"must": must_clauses}}
        else:
            return {"match_all": {}}

    async def close(self) -> None:
        """Close Elasticsearch connection"""
        await self.client.close()
