try:
    from .parser import JavaPlusPlusParser, parse_file, parse_str
except ImportError:
    from javapp.parser import JavaPlusPlusParser, parse_file, parse_str
from java import tokenize, JavaParser, JavaSyntaxError, tree

import unittest

class UnitTests(unittest.TestCase):
    # def test_parser(self):
    #     import os.path
    #     import pprint
    #     from pathlib import Path
    #     from textwrap import indent
    #     self.maxDiff = None
    #     with open(os.path.join(os.path.dirname(__file__), 'test.java'), 'rb') as file:
    #         java_unit = parse_file(file, parser=JavaParser)
    #     with open(os.path.join(os.path.dirname(__file__), 'test.javapp'), 'rb') as file:
    #         javapp_unit = parse_file(file, parser=JavaPlusPlusParser)
    #     self.assertEqual(java_unit, javapp_unit, f"java_unit != javapp_unit.\njava_unit:\n{indent(pprint.pformat(java_unit), '    ')}\njavapp_unit:\n{indent(pprint.pformat(javapp_unit), '    ')}")
    #     java_unit_str = str(java_unit)
    #     javapp_unit_str = str(javapp_unit)
    #     self.assertEqual(java_unit_str, javapp_unit_str, f"str(java_unit) != str(javapy_unit).")

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        self.maxDiff = None

    import functools
    import os
    from pathlib import Path

    test_files = Path(os.path.dirname(__file__), 'test_files')

    def test(self, test_folder):
        import pprint
        from textwrap import indent
        with test_folder.joinpath(test_folder.name + '.java').open('rb') as file:
            java_unit = parse_file(file, parser=JavaParser)
        with test_folder.joinpath(test_folder.name + '.javapp').open('rb') as file:
            parser = JavaPlusPlusParser(tokenize(file.readline), file.name)
            parser.enable_feature('*', False)
            parser.enable_feature('syntax.multiple_import_sections', True)
            parser.enable_feature('statements.print', True)
            javapp_unit = parser.parse_compilation_unit()
        self.assertEqual(java_unit, javapp_unit, f"java_unit != javapp_unit.\njava_unit:\n{indent(pprint.pformat(java_unit), '    ')}\njavapp_unit:\n{indent(pprint.pformat(javapp_unit), '    ')}")
        java_unit_str = str(java_unit)
        javapp_unit_str = str(javapp_unit)
        self.assertEqual(java_unit_str, javapp_unit_str, f"str(java_unit) != str(javapy_unit).")

    for test_folder in test_files.iterdir():
        if test_folder.is_dir():
            locals()['test_' + test_folder.name] = functools.partialmethod(test, test_folder)            

    del test, test_files, test_folder, functools, os, Path

