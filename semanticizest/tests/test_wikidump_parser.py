# -*- coding: utf-8 -*-

from cytoolz import compose

from os.path import abspath, dirname, join
import sqlite3
import tempfile

from nose.tools import (assert_equal, assert_greater, assert_in, assert_not_in)

from semanticizest.parse_wikidump.__main__ import main as parse_wikidump_main
from semanticizest.parse_wikidump import (clean_text, extract_links,
                                          page_statistics, parse_dump,
                                          remove_links)
from semanticizest._semanticizer import createtables_path


# Straight from nlwiki: a {| {| |} table (works in MediaWiki!)
unclosed_table = '''
Nikkel wordt verhandeld op beurzen zoals de London Metal Exchange.
Dagelijks komen vraag en aanbod bij elkaar en komt een prijs tot stand.
In de onderstaande tabel de gemiddelde prijs van nikkel per jaar.
{| {| class=&quot;wikitable&quot; style=&quot;text-align: center&quot;
!Omschrijving
!2005
!2006
!2007
!2008
!2009
!2010
!2011
|-
|Nikkelprijs ($/ton)|| 14.733|| 24.267|| 37.181 || 21.027 || 14.700 ||21.809 || 22.831
|}
This is not in the original.'''


def test_clean_text():
    out = clean_text(unclosed_table).splitlines()
    expected = (unclosed_table.splitlines()[:4]
                + ['']
                + unclosed_table.splitlines()[-1:])
    assert_equal(out, expected)


def test_extract_links():
    first_link = compose(tuple, next, iter, extract_links)

    assert_equal(first_link("[[foo|bar]]"), ("Foo", "bar"))
    assert_equal(first_link("[[foo]]"), ("Foo", "foo"))
    assert_equal(first_link("[[File:picture!]] [[foo]]"), ("Foo", "foo"))
    assert_equal(first_link("[[foo]]bar."), ("Foo", "foobar"))
    assert_equal(first_link("[[baz|foobar]];"), ("Baz", "foobar"))
    assert_equal(first_link("[[baz#quux]]"), ("Baz", "baz#quux"))
    assert_equal(first_link("[[baz#quux|bla]]"), ("Baz", "bla"))
    assert_equal(first_link("[[FOO_BAR|foo bar]]"), ("FOO BAR", "foo bar"))

    # Links like these commonly occur in nlwiki (and presumably dewiki and
    # other compounding languages):
    assert_equal(first_link("foo[[baz|bar]]"), ("Baz", "foobar"))

    # MediaWiki only considers alphabetic characters outside [[]] part of the
    # anchor.
    assert_equal(first_link("foo-[[bar]]"), ("Bar", "bar"))
    assert_equal(first_link("[[bar]]/baz"), ("Bar", "bar"))
    # XXX The following are broken. They do occur in the wild, e.g.,
    # -18[[Celsius|°C]] and 700[[Megabyte|MB]]-cd (found in nlwiki dump).
    #assert_equal(first_link("[[bar]]0"), ("Bar", "bar"))
    #assert_equal(first_link("[[bar]]_"), ("Bar", "bar"))

    # We're not interested in section links
    assert_equal(first_link("[[#Some section|elsewhere]] [[other_article]]"),
                 ("Other article", "other_article"))

    # This construct appears in enwiki for chemical formulae etc., but also in
    # nlwiki (and dewiki?) for more general compound nouns. The current
    # handling may not be exactly what we want; any fix should update the test
    # accordingly.
    assert_equal(list(extract_links("[[Lithium|Li]][[Fluorine|F]]")),
                 [("Lithium", "Li"), ("Fluorine", "F")])
    assert_equal(list(extract_links("[[tera-|tera]][[becquerel]]s")),
                 [("Tera-", "tera"), ("Becquerel", "becquerels")])


