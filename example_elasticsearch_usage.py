"""
Example usage of ESContentRepoAdapter
"""

import asyncio
from datetime import date

from infra.repo.es_content_repo import ESContentRepoAdapter


async def example_usage():
    # Initialize repository
    repo = ESContentRepoAdapter("http://localhost:9200")

    # Example content data
    sample_contents = [
        {
            "title": "Nova Lei de Contratações Públicas",
            "content": "Conteúdo da lei...",
            "type": "lei",
            "numero": "12345/2024",
            "orgao": "Presidência da República",
        },
        {
            "title": "Edital de Licitação",
            "content": "Detalhes do edital...",
            "type": "edital",
            "numero": "001/2024",
            "valor": "R$ 1.000.000,00",
        },
    ]

    # Insert content
    result = await repo.insert_content(
        entity_name="BR",
        group="contratacoes",
        date=date.today(),
        contents=sample_contents,
    )
    print(f"Inserted: {result}")

    # Query examples

    # 1. Search by text
    text_results = await repo.read_content(
        entity_name="BR", group="contratacoes", query={"text_search": "licitação"}
    )
    print(f"Text search results: {len(text_results)}")

    # 2. Search by exact field
    exact_results = await repo.read_content(
        entity_name="BR", group="contratacoes", query={"type": "lei"}
    )
    print(f"Exact search results: {len(exact_results)}")

    # 3. Date range search
    date_results = await repo.read_content(
        entity_name="BR",
        group="contratacoes",
        query={"date_range": {"gte": "2024-01-01", "lte": "2024-12-31"}},
    )
    print(f"Date range results: {len(date_results)}")

    # 4. Combined query
    combined_results = await repo.read_content(
        entity_name="BR",
        group="contratacoes",
        query={"type": "edital", "text_search": "licitação"},
    )
    print(f"Combined search results: {len(combined_results)}")

    # Close connection
    await repo.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
