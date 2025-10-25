# Deep Biblio Tools

Post-processing of LLM artifacts for scientific text

## Installation

### From PyPI

```bash
uv add deep-biblio-tools
```

### From Source

```bash
git clone https://github.com/Mill-Hill-Garage/deep-biblio-tools
cd deep-biblio-tools
uv sync
```

## Usage

### Python API

```python
from deep_biblio_tools import DeepBiblioTools

# Initialize with default configuration
app = DeepBiblioTools()

# Process some data
data = {"input": "example"}
result = app.process(data)
print(f"Result: {result}")
```

### Web API

Start the development server:

```bash
uvicorn deep_biblio_tools.app:app --reload
```

The API will be available at http://localhost:8000

## Contributing

See [Contributing Guide](contributing.md) for development setup and guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