def test_page_statistics():
    page = """
        Wikisyntax is the [[syntax (to be parsed)|syntax]] used on
        [[Wikipedia]].{{citation needed|date=October 2014}}
        We have to parse it, and we use every [[hack]] in the
        [[text]][[book]] that we can find.

        And now, for something [[Wikipedia|completely]] [[hack|different]].

        Let's repeat the [[text]] to get more interesting [[statistic]]s.
        And the [[book]] too.
    """

    expected_links = {('Syntax (to be parsed)', 'syntax'): 1,
                      ('Wikipedia', 'Wikipedia'): 1,
                      ('Hack', 'hack'): 1,
                      ('Text', 'text'): 2,
                      ('Book', 'book'): 2,
                      ('Wikipedia', 'completely'): 1,
                      ('Hack', 'different'): 1,
                      ('Statistic', 'statistics'): 1}

    links, ngrams = page_statistics(page, N=2)

    assert_equal(dict(links), expected_links)

    assert_in('And now', ngrams)
    assert_not_in('Wikipedia We', ngrams)
    assert_not_in('find. And', ngrams)
    assert_not_in('find And', ngrams)


def test_page_statistics_template():
    text = u"""{{Infobox politieke partij België
| naam             = Groen
| afbeelding       = Groen_logo.png
| partijvoorzitter = [[Wouter Van Besien]]
| vice-partijvoorzitter = [[Elke Van den Brandt]]
| politiek secretaris =
| functienaam1     = [[Europees Parlement]]
| functie1         = [[Bart Staes]]
| functienaam2     = [[Senaat (België)|Senaat]]
| functie2         = [[Elisabeth Meuleman]]
| functienaam3     = [[Kamer van Volksvertegenwoordigers|Kamer]]
| functie3         = [[Kristof Calvo]] (fractie met [[Ecolo]])
| functienaam4     = [[Vlaams Parlement]]
| functie4         = [[Björn Rzoska]]
| functienaam5     = [[Brussels Hoofdstedelijk Parlement|Brussels Parlement]]
| functie5         = [[Annemie Maes]]
| zetelnaam1       = [[Europees Parlement]]
| zetels1          = 1
| zetelstotaal1    = 21
| verkiezingen1    = [[Europese Parlementsverkiezingen 2014|25 mei 2014]]
| zetelnaam2       = [[Senaat (België)|Senaat]]
| zetels2          = 2
| zetelstotaal2    = 71
| verkiezingen2    = [[Belgische federale verkiezingen 2010|13 juni 2010]]
| zetelnaam3       = [[Kamer van Volksvertegenwoordigers|Kamer]]
| zetels3          = 5
| zetelstotaal3    = 150
| verkiezingen3    = [[Belgische federale verkiezingen 2010|13 juni 2010]]
| zetelnaam4       = [[Vlaams Parlement]]
| zetels4          = 7
| zetelstotaal4    = 124
| verkiezingen4    = [[Vlaamse verkiezingen 2009|7 juni 2009]]
| zetelnaam5       = [[Brussels Hoofdstedelijk Parlement|Brussels Parlement]]
| zetels5          = 2
| zetelstotaal5    = 89
| verkiezingen5    = [[Brusselse gewestverkiezingen 2009|7 juni 2009]]
| zetelnaam6       = [[Gedeputeerde|Gedeputeerden in Vlaamse provincies]]
| zetels6          = 1
| zetelstotaal6    = 30
| verkiezingen6    = [[Belgische lokale verkiezingen 2012|14 oktober 2012]]
| zetelnaam7       = [[Burgemeester|Burgemeesters in Vlaamse gemeenten]]
| zetels7          = 2
| zetelstotaal7    = 308
| verkiezingen7    = [[Belgische lokale verkiezingen 2012|14 oktober 2012]]
| zetelnaam8       = [[Burgemeester|Burgemeesters in Brusselse gemeenten]]
| zetels8          =
| zetelstotaal8    = 19
| verkiezingen8    =
| exnaam           = 1979: Agalev&lt;br /&gt;2003: Groen!
| actief in        = {{BE-vlag|Vlaanderen}}&lt;br /&gt;{{BE-vlag|Brussel}}
| hoofdkantoor     = S. De Bruynestraat 78-82&lt;br /&gt;1070 [[Anderlecht]]&lt;br /&gt;{{BE}}
| richting         = [[Links (politiek)|Links]]
| ideologie        = [[Ecologisme]]&lt;br /&gt;[[Pacifisme]]&lt;br /&gt;[[Progressivisme]]
| jongeren         = [[Jong Groen]]
| senioren         = [[GroenPlus]]
| vrouwen          =
| euroorganisatie  = [[Europese Groene Partij|EGP]]
| eurofractie      = [[De Groenen/Europese Vrije Alliantie|Groenen/EVA]]
| internationaal   = [[Global Greens|GG]]
| krant            = [http://www.groen.be/lees-mee/ecozine_234.aspx Ecozine]
| website          = [http://www.groen.be www.groen.be]
}}
[[Bestand:Logogroen.gif|150px|thumb|Oude logo van Groen&lt;br /&gt;(2003- 2012)]]
'''Groen''' is een [[Vlaanderen|Vlaamse]], [[progressivisme|progressieve]] en [[Ecologisme|groene]] [[politieke partij]], die ongeveer 7250 leden telt (2012). Tot 15 november 2003 heette de partij 'Agalev'. Daarna werd de naam 'Groen!'. Begin 2012 werd het uitroepteken weggelaten. De huidige voorzitter is [[Wouter Van Besien]]. De partij maakt deel uit van de [[Brusselse Hoofdstedelijke Regering]].

[[Pacifisme]], sociale rechtvaardigheid en ecologie (duurzame ontwikkeling) zijn drie pijlers van het Groen-programma. De partij noemt 'de kwaliteit van leven' de 'groene draad door haar programma'. Groen is een zusterpartij van het Franstalige [[Ecolo]].
"""

    expected_links = {(u'Vlaanderen', u'Vlaamse'): 1,
                      (u'Progressivisme', u'progressieve'): 1,  # capital P corrected by our WP case fixer
                      (u'Ecologisme', u'groene'): 1,
                      (u'Politieke partij', u'politieke partij'): 1,
                      (u'Wouter Van Besien', u'Wouter Van Besien'): 1,
                      (u'Brusselse Hoofdstedelijke Regering', u'Brusselse Hoofdstedelijke Regering'): 1,
                      (u'Pacifisme', u'Pacifisme'): 1,
                      (u'Ecolo', u'Ecolo'): 1
                      }

    links, ngrams = page_statistics(text, N=None)

    assert_equal(set(expected_links.keys()),
                 set(links.keys()))


