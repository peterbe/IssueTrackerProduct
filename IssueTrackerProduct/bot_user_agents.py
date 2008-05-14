bots = '''
Acoon-Robot
Gigabot
Googlebot
msnbot
msnbot-media/1.0
Teoma
Slurp
aipbot
ia_archiver
Alexibot
Aqua_Products
asterias
b2w/0.1
BackDoorBot/1.0
becomebot
Bloglines/3.
BlowFish/1.0
Bookmark search tool
BotALot
BotRightHere
BuiltBotTough
Bullseye/1.0
BunnySlippers
CCBot/1.0
CheeseBot
CherryPicker
CherryPickerElite/1.0
CherryPickerSE/1.0
Copernic
CopyRightCheck
DittoSpyder
EmailCollector
EmailSiphon
EmailWolf
EroCrawler
ExtractorPro
FairAd Client
Fasterfox
Flaming AttackBot
Foobot
Gaisbot
GetRight/4.2
Harvest/1.5
hloader
HTTrack 3.0
humanlinks
IconSurf
InfoNaviRobot
Iron33/1.0.2
Jakarta Commons-HttpClient
JennyBot
Kenjin Spider
Keyword Density/0.9
larbin
LexiBot
libWeb/clsHTTP
LinkextractorPro
LinkScan/8.1a Unix
LinkWalker
LNSpiderguy
lwp-trivial
Mata Hari
Microsoft URL Control
MIIxpc
MIIxpc/4.2
Mister PiX
moget
MSIECrawler
NetAnts
NICErsPRO
Offline Explorer
Openbot
Openfind
Openfind data gatherer
Oracle Ultra Search
PerMan
ProPowerBot/2.14
ProWebWalker
psbot
Python-urllib
QueryN Metasearch
Radiation Retriever 1.1
RepoMonkey
RepoMonkey Bait & Tackle/v1.01
RMA
searchpreview
SiteSnagger
SpankBot
spanner
SurveyBot
suzuran
Szukacz/1.4
Teleport
TeleportPro
Telesoft
The Intraformant
TheNomad
TightTwatBot
toCrawl/UrlDispatcher
True_Robot
turingos
TurnitinBot
URL Control
URL_Spider_Pro
URLy Warning
VCI
VCI WebViewer VCI WebViewer Win32
Web Image Collector
WebAuto
WebBandit
WebCapture 2.0
WebCopier
WebEnhancer
WebSauger
Website Quester
Webster Pro
WebStripper
WebZip
Wget
WWW-Collector-E
Zeus
Zeus Link Scout
'''.strip().splitlines()

__all__=['is_bot_user_agent']

import re
_regex = re.compile(r'\b(%s)\b' % '|'.join([re.escape(x) for x in bots]))

def is_bot_user_agent(user_agent):
    return bool(_regex.findall(user_agent))



