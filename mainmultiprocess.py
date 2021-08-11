
# Dependencies used
from concurrent.futures.thread import ThreadPoolExecutor
from discord.embeds import Embed
from discord_webhook import DiscordWebhook, DiscordEmbed
import requests
from favicon import get as getFavicon
import json
#import threading
import psutil
from multiprocessing import Process, process
import asyncio
from time import sleep, perf_counter
#from time import perf_counter #Testing and benchmarking reasons
from random import randint
#from itertools import cycle
from discord.ext import commands, tasks
process_list = {}
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
def send_alert(store, index, obj, variant, mode="Restock"):
    #ChannelID where the alert is going to be sent + storeURL
    channelID = str(store[store.find("|")+1:len(store)])
    
    webhook = DiscordWebhook(url=channelID)
    storeURL = store[0:store.find("|")]
    #alerts_channel = asyncio.run(bot.fetch_channel(channelID))
    productname = obj[index]['title']
    producturl = storeURL.replace(".json", "/" + obj[index]['handle'])
    price = obj[index]['variants'][0]['price']
    print(producturl)
    #Embed set-up for the alert
    embedVar = DiscordEmbed(title=productname, url=producturl)
    embedVar.add_embed_field(name="Type", value=mode)
    embedVar.add_embed_field(name="Price", value=price)
    embedVar.add_embed_field(name="Store", value=storeURL.replace("/products.json", ""))
    surl = storeURL.replace("/products.json", "")
    embedVar.add_embed_field(name="Variant", value=variant)
    embedVar.add_embed_field(name="ATC", value=f"{surl}/cart/{variant}:1")
    #In case the profuct has an image, add it
    try:
        image = obj[index]['images'][0]['src'].replace("\\", "")
        embedVar.set_thumbnail(url=image)
    except Exception:
        pass

    webhook.add_embed(embedVar)
    webhook.execute()


#@tasks.loop(5)
async def hello():
    global process_list
    while True:
        for proc in process_list:
            print(process_list[proc])
            process_list[proc].stop()
            process_list[proc].start()
        await asyncio.sleep(5)

#A command to check if the bot is alive
@bot.command()
async def rm(ctx, index=None):
    if index == None:
        out = ""
        if len(list(process_list)) > 1:
            for index, storename in enumerate(list(process_list)):
                out += f"{index}. {storename} \n"
        else:
            out = "No tasks running"
    elif int(index) <= len(list(process_list))-1:
        index = int(index)
        item = list(process_list)[index]
        psutil.Process(process_list[item].pid).kill()
        process_list.pop(item)
        f = open_file("stores.json")
        for store in f["start"]:
            if item in store:
                f["start"].remove(store)
        out = "Done"
        save_file("stores.json", f)
        
    await ctx.send(out)
@bot.command()
async def stoptasks(ctx):
    for key in process_list:
        psutil.Process(process_list[key].pid).kill()
    await ctx.send(f"{len(process_list)} Has been stopped \n {process_list}")
        

@bot.command()
async def awake(ctx):
	await ctx.send("I'm running!")


#The monitor logic
#@tasks.loop(seconds=10.0)
def monitor(store):
    tries = 0
    banned = []
    session = requests.session()
    proxieslist = []
    rand = randint(0, len(proxieslist) - 1)
    session.proxies = {"https":proxieslist[rand]}
    #Iterating over every store
    url = store[0:store.find("|")]
    #If the access is blocked, just change the proxy
    currentProducts = 0
    while True:
        try:
            currentProducts = json.loads(session.get(url).text)["products"]
            break
        except Exception:
            rand = randint(0, len(proxieslist) - 1)
            currentProducts = 0
            session.proxies = {"https":proxieslist[rand]}
            print("Reach info exception", store)
            #print("Problem!!")
        
    d = {}
    d[store] = currentProducts
    save_file(store.replace("/", "-") + ".json", d)

    while True:
        rand = randint(0, len(proxieslist) - 1)
        start = perf_counter()