def test_parse_dump_ngrams():
    db = sqlite3.connect(':memory:')
    cur = db.cursor()
    with open(createtables_path()) as create:
        cur.executescript(create.read())

    dump = join(dirname(abspath(__file__)),
                'nlwiki-20140927-pages-articles-sample.xml')
    parse_dump(dump, db, N=2)

    ngram_count = dict(cur.execute('select ngram, tf from ngrams;'))
    link_count = dict(cur.execute('select target, count from linkstats;'))

    assert_in(ur'van München', ngram_count)
    assert_in(u'Vrede van M\xfcnster', link_count)
    #assert_greater(link_count[('AMX Index', 'Amsterdam Midkap Index')], 0)
    assert_greater(link_count['AMX Index'], 0)


def test_parse_dump():
    db = sqlite3.connect(':memory:')
    cur = db.cursor()
    with open(createtables_path()) as create:
        cur.executescript(create.read())

    dump = join(dirname(abspath(__file__)),
                'nlwiki-20140927-pages-articles-sample.xml')
    parse_dump(dump, db, N=None)

    ngram_count = dict(cur.execute('select ngram, tf from ngrams;'))
    link_count = dict(cur.execute('select target, count from linkstats;'))

    assert_in('Heinrich Tessenow', ngram_count)
    assert_in('Heinrich Tessenow', link_count)


def test_parse_wikidump():
    tmpfile = 'abcdefXXXXX'
    dump = join(dirname(abspath(__file__)),
                'nlwiki-20140927-pages-articles-sample.xml')
    with tempfile.NamedTemporaryFile(tmpfile) as model_file:
        parse_wikidump_main(["--ngram=2", dump, model_file.name])

        db = sqlite3.connect(model_file.name)
        cur = db.cursor()
        actual = list(cur.execute('select count(*) from ngrams;'))[0][0]
        expected = 28944
        assert_equal(actual, expected)


def test_remove_links():
    text = """
        Wikisyntax is the [[syntax (to be parsed)|syntax]] used on
        [[Wikipedia]].{{citation needed|date=October 2014}}
        We have to parse it, and we use every [[hack]] in the
        [[text]][[book]] that we can find.
    """

    # Note space in "text book", inserted to match extract_links output (see
    # test above). If we don't do this, probabilities won't add up properly.
    expected = """
        Wikisyntax is the syntax used on Wikipedia.
        We have to parse it, and we use every hack in the
        text book that we can find.
    """

    assert_equal(remove_links(clean_text(text)).split(), expected.split())
