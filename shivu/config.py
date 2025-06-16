class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "7717913705"
    sudo_users = "5939547901" ,"5469324918", "7692788302", "7333491739", "7717913705", "6217599045", "7462765208", "7829938546", "7985079418"
    GROUP_ID = -1002004197830
    TOKEN = "7297939280:AAE7i1Y4duGdBtSI_3YfUV1eDIgOxT3NV7E"
    mongo_url = "mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    PHOTO_URL =["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "soon"
    UPDATE_CHAT = "soon"
    BOT_USERNAME = "Pick_Your_Waifu_Bot"
    CHARA_CHANNEL_ID = "-1002568368709"
    api_id = 24074986
    api_hash = "f4f6272a85d0e50e39a24cb378be118d"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
