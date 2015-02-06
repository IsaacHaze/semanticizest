#!/usr/bin/env python
"""mwlib wrapper to parse MediaWiki syntax (Wikipedia articles)

Usage:
    >>> from semanticizest.parse_wikidump.mwl import (parse, dispatch_text,
    ...                                               dispatch_links)
    >>> tree = parse("[[Wikipedia|wiki]] markup")
    >>> text, links = dispatch_text(tree), dispatch_links(tree)
"""

from mwlib.parser.nodes import (ArticleLink, ImageLink, Text, Section, Table,
                                Ref)
from mwlib.uparser import parseString
from mwlib.templ.misc import DictDB
from mwlib.dummydb import DummyDB
from mwlib.siteinfo import get_siteinfo


class UnspecifiedNode(object):
    """Placeholder for the dispatcher table."""
    pass


class MyDB(DictDB, DummyDB):
    """Kurwa, DictDB has no getURL() and DummyDB no get_site_info"""

    def __init__(self, siteinfo=None):
        super(MyDB, self).__init__()

        self.siteinfo = siteinfo


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
    # print "   ***", type(node), node.asText()[:25].encode('utf-8')
    for child in node:
        child_type = type(child)
        # print "     *", child_type, child.asText()[:25].encode('utf-8')
        fn = (table[child_type] if child_type in table else
              table[UnspecifiedNode])

        for i in fn(child):
            yield i


def dispatch_links(node):
    return dispatch(node, _dispatch_links)


def dispatch_text(node):
    return dispatch(node, _dispatch_text)


_dispatch_text = {Text: plaintext,
                  Section: heading_text,
                  ArticleLink: articlelink_text,
                  ImageLink: ignore,
                  Table: ignore,
                  Ref: ignore,

                  UnspecifiedNode: dispatch_text
                  }

_dispatch_links = {ArticleLink: articlelink,
                   Table: ignore,
                   Ref: ignore,
                   ImageLink: ignore,

                   UnspecifiedNode: dispatch_links
                   }


def parse(text, db=None, siteinfo=None):
    """Parse MediaWiki text and return the parse tree."""
    if siteinfo is None:
        siteinfo = get_siteinfo("nl")
    if db is None:
        db = MyDB(siteinfo=siteinfo)

    return parseString(raw=text, title='', wikidb=db)


if __name__ == '__main__':
    import sys

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

    si = get_siteinfo("nl")
    # print si
    res = parse(data, siteinfo=si)
    output = sep.join("_".join(e for e in i) for i in dispatcher(res))
    print output.encode("utf-8")
