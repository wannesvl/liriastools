# coding: utf-8
from bs4 import BeautifulSoup
import urllib2, httplib, urllib, re, difflib, subprocess, tempfile, codecs

u_number = '0063507'
name = 'Van Loock, W.'
tel = '+32 16 32 92 64'
email = 'wannes.vanloock@kuleuven.be'


# Search for the DOI given a title; e.g.  "computation in Noisy Radio Networks"
def searchdoi(title, author):
    params = urllib.urlencode({"titlesearch":"titlesearch", "auth2" : author, "atitle2" : title, "multi_hit" : "on", "article_title_search" : "Search", "queryType" : "author-title"})
    headers = {"User-Agent": "Mozilla/5.0" , "Accept": "text/html", "Content-Type" : "application/x-www-form-urlencoded", "Host" : "www.crossref.org"}
    conn = httplib.HTTPConnection("www.crossref.org:80")
    conn.request("POST", "/guestquery/", params, headers)
    response = conn.getresponse()
    # print response.status, response.reason
    data = response.read()
    conn.close()
    return data


def get_bib(p, item):
    try:
        return p.findChild(attrs={'name': item}).get_text()
    except:
        return ''


def sort_title(title, p=re.compile('[\W_]+')):
    return ''.join(sorted(p.sub('', title).lower()))


with open('OPACJrnList.txt', 'r') as f:
    journals_ieee = [l.rstrip('\r\n').strip('"').split('","') for l in f.readlines()]

with open('jnlactive.csv', 'rb') as f:
    journals_sd = [l.rstrip('\r\n').strip('"').split('","') for l in f.readlines()]

with open('OPACCnfList.txt', 'r') as f:
    conferences_ieee = [l.rstrip('\r\n').strip('"').split('","') for l in f.readlines()]

with open('open_access.tex', 'r') as f:
    template = unicode(f.read())

# Make dictionary of journal and conference titles
url_sd = 'http://www.sciencedirect.com/science/journal/'
journals = {sort_title(j[0]): j[9] for j in journals_ieee}
journals.update({sort_title(j[0]): url_sd + j[1] for j in journals_sd})
conferences = {sort_title(j[0]): (j[7], j[0]) for j in conferences_ieee}

# journal_titles_ieee = map(sort_title, [r[0] for r in journals_ieee])
# journal_titles_sd = map(sort_title, [r[0] for r in journals_sd])
# conference_titles = map(sort_title, [r[0] for r in conferences])

url = 'https://lirias.kuleuven.be/cv?u=U' + u_number + '&link=true&layout=APA-style'
page = urllib2.urlopen(url)
soup = BeautifulSoup(page.read())

lirias_url = 'http://lirias.kuleuven.be/handle/123456789/'

# Find all 'h1' tags
for p in soup.find_all('p'):
    # Get header text
    h = p.find_previous().find_previous()
    if h.name == 'h2':
        header = h.getText()[:2]
        print header
        if header != 'IT' and header != 'IC':
            break
    author = [a.get_text() for a in p.findChildren(attrs={'name': 'author'})]
    if author[0] == name:
        title = p.findChild(attrs={'name': 'title'}).get_text()
        try:
            doi_response = BeautifulSoup(searchdoi(title, author[0]))
            doi = doi_response.find('a', href=re.compile('^http://dx.doi.org/')).get_text()
        except:
            doi = raw_input("Could not find doi for " + title + "\n please enter manually, provide alternate link or leave blank: ")
        IR = p.find_parent('a').attrs['href']
        journal = get_bib(p, 'journal')
        pp = get_bib(p, 'pages')
        vol = get_bib(p, 'volume')
        date = get_bib(p, 'date')
        congress_date = get_bib(p, 'congressdate')
        loc = get_bib(p, 'congresslocation')
        congress = get_bib(p, 'congressname')
        if header == 'IT':
            journal_url = journals.get(sort_title(journal), None)  # Get journal url.
            if journal_url is None:
                journal_url = raw_input("Couldn't find journal. Please provide a url for the journal: ")
        elif header == 'IC':
            match = difflib.get_close_matches(sort_title(congress + date), conferences.keys())
            answer = 'n'
            i = 0
            while answer.lower() == 'n' and i < len(match):
                c = conferences[match[i]][1]
                answer = raw_input('Do we have a match (y/n):\nlirias: ' + congress + '\nbest guess: ' + c + ' ')
                if answer.lower() == 'y':
                    journal_url = conferences[match[i]][0]
                    break
                i += 1
            else:
                journal_url = raw_input("Couldn't find conference. Please provide a url for the conference: ")
        # Make tex file
        citation = p.get_text().split(title)
        d = {'first': citation[0].strip('. '),
             'title': title,
             'last': citation[1].strip('. '),
             'doi': doi,
             'journal_url': journal_url,
             'email': email,
             'tel': tel,
             'lirias_handle': IR
             }
        filename = title.replace(' ', '_').lower() + '.tex'
        with codecs.open(filename, 'wt', encoding='utf-8') as f:
            f.write(template.format(**d))
        # make pdf
        out = tempfile.TemporaryFile()
        ec = subprocess.call(["pdflatex", "-halt-on-error", filename], stdout=out)

# Clean up files
subprocess.call(["latexmk", "-c"])
