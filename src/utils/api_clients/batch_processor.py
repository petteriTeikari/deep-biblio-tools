"""Batch processing for API requests to improve performance."""

# Standard library imports
import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# Local imports
from .base import APIClient


class BatchAPIProcessor:
    """Process multiple API requests in batches for improved performance."""

    def __init__(
        self,
        api_client: APIClient,
        batch_size: int = 10,
        max_workers: int = 5,
        logger: logging.Logger | None = None,
    ):
        """Initialize batch processor.

        Args:
            api_client: The API client to use for requests
            batch_size: Maximum number of requests per batch
            max_workers: Maximum number of concurrent workers
            logger: Logger instance (creates one if not provided)
        """
        self.api_client = api_client
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)

    def process_batch(
        self,
        items: list[dict[str, Any]],
        request_builder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]],
        result_processor: Callable[[dict[str, Any], dict[str, Any]], Any]
        | None = None,
    ) -> list[tuple[dict[str, Any], Any]]:
        """Process a batch of items through the API.

        Args:
            items: List of items to process
            request_builder: Function that takes an item and returns (endpoint, params)
            result_processor: Optional function to process results

        Returns:
            List of (item, result) tuples
        """
        results = []

        # Process in chunks to respect batch size
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = self._process_batch_chunk(
                batch, request_builder, result_processor
            )
            results.extend(batch_results)

        return results

    def _process_batch_chunk(
        self,
        batch: list[dict[str, Any]],
        request_builder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]],
        result_processor: Callable[[dict[str, Any], dict[str, Any]], Any]
        | None = None,
    ) -> list[tuple[dict[str, Any], Any]]:
        """Process a single batch chunk."""
        results = []

        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(batch))
        ) as executor:
            # Submit all requests
            future_to_item = {}

            for item in batch:
                try:
                    endpoint, params = request_builder(item)
                    future = executor.submit(
                        self.api_client.request, endpoint, params
                    )
                    future_to_item[future] = item
                except Exception as e:
                    self.logger.error(
                        f"Error building request for item {item}: {e}"
                    )
                    results.append((item, None))

            # Collect results as they complete
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    response = future.result()
                    if result_processor:
                        result = result_processor(item, response)
                    else:
                        result = response
                    results.append((item, result))
                except Exception as e:
                    self.logger.error(f"Error processing item {item}: {e}")
                    results.append((item, None))

        return results

    async def process_batch_async(
        self,
        items: list[dict[str, Any]],
        request_builder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]],
        result_processor: Callable[[dict[str, Any], dict[str, Any]], Any]
        | None = None,
    ) -> list[tuple[dict[str, Any], Any]]:
        """Process a batch of items asynchronously.

        Args:
            items: List of items to process
            request_builder: Function that takes an item and returns (endpoint, params)
            result_processor: Optional function to process results

        Returns:
            List of (item, result) tuples
        """
        results = []

        # Process in chunks to respect batch size
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = await self._process_batch_chunk_async(
                batch, request_builder, result_processor
            )
            results.extend(batch_results)

        return results

    async def _process_batch_chunk_async(
        self,
        batch: list[dict[str, Any]],
        request_builder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]],
        result_processor: Callable[[dict[str, Any], dict[str, Any]], Any]
        | None = None,
    ) -> list[tuple[dict[str, Any], Any]]:
        """Process a single batch chunk asynchronously."""
        tasks = []

        for item in batch:
            task = self._process_single_item_async(
                item, request_builder, result_processor
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Pair results with items
        paired_results = []
        for item, result in zip(batch, results):
            if isinstance(result, Exception):
                self.logger.error(f"Error processing item {item}: {result}")
                paired_results.append((item, None))
            else:
                paired_results.append((item, result))

        return paired_results

    async def _process_single_item_async(
        self,
        item: dict[str, Any],
        request_builder: Callable[[dict[str, Any]], tuple[str, dict[str, Any]]],
        result_processor: Callable[[dict[str, Any], dict[str, Any]], Any]
        | None = None,
    ) -> Any:
        """Process a single item asynchronously."""
        try:
            endpoint, params = request_builder(item)

            # Run the synchronous API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.api_client.request, endpoint, params
            )

            if result_processor:
                return result_processor(item, response)
            return response

        except Exception as e:
            self.logger.error(f"Error processing item {item}: {e}")
            raise


class BatchDOIProcessor(BatchAPIProcessor):
    """Specialized batch processor for DOI lookups."""

    def process_dois(self, dois: list[str]) -> dict[str, dict[str, Any]]:
        """Process multiple DOIs in batch.

        Args:
            dois: List of DOIs to process

        Returns:
            Dictionary mapping DOI to metadata
        """
        # Create items for processing
        items = [{"doi": doi} for doi in dois]

        # Define request builder
        def request_builder(item):
            return f"works/{item['doi']}", {}

        # Process batch
        results = self.process_batch(items, request_builder)

        # Convert to dictionary
        doi_to_metadata = {}
        for item, result in results:
            if result:
                doi_to_metadata[item["doi"]] = result

        return doi_to_metadata


class BatchArXivProcessor(BatchAPIProcessor):
    """Specialized batch processor for arXiv lookups."""

    def process_arxiv_ids(
        self, arxiv_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Process multiple arXiv IDs in batch.

        Args:
            arxiv_ids: List of arXiv IDs to process

        Returns:
            Dictionary mapping arXiv ID to metadata
        """
        # Create items for processing
        items = [{"arxiv_id": arxiv_id} for arxiv_id in arxiv_ids]

        # Define request builder
        def request_builder(item):
            return "query", {"id_list": item["arxiv_id"]}

        # Process batch
        results = self.process_batch(items, request_builder)

        # Convert to dictionary
        arxiv_to_metadata = {}
        for item, result in results:
            if result:
                arxiv_to_metadata[item["arxiv_id"]] = result

        return arxiv_to_metadata
