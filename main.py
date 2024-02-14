import asyncio
from webserver import keep_alive
import os
import discord
from discord.ext import commands
import youtube_dl
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from youtube_dl import YoutubeDL
from pprint import pprint
import urllib.request
from urllib.parse import quote
import re
import random


q=[]
dcapi=os.environ['dcapi']
spcs=os.environ['spcs']
spcid=os.environ['spcid']
ytcid=os.environ['ytcid']
ytcs=os.environ['ytcs']
ytdevkey=os.environ['ytdevkey']


sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=spcid,client_secret=spcs))

client = commands.Bot(command_prefix="!")

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
            pprint(data)
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

def youtubesearch(songName):
    html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + quote(songName))
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    return video_ids[0]

def queue(arg):
    q=[]
    pl_id = arg
    response = sp.playlist_items(pl_id,offset=0,fields='items.track.id',additional_types=['track'])
    for i in range(len(response['items'])):
        response['items'][i]['track']['id']
        track = sp.track(response['items'][i]['track']['id'])
        song=track['artists'][0]['name']+' - '+track['name']
        q.append(song)
    return q

async def player(ctx,channel,url):
    async with ctx.typing():
                voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
                if voice is None or not voice.is_connected():
                    await voice.disconnect()
                    await channel.connect()
                player = await YTDLSource.from_url(url, loop=client.loop)
                ctx.message.guild.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
    await ctx.send('**Now playing:** {}'.format(player.title))

async def queuer(ctx,channel):
    global q
    while q!=[]:
        i=0
        m=youtubesearch(q.pop(i))
        await player(ctx,channel,m)
        print(m,'          ',q)
        await asyncio.sleep(vid_len(m))
        i+=1
    await discord.utils.get(client.voice_clients, guild=ctx.guild).disconnect()

def vid_len(url='https://www.youtube.com/watch?v=hUEaczrqxTs'):
    return YoutubeDL().extract_info(url, download=False)['duration']


@client.command()
async def play(ctx, *,arg):
    global q
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return
    else:
        channel = ctx.message.author.voice.channel
    
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice==None:
        await channel.connect()
    if arg.startswith('https://www.youtube.com'):
        q.append(arg)
    elif arg.startswith('https://open.spotify.com/track/') :
        song=sp.track(arg)
        q.append(song['name'])
    elif arg.startswith('https://open.spotify.com/playlist/') :
        q.extend(queue(arg))
        print(q)
    return await queuer(ctx,channel)
@client.command()
async def test(ctx):
  global q
  print(q)
      

@client.command()
async def leave(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await ctx.send("Fuck u.")
        await voice.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@client.command()
async def shuffle(ctx):
  await ctx.send("**Queue SHuffled**")
  global q
  q=list(random.shuffle(q))

@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        await ctx.send("And then there was silence.") 
        voice.pause()
    else:
        await ctx.send("Currently no audio is playing.")

@client.command()
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        await ctx.send("Bringing back the music.")
        voice.resume()
    else:
        await ctx.send("The audio is not paused.")

@client.command()
async def stop(ctx):
    global q
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    await ctx.send("ok bitch.") 
    voice.stop()
    q=[]
    

@client.command()
async def skip(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return
    else:
        channel = ctx.message.author.voice.channel
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    await ctx.send("**¯\_(ツ)_/¯**") 
    voice.stop()
    return await queuer(ctx,channel)

@client.command()
async def ping(ctx):
    await ctx.send(f'**Ping: **{round(client.latency * 1000)}ms')

keep_alive()
client.run(dcapi)