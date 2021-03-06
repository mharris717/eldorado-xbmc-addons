import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import urllib2
import re, string
import os
from t0mm0.common.addon import Addon
from t0mm0.common.net import Net
net = Net()

try:
    import json
except:
    import simplejson as json


##### XBMC  ##########
addon = Addon('plugin.video.tgun', sys.argv)
xaddon = xbmcaddon.Addon(id='plugin.video.tgun')
datapath = addon.get_profile()


##### Paths ##########
cookie_path = os.path.join(datapath, 'cookies')
cookie_jar = os.path.join(cookie_path, "cookiejar.lwp")
if os.path.exists(cookie_path) == False:
    os.makedirs(cookie_path)

##### Queries ##########
play = addon.queries.get('play', None)
mode = addon.queries['mode']
page_num = addon.queries.get('page_num', None)
url = addon.queries.get('url', None)

print 'Mode: ' + str(mode)
print 'Play: ' + str(play)
print 'URL: ' + str(url)
print 'Page: ' + str(page_num)

################### Global Constants #################################

main_url = 'http://www.tgun.tv/'
shows_url = main_url + 'shows/'
showlist_url_1 = shows_url + 'chmm.php'
showlist_url_2 = shows_url + 'chmm2.php'
classic_url = main_url + 'classic/'
classic_shows_url = classic_url + 'chm%s.php'
livetv_url = main_url + 'usa/'
livetv_pages = livetv_url + 'chmtv%s.php'
addon_path = xaddon.getAddonInfo('path')
icon_path = addon_path + "/icons/"

######################################################################

def Notify(typeq, title, message, times, line2='', line3=''):
     #simplified way to call notifications. common notifications here.
     if title == '':
          title='TGUN Notification'
     if typeq == 'small':
          if times == '':
               times='5000'
          smallicon= icon_path + 'tgun.png'
          xbmc.executebuiltin("XBMC.Notification("+title+","+message+","+times+","+smallicon+")")
     elif typeq == 'big':
          dialog = xbmcgui.Dialog()
          dialog.ok(' '+title+' ', ' '+message+' ', line2, line3)
     else:
          dialog = xbmcgui.Dialog()
          dialog.ok(' '+title+' ', ' '+message+' ')


def sys_exit():
    xbmc.executebuiltin("XBMC.Container.Update(addons://sources/video/plugin.video.tgun?mode=main,replace)")
    return


def getSwfUrl(channel_name):
        """Helper method to grab the swf url, resolving HTTP 301/302 along the way"""
        base_url = 'http://www.justin.tv/widgets/live_embed_player.swf?channel=%s' % channel_name
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0',
                   'Referer' : 'http://www.justin.tv/'+channel_name}
        req = urllib2.Request(base_url, None, headers)
        response = urllib2.urlopen(req)
        return response.geturl()


def justintv(embedcode):

    channel = re.search('data="(.+?)"', embedcode, re.DOTALL).group(1)  
    channel_name = re.search('http://www.justin.tv/widgets/.+?\?channel=(.+)', channel).group(1)
    
    api_url = 'http://usher.justin.tv/find/%s.json?type=live' % channel_name
    print 'Retrieving: %s' % api_url
    html = net.http_GET(api_url).content
    
    data = json.loads(html)
    jtv_token = ' jtv='+data[0]['token'].replace('\\','\\5c').replace(' ','\\20').replace('"','\\22')
    rtmp = data[0]['connect']+'/'+data[0]['play']
    swf = ' swfUrl=%s swfVfy=1' % getSwfUrl(channel_name)
    page_url = ' Pageurl=http://www.justin.tv/' + channel_name
    final_url = rtmp + jtv_token + swf + page_url
    return final_url


def get_blogspot(embedcode):
    print 'blogspot'
    return ''


def sawlive(embedcode, ref_url):
    url = re.search("<script type='text/javascript'> swidth='600', sheight='530';</script><script type='text/javascript' src='(.+?)'></script>", embedcode, re.DOTALL).group(1)
    ref_data = {'Referer': ref_url}

    try:
        ## Current SawLive resolving technique - always try to fix first
        html = net.http_GET(url,ref_data).content
        link = re.search('src="(http://sawlive.tv/embed/watch/[A-Za-z0-9_/]+)">', html).group(1)
        print link

    except Exception, e:
        ## Use if first section does not work - last resort which returns compiled javascript
        print 'SawLive resolving failed, attempting jsunpack.jeek.org, msg: %s' % e
        Notify('small','SawLive', 'Resolve Failed. Using jsunpack','')
        
        jsunpackurl = 'http://jsunpack.jeek.org'
        data = {'urlin': url}
        html = net.http_POST(jsunpackurl, data).content
        link = re.search('src="(http://sawlive.tv/embed/watch/[A-Za-z0-9]+[/][A-Za-z0-9_]+)"',html).group(1)
        print link

    html = net.http_GET(link, ref_data).content
    
    swfPlayer = re.search('SWFObject\(\'(.+?)\'', html).group(1)
    playPath = re.search('\'file\', \'(.+?)\'', html).group(1)
    streamer = re.search('\'streamer\', \'(.+?)\'', html).group(1)
    appUrl = re.search('rtmp[e]*://.+?/(.+?)\'', html).group(1)
    rtmpUrl = ''.join([streamer,
       ' playpath=', playPath,
       ' app=', appUrl,
       ' pageURL=', url,
       ' swfUrl=', swfPlayer,
       ' live=true'])
    print rtmpUrl
    return rtmpUrl


