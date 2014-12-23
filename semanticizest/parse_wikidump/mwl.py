#!/usr/bin/env python

import sys
from itertools import islice

from mwlib.refine.compat import parse_txt as parse
from mwlib.parser.nodes import ArticleLink, Text, Section
from mwlib.templ.misc import expandstr


class UnspecifiedNode(object):
    pass


def ignore(node):
    return
    yield

def plaintext(node):
    text = node.caption
    yield (text,)

def articlelink(node):
    try:
        text_node = node.children[0]
        text = text_node.caption
    except IndexError:
        text = node.target

    yield (node.target, text)

def articlelink_text(node):
    try:
        text_node = node.children[0]
        text = text_node.caption
    except IndexError:
        text = node.target

    yield (text, )

def heading_text(node):
    for i in dispatch_text(node.children[0]):
        yield i

    yield ('\n',)

    for i in dispatch_text(node.children[1:]):
        yield i


def dispatch(node, table):
    # print "   ***", type(node)
    for child in node:
        child_type = type(child)
        fn = table[child_type] if child_type in table else table[UnspecifiedNode]

        for i in fn(child):
            yield i

def dispatch_links(node):
    return dispatch(node, _dispatch_links)

def dispatch_text(node):
    return dispatch(node, _dispatch_text)


_dispatch_text = { Text: plaintext,
                   Section: heading_text,
                   ArticleLink: articlelink_text,
                   
                   UnspecifiedNode: dispatch_text
                  }

_dispatch_links = { ArticleLink: articlelink,
                    
                    UnspecifiedNode: dispatch_links
                  }


if __name__ == '__main__':
    fname = sys.argv[1]
    try:
        option = sys.argv[2]
    except IndexError:
        option = 'links'

    options = {'links': (dispatch_links, "\n"),
               'text': (dispatch_text, "")}
               
    dispatcher, sep = options[option]


    with open(fname) as f:
        data = f.read().decode("utf-8")

    text = expandstr(data)
    res = compat_parse(text)

    output = sep.join("_".join(e for e in i) for i in dispatcher(res))
    print output.encode("utf-8")
    # for i in option(res):
    #     print type(i), i[:25]
