#!/usr/bin/env python3
import subprocess
import json
import sys

def main():
    try:
        # Run the claude command and capture output
        result = subprocess.run(
            ['/Users/grey/.local/bin/claude', 'plugin', 'list', '--available', '--json'],
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout)

        # Handle different possible JSON structures
        if isinstance(data, list):
            plugins = data
        elif isinstance(data, dict):
            # Prioritize 'available' then 'plugins' keys
            plugins = data.get('available') or data.get('plugins')
            if plugins is None:
                # Fallback: find the first value that is a non-empty list
                for val in data.values():
                    if isinstance(val, list) and len(val) > 0:
                        plugins = val
                        break
                if plugins is None:
                    plugins = []
        else:
            plugins = []

        print(f'{"NAME":<25} {"VERSION":<10} {"DESCRIPTION"}')
        print('-' * 80)
        for p in plugins:
            if not isinstance(p, dict):
                continue
            name = str(p.get('name', ''))
            ver = str(p.get('version', ''))
            desc = str(p.get('description', ''))
            print(f'{name:<25} {ver:<10} {desc}')

    except subprocess.CalledProcessError as e:
        print(f"Error calling claude: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
