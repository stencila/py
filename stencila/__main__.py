"""
A main file used when running this module e.g. `python -m stencila`

A command line interface, primarily intended for machine use,
such as spawning new hosts. Provide a function name as first argument
and function options as a JSON object in the second argument or
standard input. e.g.

  python -m stencila spawn '{"port":2300}'
  echo '{"port":2300}' | python -m stencila spawn
"""
import json
import stencila
import sys

# Function to execute
name = sys.argv[1] if len(sys.argv) > 1 else 'run'
func = vars(stencila).get(name)
if not func:
    print('Not a valid function: ' + name)
    sys.exit(1)


# Function options as JSON object from second argument or stdin
inp = sys.argv[2] if len(sys.argv) > 2 else ''
options = {}
if len(inp):
    try:
        options = json.loads(inp)
    except:
        print('Error parsing JSON options: ' + inp)
        sys.exit(1)

# Execute the function and output any result as JSON
result = func(**options)
if result:
    out = json.dumps(result)
    print(out)
