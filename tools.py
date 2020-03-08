#!/usr/local/bin/python

import sys
import argparse
import binascii
import logging
import jsonlines
import redis

if __name__ == '__main__':
    logging.basicConfig()
    log = logging.getLogger('redis-tools')
    log.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description='some tools for managing redis data')

    parser.add_argument('--host', metavar='hostname', type=str, default='localhost', help='redis hostname')
    parser.add_argument('--port', metavar='port', type=str, default='6379', help='redis port')
    parser.add_argument('--db', metavar='db', type=str, default='0', help='redis database')

    subparsers = parser.add_subparsers(help='supported commands', dest='command')

    parser_export = subparsers.add_parser('export',
                                          help='export redis keys as jsonl with key data as base64')
    parser_import = subparsers.add_parser('import',
                                          help='import redis keys from jsonl with key data as base64')
    parser_export.add_argument(
        'keys', metavar='key', type=str, nargs='+', help='redis key or pattern (use "*", for whole db)')
    parser_export.add_argument(
        '-o', '--output', metavar='filename', default=sys.stdout, type=argparse.FileType('w'),
        help='output file (skip or set to "-" for stdout)')
    parser_export.add_argument('--noscan', action='store_true', default=False, help='do not use SCAN, but KEYS')
    parser_export.add_argument('--nosavettl', action='store_true', default=False, help='do not save TTLs')

    parser_import.add_argument(
        '-i', '--input', metavar='filename', default=sys.stdin, type=argparse.FileType('r'),
        help='input file (skip or set to "-" for stdin)')
    parser_import.add_argument(
        '-t', '--ttl', metavar='milliseconds', type=int, default=0,
        help='expire time in milliseconds (if you want to replace all TTLs stored in input file, use --ignorettl)')
    parser_import.add_argument(
        '--noreplace', action='store_true', default=False, help='do not replace existing keys')
    parser_import.add_argument(
        '--ignorettl', action='store_true', default=False, help='ignore key-specific TTLs')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    r = redis.Redis(host=args.host, port=args.port, db=args.db)

    if args.command == 'export':
        with jsonlines.Writer(args.output, sort_keys=True) as fh:
            for pattern in args.keys:
                for key in (r.keys(pattern) if args.noscan else r.scan_iter(pattern)):
                    pipe = r.pipeline()
                    pipe.dump(key)
                    pipe.pttl(key)
                    piperes = pipe.execute()
                    dumpres = piperes[0]
                    ttlres = piperes[1]
                    if dumpres is None:
                        log.warning('Could not store vanished key {}'.format(key))
                    else:
                        data = dict()
                        data['k'] = key.decode('utf-8')
                        data['x'] = binascii.b2a_base64(dumpres, newline=False).decode('utf-8')
                        if not args.nosavettl:
                            data['t'] = ttlres

                        fh.write(data)
        args.output.flush()

    if args.command == 'import':
        with jsonlines.Reader(args.input) as fh:
            for data in fh:
                key_bytes = binascii.a2b_base64(data['x'])
                restore_args = list()
                restore_args.append(data['k'])
                ttl = data.get('t', -1)
                if args.ignorettl or ttl < 0:
                    ttl = args.ttl
                restore_args.append(ttl)
                restore_args.append(key_bytes)
                if not args.noreplace:
                    restore_args.append('REPLACE')
                try:
                    r.restore(*restore_args)
                except redis.exceptions.ResponseError as why:
                    if str(why).startswith('BUSYKEY'):
                        log.info('Skipping restore for existing key "{}"'.format(data['k']))
                    else:
                        raise why
