# -*- coding: utf-8 -*-

################################################################
# xmldirector.crex
# (C) 2015,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################


import re


class RuleRewriter(object):

    def __init__(self, rules):
        self.rules = [Rule(*rule) for rule in rules]


    def rewrite(self, path):

        for rule in self.rules:
            mo = rule.src_compiled.search(path)
            if not mo:
                continue
            return re.sub(rule.src_compiled, rule.dest_compiled, path)
        return path


class Rule(object):

    def __init__(self, src, dest):
        self.src = src
        self.dest = dest
        self.src_compiled = self.compile_src(src)
        self.dest_compiled = self.compile_dest(dest)

    def compile_src(self, pat):
        return re.compile(pat)

    def compile_dest(self, pat):

        def replacer(mo):
            pattern = mo.group(0)
            group_no = pattern.lstrip('$')
            return '\\{}'.format(group_no)
            
        pattern = re.compile(r'(\$\d*)', re.UNICODE)
        return pattern.sub(replacer, pat)


if __name__ == '__main__':

    rules = [
        ('src/word/(.*).docx', 'out/$1.docx'),
        ('src/(.*)', '$1'),
        ('xxx/(.*)', 'hell/world/$1'),
    ]

    paths = [
        'src/word/index.docx',
        'src/word/sample.docx',
        'src/hello/world/x.png',
        'xxx/nix.png',
        'nix'

    ]

    rewriter = RuleRewriter(rules)
    for path in paths:
        print '-'*80
        print path
        print rewriter.rewrite(path)
