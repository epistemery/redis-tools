# About

Simple Python script providing tools for exporting/importing selected
keys from/to a Redis database. Keys may be specified using patterns
as utilized by Redis' `SCAN` and `KEYS` commands
(e.g. "prefix:*:suffix").

Works with Python 3.7 (probably also > 3.7, not tested). Needs the
following Python packages: `redis @ 3.4.1` and `jsonlines @ 1.2.0`

Produces JSONL-Files (one JSON object each line). Stores binary key
data as Base64-coded strings. Also stores key TTLs by default
(can be switched off by using `--nosavettl`).

**NOTE**: When using `SCAN` for key discovery, there may be duplicate
keys. This is due to implementation of the `SCAN` command.
By default, the `import` subcommand replaces existing keys, so that
there are no errors when importing duplicate keys. It is also possible
to utilize the `KEYS` command using the switch `--noscan` in
order to avoid this behavior. But this also means more memory usage 
when dealing with large databases, because the script has to hold all 
key names in memory.

**NOTE**: There is limited "atomicity" when exporting Redis data
using this script. The keys are dumped sequentially, after querying
Redis for relevant keys. If, at the time of dumping, a key has
vanished, a warning is logged and the key is not stored. The maximum
level of "atomicity" can be achieved by using the `--noscan` switch.
This guarantees that for every key present at the time of querying a
specific key or pattern, a dump *attempt* will be made *after* the
initial `KEYS` query for *that particular pattern* (i.e. a single
positional argument to `export`). If the key does not exist anymore,
the key is dropped.

# Basic usage

```
# python tools.py -h

usage: tools.py [-h] [--host hostname] [--port port] [--db db]
                {export,import} ...

some tools for managing redis data

positional arguments:
  {export,import}  supported commands
    export         export redis keys as jsonl with key data as base64
    import         import redis keys from jsonl with key data as base64

optional arguments:
  -h, --help       show this help message and exit
  --host hostname  redis hostname
  --port port      redis port
  --db db          redis database
```

```
# python tools.py export -h

usage: tools.py export [-h] [-o filename] [--noscan] [--nosavettl]
                       key [key ...]

positional arguments:
  key                   redis key or pattern (use "*", for whole db)

optional arguments:
  -h, --help            show this help message and exit
  -o filename, --output filename
                        output file (skip or set to "-" for stdout)
  --noscan              do not use SCAN, but KEYS
  --nosavettl           do not save TTLs
```

```
# python tools.py import -h

usage: tools.py import [-h] [-i filename] [-t milliseconds] [--noreplace]
                       [--ignorettl]

optional arguments:
  -h, --help            show this help message and exit
  -i filename, --input filename
                        input file (skip or set to "-" for stdin)
  -t milliseconds, --ttl milliseconds
                        expire time in milliseconds (if you want to replace
                        all TTLs stored in input file, use --ignorettl)
  --noreplace           do not replace existing keys
  --ignorettl           ignore key-specific TTLs
```

## Running in docker container (tl;dr)

### Export

```
docker run -i --rm --network host redis-tools export "*" > dump.jsonl
```

### Import

```
docker run -i --rm --network host redis-tools import < dump.jsonl
```

It is important, especially when importing with redirection of stdin,
that the `-i` flag of `docker run` is set and the `-t` flag
is **not** set in order for redirection to work properly.
