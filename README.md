# GrepNet - Network-aware Grep

Search for CIDR blocks, IP ranges, and network addresses in files using familiar grep-like syntax.

## Installation

### From source (development)

```bash
cd /home/chains/dev/grepnet

# Install in editable mode
pip install -e .

# Or run directly with PYTHONPATH
export PYTHONPATH=/home/chains/dev/grepnet/src
./bin/grepnet --help
```

### Standard installation

```bash
pip install grepnet
```

## Quick Start

```bash
# Search for a CIDR block
grepnet '192.0.2.0/24' config.txt

# Search for multiple patterns
grepnet -e '10.0.0.0/8' -e '172.16.0.0/12' *.txt

# Use stdin
echo "server 192.0.2.1" | grepnet '192.0.2.0/24'

# Show only subnet masks
grepnet '192.0.2.0 255.255.255.0' data.txt
```

## Project Structure

```
grepnet/
├── src/
│   └── grepnet/              # Main Python package
│       ├── __init__.py
│       ├── cli.py            # CLI interface
│       ├── grepnet.py        # Main orchestrator
│       ├── core/             # Data structures
│       │   ├── colorizer.py
│       │   ├── binary_detector.py
│       │   └── network_objects.py
│       ├── parsing/          # Network extraction
│       │   ├── network_parser.py
│       │   ├── comment_handler.py
│       │   └── extractors/   # Format-specific extractors
│       ├── input/            # Input source abstraction
│       ├── matching/         # Network comparison
│       └── output/           # Output formatting (future)
├── bin/
│   └── grepnet              # Executable entry point
├── tests/                    # Test suite (bash tests)
├── pyproject.toml           # Modern Python packaging
├── setup.py                 # Fallback packaging
├── GREPNET-SPEC.md          # Full specification
└── README.md                # This file
```

## Supported Network Formats

- **CIDR notation**: `192.0.2.0/24`, `2001:db8::/32`
- **Subnet mask**: `192.0.2.0 255.255.255.0`
- **Inverse mask**: `192.0.2.0 0.0.0.255`
- **IP ranges**: `192.0.2.0-192.0.2.255`
- **Bare IP addresses**: `192.0.2.1`, `2001:db8::1`

## Match Types

- **equals** (`me=`): Pattern and data are identical
- **subset** (`mb=`): Data is contained within pattern
- **superset** (`mS=`): Data contains pattern
- **overlap** (`mo=`): Partial overlap (ranges only)
- **unmatched** (`mu=`): No relationship

## Features

- ✅ IPv4 and IPv6 support
- ✅ Multiple input formats (CIDR, masks, ranges)
- ✅ Comment filtering (disable with `--no-filter-comments`)
- ✅ Strict CIDR validation mode
- ✅ Binary file detection (VTY protection)
- ✅ ANSI color output (configurable)
- ✅ Unified input handling (files, stdin, pipes)

## Development

See [GREPNET-SPEC.md](GREPNET-SPEC.md) for complete specification and architecture documentation.

See [IMPLEMENTATION-PYTHON.md](IMPLEMENTATION-PYTHON.md) for Python implementation details.

## Testing

```bash
# Run existing bash test suite
cd tests
bash run_tests.sh
```

## License

GPL-3.0-or-later
