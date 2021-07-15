import discord
from discord.ext import commands
import asyncio
from pymongo import MongoClient
import json
from textify import Canvas

client = commands.Bot(command_prefix=["t!", "T!"], help_command=None)
mc = MongoClient(json.load(open("tokens.json"))["mongo"])
db = mc["Textify"]
prefs = db["prefs"]

async def send_embed(title, description, ctx, fields=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=0xfa6265
    )
    
    if fields:
        for field in fields:
            i = fields.index(field)
            embed.add_field(name="Description" if i == 0 else ("Library Usage" if i == 1 else "Command usage"), value=field)

    await ctx.send(embed=embed)

def render_from_display(display, width, height, xborder, yborder):
    res = ""

    res += xborder * width + "\n"
    for i in range(height):
        res += yborder + "".join(display[width*i:width*(i+1)])+ yborder + "\n"
    res += xborder * width

    return res

async def query_db(ctx):
    query = prefs.find_one({"_id": ctx.author.id})
    if query == None:
        return await ctx.send("Please run `t!setup` first!")
    
    width = query["width"]
    height = query["height"]
    background_char = query["background_char"]
    
    return (width, height, background_char)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}#{client.user.discriminator}")

@client.command(aliases=["latency"])
async def ping(ctx):
    await send_embed("Latency", f"{round(client.latency * 1000, 2)}ms", ctx)

@client.command()
async def help(ctx, func=None):
    if not func:
        return await send_embed("Please mention a function!", "Correct usage is `t!help <function>`\nAll functions: `render, render_val, rect, addborders, image`.", ctx)

    if func == "render":
        await send_embed("Canvas.render()", "", ctx, [
            "Renders the canvas to screen.",
            "`screen.render()`",
            "`t!render`"
        ])
    elif func == "render_val":
        await send_embed("Canvas.render_val()", "", ctx, [
            "Returns the string representation of the canvas with formatting.",
            "`screen.render_val()`",
            "`t!render_val`"
        ])
    elif func == "rect":
        await send_embed("Canvas.rect(background_char, x, y, width, height, line_width=0, line_width_character=\" \")", "", ctx, [
            "Fills a rectangle at x and y, with a given width and height. Background_char is the fill color",
            "`screen.rect(1, 1, 5, 5)`",
            "`t!rect :blue_square: 1 1 5 5`"
        ])
    elif func in ["border", "addborders"]:
        await send_embed("Canvas.addborders(x_axis, y_axis)", "", ctx, [
            "Creates canvas borders.",
            "`screen.addborders(\"#\", \"#\")`",
            "`t!border / tp!addborders :green_square: :green_square:`"
        ])
    elif func in ["image", "draw_image"]:
        await send_embed("Canvas.draw_image(x, y, image)", "", ctx, [
            "Draws an image on the canvas at x and y. Takes a 2D array as input.",
            "`screen.draw_image(2, 3, [['#', 'O', '#'], ['/', '|', '\\'], ['/', '#', '\\']])`",
            "`t!image / tp!draw_image 2 3 [['🟥', '😳', '🟥'], ['↙', '⬇', '↘'], ['↙', '🟥', '↘']]`"
        ])
    else:
        await send_embed("Invalid argument!", "Please enter an existing function. Do `t!help` to see all functions.", ctx)