if __name__=='__main__':
    import unittest
    class UserAgentTestCase(unittest.TestCase):
        def test_batch(self):
            tests = [
            (False, 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.14) Gecko/20080419 Ubuntu/8.04 (hardy) Firefox/2.0.0.14'),
            (False, 'Mozilla/5.0 (compatible; Konqueror/4.0; Linux) KHTML/4.0.3 (like Gecko)'),
            (True, 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'),
            (True, 'msnbot-media/1.0 (+http://search.msn.com/msnbot.htm)'),
            (True, 'Wget/1.10.2'),
            (True, 'Mozilla/5.0 (compatible; Yahoo! Slurp/3.0; http://help.yahoo.com/help/us/ysearch/slurp)'),
            (True, 'Mozilla/5.0 (compatible; Ask Jeeves/Teoma; +http://about.ask.com/en/docs/about/webmasters.shtml)'),
            (True, 'msnbot/1.1 (+http://search.msn.com/msnbot.htm)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'),
            (True, 'Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)'),
            (False, ''),
            (True, 'Bloglines/3.1 (http://www.bloglines.com; 1 subscriber)'),
            (False, 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.2.1; aggregator:Tailrank (Spinn3r 2.1); http://spinn3r.com/robot) Gecko/20021130'),
            (False, 'curl/7.18.0 (i486-pc-linux-gnu) libcurl/7.18.0 OpenSSL/0.9.8g zlib/1.2.3.3 libidn/1.1'),
            (False, 'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.4.4'),
            (False, 'User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2)'),
            (True, 'Nokia6820/2.0 (4.83) Profile/MIDP-1.0 Configuration/CLDC-1.0 (compatible; Googlebot-Mobile/2.1; +http://www.google.com/bot.html)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; SV1; TencentTraveler ; .NET CLR 1.1.4322; .NET CLR 2.0.50727)'),
            (False, 'Yandex/1.01.001 (compatible; Win16; I)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'),
            (False, 'Mozilla/5.0 (Twiceler-0.9 http://www.cuill.com/twiceler/robot.html)'),
            (False, 'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; 3 subscribers; feed-id=10163738114753035636)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7) Gecko/20040815 Firefox/0.8 (MOOX M3)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.2; .NET CLR 1.1.4322)'),
            (False, 'Site 24 X 7 RPT-HTTPClient/0.3-3E'),
            (False, 'Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10_4_11; en) AppleWebKit/525.18 (KHTML, like Gecko) Version/3.1.1 Safari/525.18'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)'),
            (False, 'Mozilla/5.0 (compatible; Google Desktop)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.9b5) Gecko/2008032620 Firefox/3.0b5'),
            (False, 'Mozilla/4.0 (compatible;)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'),
            (False, 'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; 2 subscribers; feed-id=7862281799759567937)'),
            (False, 'Yandex/1.01.001 (compatible; Win16; H)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'),
            (False, 'Mozilla/5.0 (compatible; YodaoBot/1.0; http://www.yodao.com/help/webmaster/spider/; )'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; nb-NO; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'),
            (False, 'YandexSomething/1.0'),
            (False, 'YandexBlog/0.99.101 (compatible; DOS3.30; Mozilla/5.0; B; robot) 0 readers'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; EmbeddedWB 14,52 from: http://www.bsalsa.com/ Embedded Web Browser from: http://bsalsa.com/; .NET CLR 1.1.4322; .NET CLR 2.0.50727)'),
            (False, 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9b5) Gecko/2008050509 Firefox/3.0b5'),
            (False, 'Mozilla/5.0 (X11; U; Linux i686 (x86_64); en-US; rv:1.8.1) Gecko/20061010 Firefox/2.0'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30; .NET CLR 3.0.04506.648)'),
            (True, 'Jakarta Commons-HttpClient/3.1'),
            (False, 'Nokia6682/2.0 (3.01.1) SymbianOS/8.0 Series60/2.6 Profile/MIDP-2.0 configuration/CLDC-1.1 UP.Link/6.3.0.0.0 (compatible;YahooSeeker/M1A1-R2D2; http://help.yahoo.com/help/us/ysearch/crawling/crawling-01.html)'),
            (True, 'Acoon-Robot 4.0.2.17 (http://www.acoon.de)'),
            (False, 'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; fr-fr) AppleWebKit/312.5 (KHTML, like Gecko) Safari/312.3'),
            (True, 'CCBot/1.0 (+http://www.commoncrawl.org/bot.html)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.2; WOW64; .NET CLR 2.0.50727; .NET CLR 3.0.04506.648; .NET CLR 3.5.21022)'),
            (True, 'Googlebot-Image/1.0'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.8.1) VoilaBot BETA 1.2 (support.voilabot@orange-ftgroup.com)'),
            (False, 'Mozilla/5.0(Windows;N;Win98;m18)Gecko/20010124'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)'),
            (False, 'Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14,gzip(gfe) (via translate.google.com)'),
            (False, 'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/51 (like Gecko) Safari/51'),
            (False, 'Mozilla/5.0 (compatible; Exabot-Images/3.0; +http://www.exabot.com/go/robot)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows XP)'),
            (False, 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.12) Gecko/20080208 Fedora/2.0.0.12-1.fc8 Firefox/2.0.0.12'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30; InfoPath.1; .NET CLR 3.0.04506.648)'),
            (False, 'YahooFeedSeeker Testing/2.0 (compatible; Mozilla 4.0; MSIE 5.5; http://publisher.yahoo.com/rssguide; users 1; views 176)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1;1813)'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'),
            (False, 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; ja-JP-mac; rv:1.9b5) Gecko/2008032619 Firefox/3.0b5'),
            (False, 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 5.0)'),
            (False, 'Mozilla/5.0 (Windows; U; WinNT4.0; en-US; rv:1.2) Gecko/20021126'),
            (False, 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 2.0.50727)'),
            (False, 'Java/1.4.1_04'),
            ]
            
            for expect, user_agent in tests:
                self.assertEqual(expect, is_bot_user_agent(user_agent))
                
    def suite():
        return unittest.makeSuite(UserAgentTestCase)
    
    unittest.main()
            