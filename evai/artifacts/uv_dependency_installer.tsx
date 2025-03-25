# UV Command to Install Dependencies from pyproject.toml

## Basic Command

To install dependencies from a pyproject.toml file using UV, you can use:

```bash
uv pip install --requirement pyproject.toml
```

## Additional Options

For more control over the installation, you can use these options:

### Install in development mode
```bash
uv pip install --editable .
```

### Install with specific extras
```bash
uv pip install --requirement pyproject.toml --extra dev
```

### Install to a specific location or virtual environment
```bash
uv pip install --requirement pyproject.toml --target /path/to/target
```

### Install with pip compatibility mode
```bash
uv pip install --requirement pyproject.toml --pip-config.break-system-packages
```

## Performance Tips

- UV is designed for speed - it's typically 10-100x faster than pip
- For even faster installations, you can use:
  ```bash
  uv pip install --requirement pyproject.toml --no-deps
  ```
  (only if you're sure about dependency management)

## Common Issues

If you encounter errors:
- Ensure you have the latest version of UV installed
- Check that your pyproject.toml file is properly formatted
- Try running with `--verbose` flag for more detailed output