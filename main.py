
# Dependencies used
from discord.embeds import Embed
import requests
from favicon import get as getFavicon
import json
#from time import perf_counter #Testing and benchmarking reasons
from random import randint
#from itertools import cycle
from discord.ext import commands, tasks

#Discord Bot Information
TOKEN = ""
bot = commands.Bot(command_prefix="!")

# Proxies set up
session = requests.session()
proxieslist = []
#session.proxies = {"https":next(proxieslist)}


# Secondary functions
def save_file(file, out_object):
    with open(file, "w") as f:
        json.dump(out_object, f, indent=4)
def open_file(file):
    with open(str(file), "r") as f:
        data = json.load(f) 
    return data

#Function in charge to send alerts
async def send_alert(store, index, obj, variant, mode="Restock"):
    #ChannelID where the alert is going to be sent + storeURL
    channelID = int(store[store.find("|")+1:len(store)])
    storeURL = store[0:store.find("|")]
    alerts_channel = await bot.fetch_channel(channelID)
    productname = obj[index]['title']
    producturl = storeURL.replace(".json", "/" + obj[index]['handle'])
    price = obj[index]['variants'][0]['price']
    print(producturl)
    #Embed set-up for the alert
    embedVar = Embed(title=productname, url=producturl, color=randint(0, 0xffffff))
    embedVar.add_field(name="Type", value=mode)
    embedVar.add_field(name="Price", value=price)
    embedVar.add_field(name="Store", value=storeURL.replace("/products.json", ""))
    embedVar.add_field(name="Variant", value=variant)
    #In case the profuct has an image, add it
    try:
        image = obj[index]['images'][0]['src'].replace("\\", "")
        embedVar.set_thumbnail(url=image)
    except Exception:
        pass

    await alerts_channel.send(embed=embedVar)

#A command to check if the bot is alive
@bot.command()
async def awake(ctx):
	await ctx.send("I'm running!")


#The monitor logic
@tasks.loop(seconds=10.0)
async def monitor():
    #start = perf_counter()
    session.proxies = {"https":proxieslist[randint(0, len(proxieslist) - 1)]}
    print("Current Proxy IP: "+session.get("https://jsonip.com/").json()["ip"])
    stores = open_file("stores.json")
    #Iterating over every store
    for store in stores:
        url = store[0:store.find("|")]
        print("Analizing store: " + url)
        
        #If the access is blocked, just change the proxy
        currentProducts = 0
        while currentProducts == 0:
            try:
                currentProducts = json.loads(session.get(url).text)["products"]
            except Exception:
                currentProducts = 0
                session.proxies = {"https":proxieslist[randint(0, len(proxieslist) - 1)]}
                print("Reach info exception", store)
                #print("Changing IP to: "+session.get("https://jsonip.com/").json()["ip"])c

		#Analizing the information
        if stores[store] == currentProducts:
            # Nothing changed in the store, no alerts
            pass
        else:
            print("The store's database changed!! Checking for possible restocks..")
            for index, newProduct in enumerate(currentProducts):
                foundobj = False
                # Re-stock check
                if newProduct not in stores[store]:
                    for oldProduct in stores[store]:
                        #Check if the product already was in the database
                        if newProduct["id"] == oldProduct["id"]:
                            foundobj = True
                            if len(newProduct["variants"]) > len(oldProduct["variants"]):
                                #New Variant code UNUSED
                            #    for variant in newProduct['variants']:
                            #        try:
                            #            oldProduct['variants'].remove(variant)
                            #        except Exception:
                            #            await send_alert(store, index, currentProducts, variant['id'], mode="New Variant")

                                print(f"{newProduct['title']} restocked NEW VARIANT")
                                
                            else:
                                #Iterating over new and old products
                                for oldVariant in oldProduct["variants"]: 
                                    for newVariant in newProduct["variants"]:
                                        # Check if it found the correct variant
                                        if oldVariant["id"] == newVariant["id"]:
                                            #The re-stock check
                                            if oldVariant["available"] == False and newVariant["available"] == True:
                                                # The item was restocked, call the alerts function
                                                await send_alert(store, index, currentProducts, newVariant['id'])
                                                #print(f"{newProduct['title']} restocked")
                                                break
                    # If the product wasn't found on the old database, means that it is a new product
                    if foundobj == False:
                        for newVariant in newProduct["variants"]:
                            if newVariant["available"] == True:
                                # Send an alert of a new product
                                await send_alert(store, index, currentProducts, newVariant['id'], mode="Add")
                                #print(f"{newProduct['title']} has been added")
                                break
            #Updating the database
            stores[store] = currentProducts
            save_file("stores.json", stores)
    #The function ends
    print("End of iteration")
    #print(start - perf_counter())



        

@bot.command()
async def add(ctx, store, channelID=""):
    # Check if the syntax used is correct
    if channelID != "":
        temp = store
        #Step needed for future analizing
        if "products.json" not in store:
            store = store + "/products.json"
        else:
            temp = store[0:store.find("products.json")]
        #Try to get the current product list
        try:
            products_data = json.loads(requests.get(store).text)["products"]
            if len(products_data) == 0:
                await ctx.send("This store is not a real store or the URL is invalid, not adding it...")
                return 0
        except Exception:
            await ctx.send("This store is not a real store or the URL is invalid, not adding it...")
            return 0        
        #Embed construction for a correct adding
        embedVar = Embed(title="Store added successfully", color=0x03ff28)
        embedVar.add_field(name="Store", value=temp)
        try:
	        embedVar.set_thumbnail(url=getFavicon(temp)[0].url)
        except Exception:
        	pass
        embedVar.add_field(name="Current products", value=len(products_data))

        #Check for duplicates
        stores = open_file("stores.json")
        for savedstore in stores:
            if store in savedstore:
                stores.pop(savedstore)
                stores[store+"|"+channelID] = products_data
                save_file("stores.json", stores)
                await ctx.send(embed=embedVar)
                return 0

        #Save the information
        stores[store+"|"+channelID] = products_data
        save_file("stores.json", stores)
        await ctx.send(embed=embedVar)
    else:
        await ctx.send("Usage: !add <storeURL> <channelID>")




@bot.event
async def on_message(message):
	if message.channel.id in (842269998902149150, 823628505245024258):
		await bot.process_commands(message)



@bot.event
async def on_ready():
    monitor.start()
    print("Ready")


bot.run(TOKEN)