@client.command()
async def setup(ctx):
    def check(message):
        return message.channel == ctx.channel and message.author == ctx.author

    try:
        await ctx.send("Enter width:")
        width = await client.wait_for("message", timeout=60, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Timed out (you did not respond in time!)")
    else:
        try:
            width = int(width.content)
        except:
            await ctx.send("Width must be an integer!")
    
    try:
        await ctx.send("Enter height:")
        height = await client.wait_for("message", timeout=60, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Timed out (you did not respond in time!)")
    else:
        try:
            height = int(height.content)
        except:
            await ctx.send("Height must be an integer!")

    try:
        await ctx.send("Enter background character (only emojis in the Discord implementation). Type none to default to :red_square:):")
        background_char = await client.wait_for("message", timeout=60, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Timed out (you did not respond in time!)")
    else:
        background_char = background_char.content
        if background_char.lower() == "none":
            background_char = ":red_square:"

    if width * height * len(background_char) > 2000:
        return await ctx.send("Height and width are too big! This is a Discord limitation not in the library. Please run setup again.")

    screen = Canvas(width, height, background_char)

    try:
        prefs.insert_one({"_id": ctx.author.id, "width": width, "height": height, "background_char": background_char, "canvas": screen.display, "xborder": "", "yborder": ""})
    except:
        prefs.update_one({"_id": ctx.author.id}, {"width": width, "height": height, "background_char": background_char, "canvas": screen.display, "xborder": "", "yborder": ""})

    await ctx.send("Finished setup.")

@client.command()
async def render(ctx):
    canvas_args = await query_db(ctx)
    screen = Canvas(*canvas_args)
    xborder = prefs.find_one({"_id": ctx.author.id})["xborder"]
    yborder = prefs.find_one({"_id": ctx.author.id})["yborder"]
    screen.addborders(xborder, yborder)
    await send_embed("Canvas", screen.render_val(), ctx)

@client.command()
async def rect(ctx, *, args=None):
    if args == None:
        return await send_embed("Correct usage", "`t!rect <background_char> <x> <y> <width> <height> [line_width=0] [line_width_character=\" \"]`", ctx)

    canvas_args = await query_db(ctx)
    screen = Canvas(*canvas_args)

    args = args.split()
    if len(args) not in [5, 7]:
        return await send_embed("Invalid arguments", "Please run `t!help rect` or `t!rect` for correct usage.", ctx)
    
    try:
        args[1:] = list(map(lambda x: int(x), args[1:]))
    except:
        return await send_embed("Wrong type!", "Please check if x, y, width and height are all integers.", ctx)
    
    screen.rect(*args)
    await send_embed("Canvas", screen.render_val(), ctx)
    
    prefs.update_one({"_id": ctx.author.id}, {"$set": {"canvas": screen.display}})

@client.command(aliases=["addborders"])
async def border(ctx, xborder=None, yborder=None):
    if None in [xborder, yborder]:
        xborder = ""
        yborder = ""
    try:
        prefs.update_one({"_id": ctx.author.id}, {"$set": {"xborder": xborder}})
        prefs.update_one({"_id": ctx.author.id}, {"$set": {"yborder": yborder}})
        await ctx.send(f"Borders {'re'if''in[xborder, yborder]else''}set!")
    except:
        await ctx.send("Run `t!setup` first!")

@client.command()
async def render_val(ctx):
    canvas_args = await query_db(ctx)
    screen = Canvas(*canvas_args)
    xborder = prefs.find_one({"_id": ctx.author.id})["xborder"]
    yborder = prefs.find_one({"_id": ctx.author.id})["yborder"]
    screen.addborders(xborder, yborder)
    await ctx.send(f"`{screen.render_val()}`")

@client.command(aliases=["draw_image"])
async def image(ctx, *, args=None):
    if args == None:
        return await send_embed("Invalid args", "Correct usage: `t!image <x> <y> <img>`", ctx)

    args = args.split()
    try:
        x = int(args[0])
        y = int(args[1])
    except:
        return await send_embed("Invalid type", "X and Y must be integers.", ctx)
    
    img = "".join(args[2:])
    if "." in img:
        return await ctx.send("`.` is not allowed in images to prevent eval abuse.")
    
    canvas_args = await query_db(ctx)
    screen = Canvas(*canvas_args)

    screen.draw_image(x, y, eval(img))
    await send_embed("Canvas", screen.render_val(), ctx)

@client.command()
async def clear(ctx):
    prefs.delete_one({"_id": ctx.author.id})
    await ctx.send("Cleared preferences. You can run `t!setup` again.")

client.run(json.load(open("tokens.json"))["bot"])