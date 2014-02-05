"This file contains techniques for extracting data from HTML pages."
from bs4 import BeautifulSoup


class Technique(object):
    def __init__(self, extractor=None, *args, **kwargs):
        """
        Capture the extractor this technique is running within,
        if any.
        """
        self.extractor = extractor
        super(Technique, self).__init__(*args, **kwargs)

    def extract(self, html):
        "Extract data from a string representing an HTML document."
        return {'titles': [],
                'descriptions': [],
                'images': [],
                'urls': [],
                }

class HeadTags(Technique):
    """
    Extract info from standard HTML metatags like title, for example:

        <head>
            <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
            <meta name="author" content="Will Larson" />
            <meta name="description" content="Will Larson&#39;s blog about programming and other things." />
            <meta name="keywords" content="Blog Will Larson Programming Life" />
            <link rel="alternate" type="application/rss+xml" title="Page Feed" href="/feeds/" />
            <link rel="canonical" href="http://lethain.com/digg-v4-architecture-process/">
            <title>Digg v4&#39;s Architecture and Development Processes - Irrational Exuberance</title>
        </head>

    This is usually a last-resort, low quality, but reliable parsing mechanism.
    """
    meta_name_map = {
        "description": "descriptions",
        "author": "authors",
        }

    def extract(self, html):
        "Extract data from meta, link and title tags within the head tag."
        extracted = {}
        soup = BeautifulSoup(html)
        # extract data from title tag
        title_tag = soup.find('title')
        if title_tag:
            extracted['titles'] = [title_tag.string]

        # extract data from meta tags
        for meta_tag in soup.find_all('meta'):
            if 'name' in meta_tag.attrs and 'content' in meta_tag.attrs:
                name = meta_tag['name']
                if name in self.meta_name_map:
                    name_dest = self.meta_name_map[name]
                    if name_dest not in extracted:
                        extracted[name_dest] = []
                    extracted[name_dest].append(meta_tag.attrs['content'])

        # extract data from link tags
        for link_tag in soup.find_all('link'):
            if 'rel' in link_tag.attrs:
                if ('alternate' in link_tag['rel'] or link_tag['rel'] == 'alternate') and 'type' in link_tag.attrs and link_tag['type'] == "application/rss+xml" and 'href' in link_tag.attrs:
                    if 'feeds' not in extracted:
                        extracted['feeds'] = []
                    extracted['feeds'].append(link_tag['href'])
                elif ('canonical' in link_tag['rel'] or link_tag['rel'] == 'canonical') and 'href' in link_tag.attrs:
                    if 'urls' not in extracted:
                        extracted['urls'] = []
                    extracted['urls'].append(link_tag['href'])

        return extracted



class FacebookOpengraphTags(Technique):
    """
    Extract info from html Facebook Opengraph meta tags.

    Facebook tags are ubiquitous on high quality sites, and tend to be higher quality
    than more manual discover techniques. Especially for picking high quality images,
    this is probably your best bet.

    Some example tags from `the Facebook opengraph docs <https://developers.facebook.com/docs/opengraphprotocol/>`::

        <meta property="og:title" content="The Rock"/>
        <meta property="og:type" content="movie"/>
        <meta property="og:url" content="http://www.imdb.com/title/tt0117500/"/>
        <meta property="og:image" content="http://ia.media-imdb.com/rock.jpg"/>
        <meta property="og:site_name" content="IMDb"/>
        <meta property="fb:admins" content="USER_ID"/>
        <meta property="og:description"
            content="A group of U.S. Marines, under command of
                     a renegade general, take over Alcatraz and
                     threaten San Francisco Bay with biological
                     weapons."/>

    There are a bunch of other opengraph tags, but they don't seem
    useful to extraction's intent at this point.
    """
    property_map = {
        'og:title': 'titles',
        'og:url': 'urls',
        'og:image': 'images',
        'og:description': 'descriptions',
        'og:type': 'types',  # Ideally would annotate this to indicate an OG type
    }

    def extract(self, html):
        "Extract data from Facebook Opengraph tags."
        extracted = {}
        soup = BeautifulSoup(html)
        og_tags = {}
        for meta_tag in soup.find_all('meta'):
            try:
                try:
                    property_ = meta_tag['property']
                except KeyError:
                    property_ = meta_tag['name']

                if not property_.startswith("og:"):
                    continue
                content = meta_tag['content'].strip()
                if not content:
                    continue

                og_prop = property_[len("og:"):].replace(":", "_")
                og_tags[og_prop] = content

                property_dest = self.property_map[property_]
                extracted.setdefault(property_dest, []).append(content)
            except KeyError:
                pass

        if 'type' in og_tags:
            extracted['og_tags'] = og_tags
        return extracted


