import io
import java.tree as tree
from java.parser import JavaParser, JavaSyntaxError, parse_file as java_parse_file, parse_str as java_parse_str
from java.tokenize import *
from typeguard import check_type, check_argument_types
from typing import Union, List, Optional, Type, Tuple, Set

class JavaPlusPlusParser(JavaParser):
    #region init
    supported_features = {
        'statements.print', 'expressions.class_creator', 'literals.collections', 'trailing_commas.argument', 'trailing_commas.other',
        'syntax.argument_annotations', 'auto_imports.types', 'auto_imports.statics', 'syntax.multiple_import_sections',
        'literals.optional',
    }
                                    
    auto_imports = {
        'java.util': {
            'List', 'Set', 'Map', 'ArrayList', 'HashSet', 'HashMap',
            'EnumSet', 'Collection', 'Iterator', 'Collections', 'Arrays',
            'Calendar', 'Date', 'EnumMap', 'GregorianCalendar', 'Locale',
            'Objects', 'Optional', 'OptionalDouble', 'OptionalInt', 'OptionalLong',
            'Properties', 'Random', 'Scanner', 'Spliterators', 'Spliterator', 'Timer',
            'SimpleTimeZone', 'TimeZone', 'UUID', 'ConcurrentModificationException',
            'NoSuchElementException'
        },
        'java.util.stream': {
            'Collector', 'DoubleStream', 'IntStream', 'LongStream', 'Stream',
            'Collectors', 'StreamSupport'
        },
        'java.io': {
            'Closeable', 'Serializable', 'BufferedInputStream', 'BufferedOutputStream', 'BufferedReader',
            'BufferedWriter', 'ByteArrayInputStream', 'ByteArrayOutputStream', 'CharArrayReader', 'CharArrayWriter',
            'Console', 'File', 'FileInputStream', 'FileOutputStream', 'FileReader', 'FileWriter', 'InputStream',
            'InputStreamReader', 'OutputStream', 'OutputStreamWriter', 'PrintStream', 'PrintWriter', 'Reader',
            'Writer', 'StringReader', 'StringWriter', 'FileNotFoundException', 'IOException', 'IOError'
        },
        'java.nio.file': {
            'Path', 'Files', 'Paths', 'StandardCopyOption', 'StandardOpenOption',
        },
        'java.math': {
            'BigDecimal', 'BigInteger', 'MathContext', 'RoundingMode'
        }, 
        'java.nio.charset': {
            'StandardCharsets'
        },
        'java.util.concurrent': {
            'Callable', 'Executors', 'TimeUnit'
        },
        'java.util.function': '*',
        'java.util.regex': {
            'Pattern'
        }
    }

    static_imports = {
        'java.lang': {
            'Boolean': {'parseBoolean'},
            'Byte': {'parseByte'},
            'Double': {'parseDouble'},
            'Float': {'parseFloat'},
            'Integer': {'parseInt', 'parseUnsignedInt'},
            'Long': {'parseLong', 'parseUnsignedLong'},
            'Short': {'parseShort'},
            'String': {'format', 'join'},
        }
    }

    def __init__(self, tokens, filename='<unknown source>'):
        super().__init__(tokens, filename)
        self.print_statements = True
        self.collections_literals = True
        self.class_creator_expressions = True
        self.argument_trailing_commas = True
        self.other_trailing_commas = False
        self.argument_annotations_syntax = True
        self.types_auto_imports = True
        self.statics_auto_imports = True
        self.multiple_import_sections_syntax = True
        self.optional_literals = True

    #endregion init

    def enable_feature(self, feature: str, enabled: bool=True):
        enabled = bool(enabled)
        if feature == '*':
            for feature in type(self).supported_features:
                setattr(self, type(self).feature_name_to_attr(feature), enabled)
        elif feature in type(self).supported_features:
            setattr(self, type(self).feature_name_to_attr(feature), enabled)
        elif feature.endswith('.*'):
            prefix = feature[0:-2]
            found = False
            for feature in type(self).supported_features:
                if feature.startswith(prefix):
                    setattr(self, type(self).feature_name_to_attr(feature), enabled)
                    found = True
            if not found:
                raise ValueError(f"unsupported category '{prefix}'")
        else:
            raise ValueError(f"unsupported feature '{feature}'")

    @classmethod
    def feature_name_to_attr(cls, name: str) -> str:
        strs = name.split('.')
        return '_'.join(reversed(strs))

    #region Declarations
    def parse_import_section(self) -> List[tree.Import]:
        imports = []
        while True:
            if self.would_accept('import'):
                imports.extend(self.parse_import_declarations())
            elif self.would_accept('from'):
                imports.extend(self.parse_from_import_declarations())
            elif self.would_accept('unimport'):
                self.parse_unimport(imports)
            elif not self.accept(';'):
                break

        auto_import_index = 0

        if self.types_auto_imports:
            for package, imported_types in type(self).auto_imports.items():
                if imported_types == '*':
                    found = False
                    for _import in imports:
                        if not _import.static and _import.imported_package == package and _import.wildcard:
                            found = True
                            break
                    if not found:
                        imports.insert(0, tree.Import(name=tree.Name(package), wildcard=True))
                        auto_import_index += 1
                else:
                    for imported_type in imported_types:
                        found = 0
                        for _import in imports:
                            if not _import.static:
                                if _import.imported_package == package and _import.wildcard:
                                    found = 2
                                    break
                                elif _import.imported_type == imported_type:
                                    found = 1
                                    break
                        if found:
                            if found == 2:
                                break # wildcard imported package, skip this one
                        else:
                            imports.insert(0, tree.Import(name=tree.Name(package + '.' + imported_type)))
                            auto_import_index += 1

        if self.statics_auto_imports:
            for package, types in type(self).static_imports.items():
                for typename, members in types.items():
                    if members == '*':
                        found = False
                        for _import in imports:
                            if _import.static and _import.wildcard and _import.imported_package == package and _import.imported_type == typename:
                                found = True
                                break
                        if not found:
                            imports.insert(0, tree.Import(name=tree.Name(package + '.' + typename), static=True, wildcard=True))
                            auto_import_index += 1
                    else:
                        for member in members:
                            found = 0
                            for _import in imports:
                                if _import.static:
                                    if _import.imported_package == package and _import.imported_type == typename and _import.wildcard:
                                        found = 2
                                        break
                                    elif _import.imported_name == member:
                                        found = 1
                                        break
                            if found:
                                if found == 2:
                                    break # wildcard imported member, skip this one
                            else:
                                imports.insert(0, tree.Import(name=tree.Name(package + '.' + typename + '.' + member), static=True))                
                                auto_import_index += 1

        if auto_import_index:
            from functools import cmp_to_key
            def import_cmp(i1, i2):
                if i1.static and not i2.static:
                    return -1
                if not i1.static and i2.static:
                    return 1
                if i1.wildcard and not i2.wildcard:
                    return -1
                if not i1.wildcard and i2.wildcard:
                    return 1
                i1 = str(i1.name)
                i2 = str(i2.name)
                if i1 == i2:
                    return 0
                elif i1 < i2:
                    return -1
                else:
                    return 1
                
            imports[0:auto_import_index] = sorted(imports[0:auto_import_index], key=cmp_to_key(import_cmp))

        return imports

    def parse_import_declarations(self) -> List[tree.Import]:
        imports = []
        self.require('import')
        static = bool(self.accept('static'))
        while True:
            if not static and self.accept('java', '++'):
                if self.accept('.', '*'):
                    feature = '*'
                else:
                    self.require('.')
                    feature = self.parse_ident()
                    while self.accept('.'):
                        if self.accept('*'):
                            feature += '.*'
                            break
                        else:
                            feature += '.' + self.parse_ident()
                self.enable_feature(feature)
            else:
                name, wildcard = self.parse_import_name()
                imports.append(tree.Import(name=name, static=static, wildcard=wildcard))
            if not self.accept(','):
                break
            if self.other_trailing_commas and self.would_accept(';'):
                break
        self.require(';')
        return imports

    def parse_unimport(self, imports: List[tree.Import]):
        self.require('unimport')
        self.require('java', '++')
        while True:
            if self.accept('.', '*'):
                feature = '*'
            else:
                self.require('.')
                feature = self.parse_ident()
                while self.accept('.'):
                    if self.accept('*'):
                        feature += '.*'
                        break
                    else:
                        feature += '.' + self.parse_ident()
            self.enable_feature(feature, False)
            if not self.accept(','):
                break
            if self.other_trailing_commas and self.would_accept(';'):
                break
        return []

    def parse_from_import_declarations(self) -> List[tree.Import]:
        self.require('from')
        imports = []

        if self.would_accept('java', '++'): # 'from java++ import ...' / 'from java++ unimport ...' statement, allows modifying syntax
            self.next() # skips past the 'java' token
            self.next() # skips past the '++' token

            if self.accept('import'):
                enable_feature = True
            else:
                self.require('unimport')
                enable_feature = False

            if self.accept('*'):
                self.enable_feature('*', enable_feature)

            else:
                while True:
                    start_pos = self.position()
                    feature = self.parse_ident()
                    while self.accept('.'):
                        if self.accept('*'):
                            feature += '*'
                            break
                        else:
                            feature += '.' + self.parse_ident()
                    try:
                        self.enable_feature(feature, enable_feature)
                    except ValueError as e:
                        raise JavaSyntaxError(str(e), at=start_pos)
                    if not self.accept(','):
                        break
                    if self.other_trailing_commas and self.would_accept(';'):
                        break
        else:
            base = self.parse_qual_name()
            self.require('import')
            static = bool(self.accept('static'))

            name, wildcard = self.parse_from_import_name(base)
            imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

            while self.accept(','):
                if self.other_trailing_commas and self.would_accept(';'):
                    break
                name, wildcard = self.parse_from_import_name(base)
                imports.append(tree.Import(name=name, static=static, wildcard=wildcard))

        self.require(';')

        return imports

    def parse_from_import_name(self, base_name):
        if self.accept('*'):
            return base_name, True
        else:
            base_name += self.parse_qual_name()
            wildcard = bool(self.accept('.', '*'))
            return base_name, wildcard
    
    def parse_type_declarations(self, doc=None, modifiers=None, annotations=None, imports: List[tree.Import]=None) -> List[tree.TypeDeclaration]:
        types = [self.parse_type_declaration(doc, modifiers, annotations)]
        while self.token.type != ENDMARKER:
            if not self.accept(';'):
                if self.multiple_import_sections_syntax and imports is not None and self.would_accept(('from', 'import')):
                    imports.extend(self.parse_import_section())
                else:
                    types.append(self.parse_type_declaration())
        return types

    def parse_parameters(self, allow_this=True):
        self.require('(')
        if self.would_accept(')'):
            params = []
        else:
            params = [self.parse_parameter_opt_this() if allow_this else self.parse_parameter()]
            while self.accept(','):
                if self.argument_trailing_commas and self.would_accept(')'):
                    break
                params.append(self.parse_parameter())
        self.require(')')
        return params

    #endregion Declarations

    #region Statements
    def parse_statement(self):
        if self.print_statements:
            if self.accept('println'):
                if self.accept(';'):
                    return self.make_print_statement('println')
                elements = [self.parse_arg()]
                if self.would_accept(','):
                    while self.accept(','):
                        if self.other_trailing_commas and self.would_accept(';'):
                            break
                        elements.append(self.parse_arg())
                elif not self.would_accept(';'):
                    while not self.would_accept((';', ENDMARKER)):
                        elements.append(self.parse_arg())
                self.require(';')
                if len(elements) == 1:
                    return self.make_print_statement('println', elements[0])
                stmts = []
                for i, arg in enumerate(elements):
                    if i:
                        stmts.append(self.make_print_statement('print', tree.Literal("' '")))
                    stmts.append(self.make_print_statement('print' if i+1 < len(elements) else 'println', arg))
                return tree.Block(stmts)
            elif self.accept('print'):
                if self.accept(';'):
                    return tree.EmptyStatement()
                elements = [self.parse_arg()]
                if self.would_accept(','):
                    while self.accept(','):
                        if self.other_trailing_commas and self.would_accept(';'):
                            break
                        elements.append(self.parse_arg())
                elif not self.would_accept(';'):
                    while not self.would_accept((';', ENDMARKER)):
                        elements.append(self.parse_arg())
                self.require(';')
                if len(elements) == 1:
                    return self.make_print_statement('print', elements[0])
                stmts = []
                for i, arg in enumerate(elements):
                    if i:
                        stmts.append(self.make_print_statement('print', tree.Literal("' '")))
                    stmts.append(self.make_print_statement('print', arg))
                return tree.Block(stmts)
            elif self.accept('printf'):
                args = [self.parse_arg()]
                if self.would_accept(','):
                    while self.accept(','):
                        if self.other_trailing_commas and self.would_accept(';'):
                            break
                        args.append(self.parse_arg())
                elif not self.would_accept(';'):
                    while not self.would_accept((';', ENDMARKER)):
                        args.append(self.parse_arg())
                self.require(';')
                return tree.ExpressionStatement(tree.FunctionCall(name=tree.Name('printf'), args=args, object=self.make_member_access_from_dotted_name('java.lang.System.out')))
            elif self.accept('printfln'):
                args = [tree.BinaryExpression(lhs=self.parse_arg(), op='+', rhs=tree.Literal('"%n"'))]
                if self.would_accept(','):
                    while self.accept(','):
                        if self.other_trailing_commas and self.would_accept(';'):
                            break
                        args.append(self.parse_arg())
                elif not self.would_accept(';'):
                    while not self.would_accept((';', ENDMARKER)):
                        args.append(self.parse_arg())
                self.require(';')
                return tree.ExpressionStatement(tree.FunctionCall(name=tree.Name('printf'), args=args, object=self.make_member_access_from_dotted_name('java.lang.System.out')))

        return super().parse_statement()

    def make_print_statement(self, name: str, arg: tree.Expression=None):
        return tree.ExpressionStatement(tree.FunctionCall(name=tree.Name(name), args=[] if arg is None else [arg], object=self.make_member_access_from_dotted_name('java.lang.System.out')))

    def parse_variable_decl(self, doc=None, modifiers=None, annotations=None, end=';'):
        if doc is None:
            doc = self.doc
        if modifiers is None and annotations is None:
            modifiers, annotations = self.parse_mods_and_annotations(newlines=(end == NEWLINE))
        if self.accept('var'):
            typ = tree.GenericType(name=tree.Name('var'))
        else:
            typ = self.parse_type()
        declarators = [self.parse_declarator(array=isinstance(typ, tree.ArrayType))]
        while self.accept(','):
            if self.other_trailing_commas and self.would_accept(end):
                break
            declarators.append(self.parse_declarator(array=isinstance(typ, tree.ArrayType)))
        self.require(end)
        return tree.VariableDeclaration(type=typ, declarators=declarators, doc=doc, modifiers=modifiers, annotations=annotations)

    def parse_expr_list(self, end):
        update = [self.parse_expr()]
        while self.accept(','):
            if self.other_trailing_commas and self.would_accept(end):
                break
            update.append(self.parse_expr())
        return update

    def parse_case_labels(self):
        labels = [self.parse_case_label()]
        while self.accept(','):
            if self.other_trailing_commas and self.would_accept((':', '->')):
                break
            labels.append(self.parse_case_label())
        return labels

    #endregion Statements

    #region Type Stuff
    def parse_type_parameters(self):
        self.require('<')
        params = [self.parse_type_parameter()]
        while self.accept(','):
            if self.other_trailing_commas and self.would_accept('>'):
                break
            params.append(self.parse_type_parameter())
        self.require('>')
        return params

    def parse_annotation(self):
        self.require('@')
        typ = tree.GenericType(name=self.parse_qual_name())

        if self.accept('('):
            if self.would_accept(NAME, '='):
                args = [self.parse_annotation_arg()]
                while self.accept(','):
                    if self.argument_trailing_commas and self.would_accept(')'):
                        break
                    args.append(self.parse_annotation_arg())
            elif not self.would_accept(')'):
                args = self.parse_annotation_value()
            self.require(')')
        else:
            args = None

        return tree.Annotation(type=typ, args=args)

    def parse_type_args(self):
        self.require('<')
        args = []
        if not self.would_accept('>'):
            args.append(self.parse_type_arg())
            while self.accept(','):
                if self.argument_trailing_commas and self.would_accept('>'):
                    break
                args.append(self.parse_type_arg())
        self.require('>')
        return args

    def parse_generic_type_list(self):
        types = [self.parse_generic_type()]
        while self.accept(','):
            if self.other_trailing_commas and not self.would_accept(NAME):
                break
            types.append(self.parse_generic_type())
        return types

    def primitive_to_wrapper(self, typ: tree.Type) -> tree.Type:
        if isinstance(typ, tree.PrimitiveType):
            if typ.name == 'boolean':
                return tree.GenericType(tree.Name('java.lang.Boolean'))
            elif typ.name == 'byte':
                return tree.GenericType(tree.Name('java.lang.Byte'))
            elif typ.name == 'short':
                return tree.GenericType(tree.Name('java.lang.Short'))
            elif typ.name == 'char':
                return tree.GenericType(tree.Name('java.lang.Character'))
            elif typ.name == 'int':
                return tree.GenericType(tree.Name('java.lang.Integer'))
            elif typ.name == 'long':
                return tree.GenericType(tree.Name('java.lang.Long'))
            elif typ.name == 'float':
                return tree.GenericType(tree.Name('java.lang.Float'))
            else:
                assert typ.name == 'double'
                return tree.GenericType(tree.Name('java.lang.Double'))
        elif isinstance(typ, tree.VoidType):
            return tree.GenericType(tree.Name('java.lang.Void'))
        else:
            return typ

    #endregion Type Stuff

    #region Expressions
    def parse_conditional(self):
        if self.would_accept(NAME, '->') or self.would_accept('('):
            try:
                with self.tokens:
                    result = self.parse_lambda()
            except JavaSyntaxError:
                result = self.parse_logic_or_expr()
        else:
            result = self.parse_logic_or_expr()            
        if self.accept('?'):
            if self.optional_literals and self.would_accept(('<', ')', ']', '}', ',', ';', ENDMARKER)):
                return self.parse_optional_literal_rest(result)
            truepart = self.parse_assignment()
            self.require(':')
            falsepart = self.parse_conditional()
            result = tree.ConditionalExpression(condition=result, truepart=truepart, falsepart=falsepart)
        return result

    def parse_optional_literal_rest(self, value):
        typename = 'Optional'
        name = 'ofNullable'
        if isinstance(value, tree.CastExpression) and isinstance(value.type, tree.PrimitiveType):
            if value.name == 'int':
                typename = 'OptionalInt'
                name = 'of'
            elif value.name == 'double':
                typename = 'OptionalDouble'
                name = 'of'
            elif value.name == 'long':
                typename = 'OptionalLong'
                name = 'of'
        if self.accept('<'):
            annotations = self.parse_annotations()
            if self.accept('int', '>'):
                typename = 'OptionalInt'
                name = 'of'
            elif self.accept('double', '>'):
                typename = 'OptionalDouble'
                name = 'of'
            elif self.accept('long', '>'):
                typename = 'OptionalLong'
                name = 'of'
            else:
                if self.would_accept('?'):
                    typ = self.parse_type_arg(annotations)
                else:
                    typ = self.parse_type(annotations)
                self.require('>')
                return tree.FunctionCall(args=[value], name=tree.Name(name), object=self.make_member_access_from_dotted_name('java.util.Optional'), typeargs=[self.primitive_to_wrapper(typ)])
        return tree.FunctionCall(args=[value], name=tree.Name(name), object=self.make_member_access_from_dotted_name('java.util.' + typename))
    
    def parse_cast(self):
        if self.would_accept('('):
            try:
                with self.tokens:
                    self.next() # skip past the '(' token
                    typ = self.parse_cast_type()
                    self.require(')')
                    if self.would_accept('(') or self.would_accept(NAME, '->'):
                        try:
                            with self.tokens:
                                expr = self.parse_lambda()
                        except JavaSyntaxError:
                            expr = self.parse_postfix()
                            if self.would_accept(('++', '--')):
                                op = self.token.string
                                self.next()
                                expr = tree.IncrementExpression(op=op, prefix=False, expr=expr)  
                    else:
                        # if self.optional_literals and self.would_accept('?', (')', ']', '}', ',', ';', ENDMARKER)):
                        #     self.next() # skips past the '?' token
                        #     if isinstance(typ, tree.PrimitiveType):
                        #         if typ.name == 'int':
                        #             return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalInt'))
                        #         elif typ.name == 'double':
                        #             return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalDouble'))
                        #         elif typ.name == 'long':
                        #             return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalLong'))
                                
                        #     return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.Optional'), typeargs=[self.primitive_to_wrapper(typ)])
                        expr = self.parse_cast()
                    return tree.CastExpression(type=typ, expr=expr)
            except JavaSyntaxError:
                pass
        result = self.parse_postfix()
        if self.would_accept(('++', '--')):
            op = self.token.string
            self.next()
            result = tree.IncrementExpression(op=op, prefix=False, expr=result)
        return result

    def parse_postfix(self):
        result = self.parse_primary()
        while True:
            if self.would_accept('.'):
                result = self.parse_dot_expr(result)

            elif self.accept('['):
                index = self.parse_expr()
                self.require(']')
                result = tree.IndexExpression(indexed=result, index=index)

            elif self.would_accept('::'):
                result = self.parse_ref_expr(result)

            elif self.optional_literals and self.accept('!'):
                result = tree.FunctionCall(name=tree.Name('orElseThrow'), object=result)

            else:
                return result

    def parse_args(self):
        self.require('(')
        args = []
        if not self.would_accept(')'):
            args.append(self.parse_arg())
            while self.accept(','):
                if self.argument_trailing_commas and self.would_accept(')'):
                    break
                args.append(self.parse_arg())
        self.require(')')

        return args

    def parse_arg(self):
        if self.argument_annotations_syntax:
            self.accept(NAME, ':')
        return super().parse_arg()

    def make_member_access_from_dotted_name(self, qualname: str) -> tree.MemberAccess:
        result = None
        for name in qualname.split('.'):
            result = tree.MemberAccess(name=tree.Name(name), object=result)
        return result

    def parse_primary(self):
        if self.would_accept(REGEX):
            import re
            string = self.token.string[1:-1]
            self.next()
            regex = '"'
            escape = False
            for c in string:
                if escape:
                    if c == '"':
                        regex += '\\'
                    elif c != '/':
                        regex += R'\\'
                    regex += c
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"':
                    regex += R'\"'
                else:
                    regex += c
            regex += '"'
            regex = re.sub(r"((?:\\\\)*)\\x([a-fA-F0-9]{2})", R'\1\u00\2', regex)
            literal = tree.Literal(regex)
            return tree.FunctionCall(name=tree.Name('compile'), object=self.make_member_access_from_dotted_name('java.util.regex.Pattern'), args=[literal])

        elif self.would_accept(STRING) and ('b' in self.token.string[0:2] or 'B' in self.token.string[0:2]):
            import ast
            elems = [tree.Literal(str(i)) for i in ast.literal_eval(self.token.string)]
            self.next()
            return tree.ArrayCreator(type=tree.PrimitiveType('byte'), dimensions=[tree.DimensionExpression()], initializer=tree.ArrayInitializer(elems))

        elif self.optional_literals and self.accept('?'):
            if self.accept('<'):
                annotations = self.parse_annotations()
                if self.accept('int', '>'):
                    return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalInt'))
                elif self.accept('double', '>'):
                    return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalDouble'))
                elif self.accept('long', '>'):
                    return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.OptionalLong'))
                else:
                    if self.would_accept('?'):
                        typ = self.parse_type_arg(annotations)
                    else:
                        typ = self.parse_type(annotations)
                    self.require('>')
                    return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.Optional'), typeargs=[self.primitive_to_wrapper(typ)])
            else:
                return tree.FunctionCall(name=tree.Name('empty'), object=self.make_member_access_from_dotted_name('java.util.Optional'), args=[])

        else:
            return super().parse_primary()

    def parse_list_literal(self):
        if not self.collections_literals:
            return super().parse_list_literal()
        self.require('[')
        elements = []
        if not self.would_accept(']'):
            if not self.accept(','):
                elements.append(self.parse_expr())
                while self.accept(','):
                    if self.would_accept(']'):
                        break
                    elements.append(self.parse_expr())
        self.require(']')

        return self.make_list_literal(elements)

    def make_list_literal(self, elements: List[tree.Expression]):
        return tree.FunctionCall(args=elements,
                                 name=tree.Name('of'), 
                                 object=self.make_member_access_from_dotted_name('java.util.List'))

    def parse_map_literal(self):
        if not self.collections_literals:
            return super().parse_map_literal()
        self.require('{')
        entries = []
        if not self.would_accept('}'):
            if not self.accept(','):
                key = self.parse_expr()
                if not self.accept(':'):
                    return self.parse_set_literal_rest(key)
                entries.append((key, self.parse_expr()))
                while self.accept(','):
                    if self.would_accept(']'):
                        break
                    entries.append(self.parse_map_entry())
        self.require('}')

        return self.make_map_literal(entries)

    def make_map_literal(self, entries: List[Tuple[tree.Expression, tree.Expression]]):
        if len(entries) <= 10:
            args = []
            for key, value in entries:
                args.append(key)
                args.append(value)
            return tree.FunctionCall(args=args,
                                     name=tree.Name('of'), 
                                     object=self.make_member_access_from_dotted_name('java.util.Map'))
        else:
            for i, (key, value) in enumerate(entries):
                entries[i] = tree.FunctionCall(args=[key, value],
                                               name=tree.Name('entry'), 
                                               object=self.make_member_access_from_dotted_name('java.util.Map'))
            return tree.FunctionCall(args=entries,
                                     name=tree.Name('ofEntries'), 
                                     object=self.make_member_access_from_dotted_name('java.util.Map'))

    def parse_map_entry(self):
        key = self.parse_expr()
        self.require(':')
        value = self.parse_expr()
        return key, value

    def parse_set_literal_rest(self, elem):
        elements = [elem]
        while self.accept(','):
            if self.would_accept('}'):
                break
            elements.append(self.parse_expr())
        self.require('}')

        return self.make_set_literal(elements)

    def make_set_literal(self, elements: List[tree.Expression]):
        return tree.FunctionCall(args=elements,
                                 name=tree.Name('of'),
                                 object=self.make_member_access_from_dotted_name('java.util.Set'))

    def parse_class_creator_rest(self, type, typeargs):
        if not self.class_creator_expressions:
            return super().parse_class_creator_rest(type, typeargs)
            
        members = None

        if self.accept('{'):
            expr = self.parse_expr()
            if self.accept(':'):
                entries = [(expr, self.parse_expr())]
                while self.accept(','):
                    if self.would_accept('}'):
                        break
                    entries.append(self.parse_map_entry())
                self.require('}')
                args = [self.make_map_literal(entries)]
            else:
                elements = [expr]
                while self.accept(','):
                    if self.would_accept('}'):
                        break
                    elements.append(self.parse_expr())
                self.require('}')
                args = [self.make_list_literal(elements)]

        elif self.would_accept('('):
            args = self.parse_args()
        
            if self.would_accept('{'):
                members = self.parse_class_body(self.parse_class_member)

        else:
            args = []
        
        if typeargs is None:
            typeargs = []
        return tree.ClassCreator(type=type, args=args, typeargs=typeargs, members=members)

    #endregion Expressions

def parse_file(file, parser: Type[JavaParser]=JavaPlusPlusParser) -> tree.CompilationUnit:
    return java_parse_file(file, parser)

def parse_str(s: Union[str, bytes, bytearray], encoding='utf-8', parser: Type[JavaParser]=JavaPlusPlusParser) -> tree.CompilationUnit:
    return java_parse_str(s, encoding=encoding, parser=parser)