def main(args=None):
    import argparse
    import sys, os
    import os.path
    from inspect import isfunction, signature, Parameter
    from pathlib import Path
    from typing import List, Type
    from textwrap import wrap

    def get_parse_methods(cls):
        for func in vars(cls).values():
            if isfunction(func) and func.__name__.startswith("parse_"):
                sig = signature(func)
                params = sig.parameters
                
                if len(params) == 1 and 'self' in params:
                    valid = True
                else:
                    for param in params.values():
                        if param.default is Parameter.empty:
                            valid = False
                            break
                if valid:
                    yield func.__name__[6:]

    argparser = argparse.ArgumentParser(description='Parse a javapy file')
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--list-features', '-lf', action='store_true',
        help='Print a list of supported feature names to the -e and -d options and exit. ')
    group.add_argument('--list-parse-methods', '-lp', type=int, metavar='NUM_COLUMNS', nargs='?', const=3,
        help='Print a list of valid arguments to the --parse option and exit. '
             'If there is exactly one positional argument, it is interpreted as the number of columns to output.')
    group.add_argument('--parse', '-p', metavar='PARSE_METHOD',
        help='Instead of parsing a file, parse the argument as this type and display the resulting Java code.')
    argparser.add_argument('--out', '-o', metavar='FILE', type=Path, action='append', default=[],
        help='Where to save the output. Special name "STDOUT" can be used to output to the console. '
             'Special name "NUL" can be used to not output anything at all. '
             'This option can be used multiple times in the case of multiple input files.')
    argparser.add_argument('--enable', '-e', metavar='FEATURES', action='append', default=[],
        help='Enable the specified comma-separated features by default')
    argparser.add_argument('--disable', '-d', metavar='FEATURES', action='append', default=[],
        help='Disable the specified comma-separated features by default')
    argparser.add_argument('--java', action='store_true',
        help='Use a vanilla Java parser instead of the Java++ parser.')
    argparser.add_argument('files', metavar='FILE', nargs='*',
        help='The file(s) or code to parse.')

    if argparser.usage is None:
        argparser.usage = '\n'.join(line if i == 0 else ' '*(8+len(argparser.prog)) + line for i, line in enumerate(wrap(argparser.prog + ' [-h] [--list-features | --list-parse-methods\xA0[NUM_COLUMNS] | --parse\xA0PARSE_METHOD [--out\xA0FILE] [--java | [--enable\xA0FEATURES] [--disable\xA0FEATURES]] [CODE\xA0[CODE\xA0...]] | [--java | [--enable\xA0FEATURES] [--disable\xA0FEATURES]] FILE\xA0[--out\xA0FILE] [FILE\xA0[--out\xA0FILE]\xA0...]]', width=80)))
        
    def error(*messages):
        print(argparser.usage)
        print(argparser.prog +': error:', *messages)
        exit(1)

    args = argparser.parse_args(args)

    if args.list_features:
        if args.out:
            error('argument --out/-o: not allowed with argument --list-features/-lf')
        if args.enable:
            error('argument --enable/-e: not allowed with argument --list-features/-lf')
        if args.disable:
            error('argument --disable/-d: not allowed with argument --list-features/-lf')
        if args.files:
            error('argument FILE: not allowed with argument --list-features')
        print(*sorted(JavaPlusPlusParser.supported_features), sep='\n', end='\n\n')
        print('Use a ".*" at the end of a namespace to use everything from that namespace.')
        print('A "*" by itself means "use every feature".')
        return

    if args.list_parse_methods is not None:
        if args.out:
            error('argument --out: not allowed with argument --list-parse-methods')
        if args.enable:
            error('argument --enable: not allowed with argument --list-parse-methods')
        if args.disable:
            error('argument --disable: not allowed with argument --list-parse-methods')
        if args.files:
            error('argument FILE: not allowed with argument --list-parse-methods')

        NUM_COLUMNS = args.list_parse_methods

        if NUM_COLUMNS <= 0:
            error('argument NUM_COLUMNS: invalid value: must be at least 1')
        
        parse_methods = sorted({*get_parse_methods(JavaParser), *get_parse_methods(JavaPlusPlusParser)})

        colsize = len(parse_methods) // NUM_COLUMNS

        leftover = len(parse_methods)
        while leftover >= colsize:
            leftover -= colsize

        col_sizes = [colsize]*NUM_COLUMNS

        add_idx = 0
        while leftover:
            col_sizes[add_idx] += 1
            leftover -= 1
            add_idx += 1

        names = [[] for _ in range(NUM_COLUMNS)]
        name_lens = [0]*NUM_COLUMNS

        row = col = 0
        for name in parse_methods:
            names[col].append(name)
            if len(name) > name_lens[col]:
                name_lens[col] = len(name)
            row += 1
            if row >= col_sizes[col]:
                row = 0
                col += 1
                if col >= NUM_COLUMNS:
                    col = 0

        fmt = ""
        for i, length in enumerate(name_lens):
            fmt += f"{{0[{i}]:<{length}}}  "

        size = max([len(lst) for lst in names])
        for lst in names:
            if len(lst) < size:
                lst.extend([""]*(size - len(lst)))
                assert len(lst) == size

        for i in range(size):
            l = []
            for lst in names:
                l.append(lst[i])
            print(fmt.format(l))

        print()

        message = \
                'Some parse methods may not support all syntax features, and some ' \
                'parse methods may not return a Node instance and thus their ' \
                'formatted output may be unexpected.'
        
        print(*wrap(message, width=80), sep='\n')

        return

  
    files: List[str] = args.files
    outfiles: List[Path] = args.out
    parse: str = args.parse
    enabled_features: List[str] = args.enable
    disabled_features: List[str] = args.disable

    if args.java:
        Parser = JavaParser

        if enabled_features:
            error('argument --java: not allowed with argument --enable/-e')
        elif disabled_features:
            error('argument --java: not allowed with argument --disable/-d')

    else:
        Parser = JavaPlusPlusParser

    if parse:
        import io

        if len(files) == 1 and files[0] == 'STDIN' or len(files) == 0:
            parser = Parser(tokenize(sys.stdin.buffer.readline), '<stdin>')
        else:
            if 'STDIN' in files:
                error('STDIN can only be used as an input file if there are no other input files')
            parser = Parser(tokenize(io.BytesIO(bytes(' '.join(files), 'utf-8')).readline), '<string>')

        if Parser is JavaPlusPlusParser:
            try:
                for features in enabled_features:
                    for feature in features.split(','):
                        parser.enable_feature(feature)
                for features in disabled_features:
                    for feature in features.split(','):
                        parser.enable_feature(feature, False)
            except ValueError as e:    
                error(e)

        if not hasattr(parser, 'parse_' + parse):
            error('invalid option for --parse/-p:', parse)
        unit = getattr(parser, 'parse_' + parse)()

        if len(outfiles) > 1:
            error('unrecognized arguments:', *outfiles[1:])

        if len(outfiles) == 0 or str(outfiles[0]) != 'NUL':
            if outfiles and str(outfiles[0]) != 'STDOUT':
                file = sys.stdout = outfiles[0].open('rb')
            else:
                file = None
            
            try:
                if isinstance(unit, (list, tuple)):
                    for elem in unit:
                        if isinstance(elem, tree.Node):
                            print(str(elem))
                        else:
                            print(repr(elem))
                        print()
                else:
                    print(str(unit))

            finally:
                if file:
                    sys.stdout = sys.__stdout__
                    file.close()
                    print('Wrote to', file.name)

    else:
        # if len(files) == 0:
        #     error('the following arguments are required: FILE')

        parsers = []
        output = []
        if len(files) == 0:
            import io
            parsers.append(Parser(tokenize(sys.stdin.buffer.readline), '<stdin>'))

            if outfiles:
                if len(outfiles) != 1:
                    error('number of output files is not the same as number of input files')
                if str(outfiles[0]) == 'STDOUT':
                    filename = '<stdout>'
                elif str(outfiles[0]) == 'NUL':
                    filename = None
                else:
                    filename = outfiles[0]

            else:
                filename = None

            output.append(filename)

        else:
            multiple_stdout_files = False
            if outfiles:
                if len(outfiles) != len(files):
                    error('number of output files is not the same as number of input files')
                for filename in files:
                    with open(filename, 'rb') as file:
                        parsers.append(Parser(tokenize(file.readline), filename))
                output = outfiles
                found_stdout_file = False
                for i, outfile in enumerate(output):
                    if str(outfile) == "STDOUT":
                        if found_stdout_file:
                            multiple_stdout_files = True
                        else:
                            found_stdout_file = True
                        output[i] = '<stdout>'
            else:
                for filename in files:
                    with open(filename, 'rb') as file:
                        parsers.append(Parser(tokenize(file.readline), filename))
                        output.append(Path(os.path.dirname(os.path.realpath(filename)), os.path.splitext(os.path.basename(filename))[0] + '.java'))

        assert len(parsers) == len(output), f"len(parsers) ({len(parsers)}) is not equal to len(output) ({len(output)})"

        for parser, outpath in zip(parsers, output):
            unit = parser.parse_compilation_unit()
            
            if Parser is JavaPlusPlusParser:
                try:
                    for features in args.enable:
                        for feature in features.split(','):
                            parser.enable_feature(feature)
                    for features in args.disable:
                        for feature in features.split(','):
                            parser.enable_feature(feature, False)
                except ValueError as e:    
                    error(e)

            if outpath == '<stdout>':
                if multiple_stdout_files:
                    print('File', parser.filename + ':')
                    print(unit)
                    print('==========================================================')
                else:
                    print(unit)
            elif outpath is not None:
                assert isinstance(outpath, Path), f"outpath ({outpath!r}) is not an instance of Path"
                with outpath.open('w') as file:
                    file.write(str(unit))
                    print("Converted", file.name)
        

if __name__ == "__main__":
    main()