class HTML5SemanticTags(Technique):
    """
    The HTML5 `article` tag, and also the `video` tag give us some useful
    hints for extracting page information for the sites which happen to
    utilize these tags.

    This technique will extract information from pages formed like::

        <html>
          <body>
            <h1>This is not a title to HTML5SemanticTags</h1>
            <article>
              <h1>This is a title</h1>
              <p>This is a description.</p>
              <p>This is not a description.</p>
            </article>
            <video>
              <source src="this_is_a_video.mp4">
            </video>
          </body>
        </html>

    Note that `HTML5SemanticTags` is intentionally much more conservative than
    `SemanticTags`, as it provides high quality information in the small number
    of cases where it hits, and otherwise expects `SemanticTags` to run sweep
    behind it for the lower quality, more abundant hits it discovers.
    """
    def extract(self, html):
        "Extract data from Facebook Opengraph tags."
        titles = []
        descriptions = []
        videos = []
        soup = BeautifulSoup(html)
        for article in soup.find_all('article') or []:
            title = article.find('h1')
            if title:
                titles.append(" ".join(title.strings))
            desc = article.find('p')
            if desc:
                descriptions.append(" ".join(desc.strings))

        for video in soup.find_all('video') or []:
            for source in video.find_all('source') or []:
                if 'src' in source.attrs:
                    videos.append(source['src'])

        return {'titles':titles, 'descriptions':descriptions, 'videos':videos}


class SemanticTags(Technique):
    """
    This technique relies on the basic tags themselves--for example,
    all IMG tags include images, most H1 and H2 tags include titles,
    and P tags often include text usable as descriptions.

    This is a true last resort technique.
    """
    # list to support ordering of semantics, e.g. h1
    # is higher quality than h2 and so on
    # format is ("name of tag", "destination list", store_first_n)
    extract_string = [('h1', 'titles', 3),
                      ('h2', 'titles', 3),
                      ('h3', 'titles', 1),
                      ('p', 'descriptions', 5),
                      ]
    # format is ("name of tag", "destination list", "name of attribute" store_first_n)
    extract_attr = [('img', 'images', 'src', 10)]

    def extract(self, html):
        "Extract data from Facebook Opengraph tags."
        extracted = {}
        soup = BeautifulSoup(html)

        for tag, dest, max_to_store in self.extract_string:
            for found in soup.find_all(tag)[:max_to_store] or []:
                if dest not in extracted:
                    extracted[dest] = []
                extracted[dest].append(" ".join(found.strings))


        for tag, dest, attribute, max_to_store in self.extract_attr:
            for found in soup.find_all(tag)[:max_to_store] or []:
                if attribute in found.attrs:
                    if dest not in extracted:
                        extracted[dest] = []
                    extracted[dest].append(found[attribute])

        return extracted


class Twitter(Technique):
    """
       <meta name="twitter:card" content="player">
    <meta name="twitter:site" content="@youtube">
    <meta name="twitter:url" content="http://www.youtube.com/watch?v=eAwwQ6lYJfo">
    <meta name="twitter:title" content="The Big Bang Theory (bloopers) -- Sheldon">
    <meta name="twitter:description" content="Recommended Links Mobile App Link: http://www.iLivingApp.com/mobileappforpros Link: http://www.morewebmoney.com/ Link: http://cbpirate.com/?hop=rdco5 Video i...">
    <meta name="twitter:image" content="http://i1.ytimg.com/vi/eAwwQ6lYJfo/maxresdefault.jpg">
    <meta name="twitter:app:name:iphone" content="YouTube">
    <meta name="twitter:app:id:iphone" content="544007664">
    <meta name="twitter:app:name:ipad" content="YouTube">
    <meta name="twitter:app:id:ipad" content="544007664">
      <meta name="twitter:app:url:iphone" content="vnd.youtube://watch/eAwwQ6lYJfo">
      <meta name="twitter:app:url:ipad" content="vnd.youtube://watch/eAwwQ6lYJfo">
    <meta name="twitter:app:name:googleplay" content="YouTube">
    <meta name="twitter:app:id:googleplay" content="com.google.android.youtube">
    <meta name="twitter:app:url:googleplay" content="http://www.youtube.com/watch?v=eAwwQ6lYJfo">
      <meta name="twitter:player" content="https://www.youtube.com/embed/eAwwQ6lYJfo">
      <meta name="twitter:player:width" content="960">
      <meta name="twitter:player:height" content="720">

    Player appears to be something we can embed in an iframe
    """

    # We're actually looking for just one twitter card thingy

    def extract(self, html):
        extracted = {}
        soup = BeautifulSoup(html)
        card = {}

        for meta_tag in soup.find_all('meta'):
            try:
                try:
                    property_ = meta_tag['name']
                except KeyError:
                    property_ = meta_tag['property']
                if not property_.startswith("twitter:"):
                    continue

                property_ = property_[len("twitter:"):].replace(":", "_")
                card[property_] = meta_tag.attrs['content']
            except KeyError:
                pass

        if 'card' in card:
            extracted.setdefault('twitter_cards', []).append(card)
        return extracted
