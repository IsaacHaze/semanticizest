from collections import defaultdict
from itertools import chain

from mwparserfromhell.parser import Parser
from mwparserfromhell.wikicode import Wikicode
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.nodes.text import Text
from mwparserfromhell.nodes.heading import Heading
from mwparserfromhell.nodes.tag import Tag


def ignore(node):
    return
    yield

def tag(node):
    # NB: mwparserfromhell handles lists rather strangely, see:
    # https://github.com/earwig/mwparserfromhell/issues/46
    keeps = set("b i li table tr td th".split())
    tag_name = unicode(node.tag)

    if tag_name in keeps:
        if node.contents is not None:
            for i in dispatch_text(node.contents):
                yield i
    else:
        print "((skip tag: %s))" % tag_name
        yield ("skip",)
    
def text(node):
    yield (node.value,)

def wikilink(node):
    text = node.text if node.text else node.title
    yield (text, node.title)

def wikilink_text(node):
    text = node.text if node.text else node.title
    yield (text,)
    
def dispatch(node, table):
    # print "     ***", type(node)
    try:
        children = node.nodes
    except AttributeError:
        return
    
    for child in children:
        child_type = type(child)
        # print "       *", child_type
        for i in table[child_type](child):
            yield i


def heading(node):
    for i in dispatch_text(node.title):
        yield i
    # ensure that the headings aren't glued to the following paragraph
    yield ("\n",)


def dispatch_links(node):
    return dispatch(node, _dispatch_links)

def dispatch_text(node):
    return dispatch(node, _dispatch_text)

    
_dispatch_links = {Wikicode: dispatch_links,
                   Template: ignore,
                   Text: ignore,
                   Heading: dispatch_links,
                   Wikilink: wikilink,
                   Tag: ignore,
                  }

_dispatch_text = {Wikicode: dispatch_text,
                  Template: ignore,
                  Text: text,
                  Heading: heading,
                  Wikilink: wikilink_text,
                  Tag: tag
                 }



def mwp_parse(markup):
    """Parses Mediawiki markup and returns a `Wikicode` object."""
    # TODO: maintain single parser? a pool of parsers?
    return Parser().parse(markup)


"""Yield all (non-template) plain text in this document."""
mwp_text = dispatch_text

"""Yield all (non-template) links in this document."""
mwp_links = dispatch_links


if __name__ == '__main__':
    import sys
    fname = sys.argv[1]
    with open(fname) as f:
        text = f.read().decode('utf-8')
    
    tree = mwp_parse(text)
    
    # for i in mwp_links(tree):
    #     output = " --> ".join(unicode(e) for e in i)
    #     print "got:", output.encode('utf-8')

    for i in mwp_text(tree):
        output = "_".join(unicode(e) for e in i)
        sys.stdout.write(output.encode('utf-8'))
    print "---"
