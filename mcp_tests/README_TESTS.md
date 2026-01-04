# Tests

## Install
```bash
python -m pip install -U pytest pytest-asyncio httpx
```

## Run
From your project root:
```bash
pytest
```

Notes:
- These tests assume your package layout matches your imports (clients/, core/, sources/, tools/).
- Network calls are mocked using httpx.MockTransport.