def mediaplayer(embedcode):
    url = re.search('<embed type="application/x-mplayer2" .+? src="(.+?)"></embed>', embedcode).group(1)
    print 'Retrieving: %s' % url
    html = net.http_GET(url).content
    
    matches = re.findall('<Ref href = "(.+?)"/>', html)
    url = matches[1]
    
    print 'Retrieving: %s' % url
    html = net.http_GET(url).content
    print html
    
    return re.search('Ref1=(.+?.asf)', html).group(1)


def ilive(embedcode):
    
    channel = re.search('<script type="text/javascript" src="http://www.ilive.to/embed/(.+?)&width=.+?"></script>', embedcode)
    
    if channel:
        url = 'http://www.ilive.to/embedplayer.php?channel=%s' % channel.group(1)
        print 'Retrieving: %s' % url
        html = net.http_GET(url).content
        filename = re.search('.*streamer=rtmp.*?&file=([^&]+).flv.*', html).group(1)
    else:
        filename = re.search('streamer=rtmp://live.ilive.to/edge&file=(.+?)&autostart=true&controlbar=bottom"', embedcode).group(1)
        url = 'http://www.ilive.to/embedplayer.php'

    swf = 'http://cdn.static.ilive.to/jwplayer/player_embed.swf'
    return 'rtmp://live.ilive.to/redirect playPath=' + filename + ' swfUrl=' + swf + ' swfVfy=true live=true pageUrl=' + url


def embedrtmp(embedcode):
    stream = re.search('<embed src="(.+?)".*?;file=(.+?)&amp;streamer=(.+?)&amp;.*?>', embedcode)
    print stream.group(3)
    app = re.search('rtmp[e]*://.+?/(.+?/)', stream.group(3)).group(1)
    return stream.group(3) + ' app=' + app + ' playpath=' + stream.group(2) + ' swfUrl=' + stream.group(1) + ' live=true'


def castto(embedcode, url):
    data = {'Referer': url}
    
    parms = re.search('<script type="text/javascript"> fid="(.+?)"; v_width=.+; .+ src=".+castto.+"></script>', embedcode)
    
    link = 'http://static.castto.me/embed.php?channel=%s' % parms.group(1)
    html = net.http_GET(link, data).content
    swfPlayer = re.search('SWFObject\(\'(.+?)\'', html).group(1)
    playPath = re.search('\'file\',\'(.+?)\'', html).group(1)
    streamer = re.search('\'streamer\',\'(.+?)\'', html).group(1)
    rtmpUrl = ''.join([streamer,
       ' playpath=', playPath,
       ' pageURL=', 'http://static.castto.me',
       ' swfUrl=', swfPlayer,
       ' live=true',
       ' token=#ed%h0#w@1'])
    print rtmpUrl
    return rtmpUrl


def owncast(embedcode, url):
    data = {'Referer': url}
    
    parms = re.search('<script type="text/javascript"> fid="(.+?)"; v_width=(.+?); v_height=(.+?);</script><script type="text/javascript" src="(.+?)"></script>', embedcode)
    
    link = 'http://www.owncast.me/embed.php?channel=%s&vw=%s&vh=%s&domain=www.tgun.tv' % (parms.group(1), parms.group(2), parms.group(3))
    #html = net.http_GET(link, data).content
    referrer = url
    USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
    req = urllib2.Request(link)
    req.add_header('User-Agent', USER_AGENT)
    req.add_header('Referer', referrer)
    response = urllib2.urlopen(req)
    html = response.read()

    swfPlayer = re.search('SWFObject\(\'(.+?)\'', html).group(1)
    playPath = re.search('\'file\',\'(.+?)\'', html).group(1)
    streamer = re.search('\'streamer\',\'(.+?)\'', html).group(1)
    rtmpUrl = ''.join([streamer,
       ' playpath=', playPath,
       ' pageURL=', 'http://static.castto.me',
       ' swfUrl=', swfPlayer,
       ' live=true'])
    print rtmpUrl
    return rtmpUrl
    