#        while rand in banned:
#            print("-----------------------"+str(rand) + "Is already banned ---------------------------")
#            rand = randint(0, len(proxieslist) - 1)
        session.proxies = {"https":proxieslist[rand]}
        

        #print("Current Proxy IP: "+session.get("https://jsonip.com/").json()["ip"])
        stores = open_file(store.replace("/", "-")+".json")
        #Iterating over every store
        url = store[0:store.find("|")]
        print("Analizing store: " + url)
        #If the access is blocked, just change the proxy
        currentProducts = 0
        while currentProducts == 0:
            try:
                currentProducts = json.loads(session.get(url, timeout=10).text)["products"]
                print("Done")
            except Exception:
                currentProducts = 0
                if rand not in banned:
                    #print(str(rand) + "Added to the banned list")
                    banned.append(rand)
                rand = randint(0, len(proxieslist) - 1)
                session.proxies = {"https":proxieslist[rand]}
                #print("Problem!!")

                print("Reach info exception", store)
                #print(session.proxies)
                #print("Changing IP to: "+session.get("https://jsonip.com/").json()["ip"])c
        
	    #Analizing the information
        if stores[store] == currentProducts:
            # Nothing changed in the store, no alerts
            pass
        else:
          #  print("The store's database changed!! Checking for possible restocks..")
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
                                
                                for variant in newProduct['variants']:
                                    try:
                                        oldProduct['variants'].remove(variant)
                                    except Exception:
                                        send_alert(store, index, currentProducts, variant['id'], mode="New Variant")
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
                                                
                                                send_alert(store, index, currentProducts, newVariant['id'])
                                                print(f"{newProduct['title']} restocked")
                                           # elif oldVariant["available"] == True and newVariant["available"] == True and oldVariant["updated_at"] != newVariant["updated_at"]:
                                           #     send_alert(store, index, currentProducts, newVariant['id'], mode="Date Changed")
                                                #break
                    # If the product wasn't found on the old database, means that it is a new product
                    if foundobj == False:
                        for newVariant in newProduct["variants"]:
                            if newVariant["available"] == True:
                                # Send an alert of a new product
                                
                                send_alert(store, index, currentProducts, newVariant['id'], mode="Add")
                                #asyncio.run(send_alert(store, index, currentProducts, newVariant['id'], mode="Add"))
                                print(f"{newProduct['title']} has been added")
                                #break
            #Updating the database
            stores[store] = currentProducts
            save_file(store.replace("/","-") + ".json", stores)
        #The function ends
        print("Time: ", perf_counter() - start)
        tries += 1
        if tries == 600:
            #print(banned)
            banned.pop(0)
            #print(banned)
            tries = 0

        sleep(10)
        
        #print("End of iteration")
        #print(start - perf_counter())



        

@bot.command()
async def add(ctx, store, channelID=""):
    # Check if the syntax used is correct
    global process_list
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
        #stores = stores["start"]

        for storeName in stores["start"]:
            if store in storeName:
                stores["start"].remove(storeName)
                process = psutil.Process(process_list[store].pid)
                process.kill()
                process_list[store] = Process(name=store ,target=monitor, args=(store + "|" + channelID,))
                process_list[store].start()
                print(process_list)
                break
        if store not in process_list:
            process_list[store] = Process(name=store ,target=monitor, args=(store + "|" + channelID,))
            process_list[store].start()
        stores["start"].append(store + "|" + channelID)

        save_file("stores.json", stores)
        await ctx.send(embed=embedVar)
        return 0
    else:
        await ctx.send("Usage: !add <storeURL> <channelID>")




@bot.event
async def on_message(message):
	if message.channel.id in (842269998902149150, 823628505245024258, 637141086334222369):
		await bot.process_commands(message)



@bot.event
async def on_ready():
    global process_list
    #monitor.start()
    with open("stores.json", "r") as f:
        x = json.load(f)
    #x = open_file("stores.json")
    #print(type(x))
    #for store in x["start"]:
    #print(ThreadPoolExecutor().submit(monitor, store="https://owlandgoosegifts.com//products.json|https://discord.com/api/webhooks/841184985679527946/YRDcuaRhoFA2T6gTSLdrfiy40dne6AWWBUzZzHJ2b2fA8Yj-v3H2ECrT1Lxm97NyZNHq"))
    #with ThreadPoolExecutor(max_workers=20) as executor:
    #    l = [executor.submit(monitor, store=storename) for storename in x["start"]]
    

    #l = [threading.Thread(target=monitor, args=(storename,)).start() for storename in x["start"]]
    #for storename in x["start"]:
    #    process_list["storename"] = Process(name=storename[0:storename.find("|")] ,target=monitor, args=(storename,))
    #bot.loop.create_task(hello())
    process_list = {storename[0:storename.find("|")] : Process(name=storename[0:storename.find("|")] ,target=monitor, args=(storename,)) for storename in x["start"]}
    print(process_list)
    for proc in process_list:
        process_list[proc].start()
        
    print(process_list)
    print("Ready")



bot.run(TOKEN)
