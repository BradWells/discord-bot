import discord
import json
import requests
import requests_cache
import us
from fuzzywuzzy import process
from discord.ext import commands


def load_json(token):
    with open('./covid.json') as f:
        config = json.load(f)
    return config.get(token)


class Covid(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        make_spellings()
        print('COVID cog ready')

    @commands.command(aliases=['covid19', 'covid-19', 'coronavirus', 'corona', 'rona', 'c19'])
    async def covid(self, ctx, *, state=None):
        update_covid_json()

        # Get all of US stats
        if state is None:
            await all_us_cases(ctx)
            return

        sent = await single_state_cases(ctx, state)

        if not sent:
            sent = await single_country_cases(ctx, state)

        if not sent:
            await ctx.send('Unknown Location')


def setup(client):
    client.add_cog(Covid(client))


requests_cache.install_cache('covid_cache', expire_after=3600)


def update_covid_json():
    url = "https://covid-api.mmediagroup.fr/v1/cases"

    response = requests.request("GET", url)
    json_response = response.json()

    with open('covid.json', 'w', encoding='utf-8') as json_file:
        json.dump(json_response, json_file, ensure_ascii=False, indent=4)


async def all_us_cases(ctx):
    us_json = load_json('US')
    keys = sorted(us_json.keys())  # Sort the JSON elements by name
    embed = discord.Embed()
    index = 0
    for i in keys:
        if i == 'All' or i == 'Recovered':
            continue

        curr = us_json[i]  # Current state
        value = f"Confirmed: {curr.get('confirmed')}\nDeaths: {curr.get('deaths')}"

        embed.add_field(name=i, value=value)
        index += 1
        # Create a new Embed every 12 states
        if i == keys[len(keys) - 1] or index % 12 == 0:
            index = 0
            await ctx.send(embed=embed)
            embed = discord.Embed()


async def single_state_cases(ctx, state: str) -> bool:
    # Get the closest spelling
    maybe = process.extract(state, spellings, limit=1)[0][0]
    got_it = False
    try:
        state = us.states.lookup(state).name
        got_it = True
    except AttributeError:
        pass

    if state is None:
        # await ctx.send('Please enter a valid state')
        return False

    if not got_it:
        state = maybe
    state = state.title()
    try:
        await make_covid_embed('US', state, ctx, state)
        return True
    except AttributeError:
        return False


async def single_country_cases(ctx, country: str) -> bool:
    # Get the closest spelling
    maybe = process.extract(country, spellings, limit=1)[0][0].lower()
    if country.lower() in usa or maybe in usa:
        country = 'US'
    else:
        country = maybe
        country = country.title()

    try:
        await make_covid_embed(country, 'All', ctx, country)
        return True
    except AttributeError:
        return False


async def make_covid_embed(country, get, ctx, title):
    js = load_json(country).get(get)
    embed = discord.Embed(
        title=title
    )
    embed.add_field(name='Confirmed', value=js.get('confirmed'))
    embed.add_field(name='Deaths', value=js.get('deaths'))
    if js.get('updated') is not None:
        embed.set_footer(text=js.get('updated'))
    await ctx.send(embed=embed)


def make_spellings():
    global usa, spellings
    usa = ['usa', 'us', 'america', 'united states', 'united states of america', 'merica', '\'merica']
    with open('./covid.json') as f:
        j = json.load(f)
    spellings = list(j.keys())
    spellings.extend(list(j.get('US').keys()))
    spellings.extend(usa)
    spellings = list(map(lambda x: x.lower(), spellings))


update_covid_json()