if play:

    html = net.http_GET(url).content
    embedcode = re.search("(<object type=\"application/x-shockwave-flash\"|<!-- start embed -->|<!-- BEGIN PLAYER CODE.+?-->|<!-- START PLAYER CODE &ac=270 kayakcon11-->)(.+?)<!-- END PLAYER CODE -->", html, re.DOTALL).group(2)
    embedcode = re.sub('<!--.+?-->', '', embedcode)

    if re.search('justin.tv', embedcode):
        stream_url = justintv(embedcode)
    elif re.search('castto', embedcode):
        stream_url = castto(embedcode, url)
    elif re.search('owncast', embedcode):
        stream_url = owncast(embedcode, url)
    elif re.search('sawlive', embedcode):
        stream_url = sawlive(embedcode, url)
    elif re.search('ilive.to', embedcode):
        stream_url = ilive(embedcode)	
    elif re.search('MediaPlayer', embedcode):
        stream_url = mediaplayer(embedcode)
    elif re.search('rtmp', embedcode):
        stream_url = embedrtmp(embedcode)
 
    else:
        Notify('small','Undefined Stream', 'Channel is using an unknown stream type','')
        stream_url = None

    #Play the stream
    if stream_url:
        addon.resolve_url(stream_url)


def mainmenu():
    page = 1
    addon.add_directory({'mode': 'tvchannels', 'url': showlist_url_1, 'page_num': page}, {'title': 'Live TV Shows & Movies'}, img=icon_path + 'newtv.png')
    addon.add_directory({'mode': 'classics', 'url': classic_shows_url % page, 'page_num': page}, {'title': 'Classic TV Shows'}, img=icon_path + 'retrotv.png')
    #addon.add_directory({'mode': 'livetv', 'url': livetv_pages % '', 'page_num': page}, {'title': 'Live TV Channels'}, img=icon_path + 'retrotv.png')


if mode == 'main':
    mainmenu()


elif mode == 'mainexit':
    sys_exit()
    mainmenu()


elif mode == 'tvchannels':
    print 'Retrieving: %s' % url
    html = net.http_GET(url).content

    page = int(page_num) 
    if page > 1:
        addon.add_directory({'mode': 'mainexit'}, {'title': '[COLOR red]Back to Main Menu[/COLOR]'}, img=icon_path + 'back_arrow.png')

    if page < 2:
        page = page +  1
        addon.add_directory({'mode': 'tvchannels', 'url': showlist_url_2, 'page_num': page}, {'title': '[COLOR blue]Next Page[/COLOR]'}, img=icon_path + 'next_arrow.png')

    match = re.compile('<a[ A-Za-z0-9\"=]* Title[ ]*="(.+?)"[ A-Za-z0-9\"=]* href="(.+?)"><img border="0" src="(.+?)" style=.+?</a>').findall(html)
    for name, link, thumb in match:
        if not re.search('http://', thumb):
            thumb = main_url + thumb
        if not re.search('veetle', link):
            addon.add_video_item({'mode': 'channel', 'url': shows_url + link}, {'title': name}, img=thumb)


elif mode == 'classics':
    print 'Retrieving: %s' % url
    html = net.http_GET(url).content

    page = int(page_num)    
    if page > 1:
        addon.add_directory({'mode': 'mainexit'}, {'title': '[COLOR red]Back to Main Menu[/COLOR]'}, img=icon_path + 'back_arrow.png')

    if page < 6:
        page = page +  1
        addon.add_directory({'mode': 'classics', 'url': classic_shows_url % page, 'page_num': page}, {'title': '[COLOR blue]Next Page[/COLOR]'}, img=icon_path + 'next_arrow.png')

    match = re.compile('<td width=110><a href="(.+?)"><img src="(.+?)" border="0" width=100 height=60 />(.+?)</a>').findall(html)
    for link, thumb, name in match:
        if not re.search('http://', thumb):
            thumb = main_url + thumb
        addon.add_video_item({'mode': 'channel', 'url': classic_url + link}, {'title': name}, img=thumb)


elif mode == 'livetv':
    print 'Retrieving: %s' % url
    html = net.http_GET(url).content

    page = int(page_num)    
    if page > 1:
        addon.add_directory({'mode': 'mainexit'}, {'title': '[COLOR red]Back to Main Menu[/COLOR]'}, img=icon_path + 'back_arrow.png')

    if page < 7:
        page = page +  1
        addon.add_directory({'mode': 'livetv', 'url': livetv_pages % page, 'page_num': page}, {'title': '[COLOR blue]Next Page[/COLOR]'}, img=icon_path + 'next_arrow.png')

    match = re.compile('<td width="100%" .+? href="(.+?)"><img border="0" src="(.+?)" style=.+?></a>(.+?)</td>').findall(html)
    for link, thumb, name in match:
        if not re.search('http://', thumb):
            thumb = main_url + thumb
        addon.add_video_item({'mode': 'channel', 'url': livetv_url + link}, {'title': name}, img=thumb)

    
elif mode == 'exit':
    sys_exit()


if not play:
    addon.end_of_directory()