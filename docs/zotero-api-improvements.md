# Zotero API Integration Improvements

This document outlines planned improvements to the Zotero API integration to follow best practices and improve efficiency when processing large numbers of citations.

## Current State

The current implementation provides basic Zotero integration:
- ✅ SQLite cache for citation metadata (30-day TTL)
- ✅ Basic API requests to Zotero translation server
- ✅ Library search functionality
- ❌ No conditional requests or version tracking
- ❌ No rate limit handling
- ❌ No backoff handling
- ❌ No incremental syncing

## Planned Improvements

### 1. Conditional Requests and Version Tracking

**Goal**: Minimize API requests by tracking library versions and making conditional requests.

**Implementation Plan**:
```python
# Add to citation_cache.py
class ZoteroVersionCache:
    """Track Zotero library versions for conditional requests."""

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "zotero_versions.json"
        self.versions = self._load_versions()

    def get_library_version(self, library_id: str) -> int | None:
        """Get the last known version of a library."""
        return self.versions.get(library_id)

    def update_library_version(self, library_id: str, version: int):
        """Update the stored version for a library."""
        self.versions[library_id] = version
        self._save_versions()
```

**Usage**:
- Store `Last-Modified-Version` header from multi-object requests
- Include `If-Modified-Since-Version: <version>` in subsequent requests
- Handle 304 Not Modified responses by using cached data

### 2. Rate Limiting and Retry Logic

**Goal**: Gracefully handle rate limits and server overload conditions.

**Implementation Plan**:
```python
# Add to zotero_integration.py
class RateLimitHandler:
    """Handle rate limiting for Zotero API requests."""

    def __init__(self):
        self.backoff_until = None
        self.retry_after = None

    def check_response_headers(self, response):
        """Check for rate limit headers in response."""
        # Check for Backoff header
        if 'Backoff' in response.headers:
            seconds = int(response.headers['Backoff'])
            self.backoff_until = time.time() + seconds
            logger.info(f"Backoff requested: {seconds} seconds")

        # Check for 429 with Retry-After
        if response.status_code == 429 and 'Retry-After' in response.headers:
            seconds = int(response.headers['Retry-After'])
            self.retry_after = time.time() + seconds
            logger.warning(f"Rate limited. Retry after: {seconds} seconds")

    def wait_if_needed(self):
        """Wait if we're in a backoff or retry-after period."""
        now = time.time()

        if self.retry_after and now < self.retry_after:
            wait_time = self.retry_after - now
            logger.info(f"Waiting {wait_time:.1f}s due to rate limit")
            time.sleep(wait_time)

        elif self.backoff_until and now < self.backoff_until:
            wait_time = self.backoff_until - now
            logger.info(f"Waiting {wait_time:.1f}s due to backoff")
            time.sleep(wait_time)
```

### 3. Request Batching and Concurrency Control

**Goal**: Efficiently process multiple citations while respecting API limits.

**Implementation Plan**:
```python
# Add to citation_manager.py
class BatchProcessor:
    """Process citations in batches with concurrency control."""

    def __init__(self, max_concurrent: int = 3, batch_size: int = 50):
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.rate_limiter = RateLimitHandler()

    async def process_citations(self, citations: list[Citation]):
        """Process citations in batches with controlled concurrency."""
        # Split into batches
        batches = [citations[i:i + self.batch_size]
                   for i in range(0, len(citations), self.batch_size)]

        # Process batches with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_batch(batch):
            async with semaphore:
                return await self._fetch_batch_metadata(batch)

        # Process all batches
        results = await asyncio.gather(
            *[process_batch(batch) for batch in batches]
        )
        return results
```

### 4. Incremental Library Sync

**Goal**: Only fetch items that have changed since last sync.

**Implementation Plan**:
```python
# Add to zotero_integration.py
def sync_library_changes(self, since_version: int = None):
    """Sync only items that have changed since the given version."""
    params = {
        'format': 'json',
        'limit': 100  # Process in chunks
    }

    if since_version:
        params['since'] = since_version

    # Fetch changed items
    url = f"{self.base_url}/users/{self.library_id}/items"

    all_items = []
    while url:
        response = self._make_request(url, params=params)

        # Store the new library version
        if 'Last-Modified-Version' in response.headers:
            new_version = int(response.headers['Last-Modified-Version'])
            self.version_cache.update_library_version(self.library_id, new_version)

        # Process items
        items = response.json()
        all_items.extend(items)

        # Check for next page
        links = self._parse_link_header(response.headers.get('Link', ''))
        url = links.get('next')
        params = {}  # Clear params for subsequent requests

    return all_items
```

### 5. Enhanced Cache Management

**Goal**: Implement intelligent caching that respects API versioning.

**Implementation Plan**:
```python
# Enhanced citation cache with version awareness
class EnhancedCitationCache(CitationCache):
    """Citation cache with version tracking and conditional request support."""

    def get_if_fresh(self, url: str, library_version: int = None) -> dict | None:
        """Get cached item only if it's fresh relative to library version."""
        cached = self.get(url)

        if not cached:
            return None

        # If we have a library version, check if cache is stale
        if library_version and cached.get('cached_at_version'):
            if cached['cached_at_version'] < library_version:
                return None  # Cache is stale

        return cached

    def store_with_version(self, url: str, data: dict, library_version: int):
        """Store data with version information."""
        data['cached_at_version'] = library_version
        data['cached_at'] = datetime.now().isoformat()
        self.store(url, data)
```

## Implementation Priority

1. **Phase 1**: Rate limiting and retry logic (High priority)
   - Prevents getting blocked
   - Essential for processing large documents

2. **Phase 2**: Conditional requests and version tracking (Medium priority)
   - Reduces API load
   - Speeds up subsequent runs

3. **Phase 3**: Batch processing and concurrency control (Medium priority)
   - Improves performance
   - Better user experience

4. **Phase 4**: Incremental sync and enhanced caching (Low priority)
   - Optimization for frequent users
   - Most beneficial for large libraries

## Testing Strategy

1. **Unit tests** for each component
2. **Integration tests** with mock Zotero API responses
3. **Rate limit testing** with artificial delays
4. **Performance benchmarks** for large citation sets

## Configuration

Add new configuration options to `.env`:

```bash
# Zotero API Configuration (existing)
ZOTERO_API_KEY=your_key
ZOTERO_LIBRARY_ID=your_id

# New options
ZOTERO_MAX_CONCURRENT_REQUESTS=3
ZOTERO_BATCH_SIZE=50
ZOTERO_CACHE_TTL_DAYS=30
ZOTERO_RESPECT_BACKOFF=true
```

## Migration Path

1. Keep existing functionality intact
2. Add new features behind feature flags
3. Gradually migrate to new implementation
4. Provide clear upgrade documentation

## Expected Benefits

- **Reduced API requests**: 50-80% reduction through caching and conditional requests
- **Better reliability**: Graceful handling of rate limits
- **Faster processing**: Batch operations and concurrency
- **Lower server load**: Respecting backoff headers
- **Future-proof**: Following Zotero API best practices

## References

- [Zotero Web API v3 Documentation](https://www.zotero.org/support/dev/web_api/v3/basics)
- [Zotero API Rate Limiting](https://www.zotero.org/support/dev/web_api/v3/basics#rate_limiting)
- [Zotero Syncing Documentation](https://www.zotero.org/support/dev/web_api/v3/syncing)
