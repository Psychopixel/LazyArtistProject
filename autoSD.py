import PySimpleGUI as sg
from io import BytesIO
import io
import os
from PIL import Image
import requests, json
import openai
import time
import sys
import requests
from PIL import PngImagePlugin
from colorama import Fore, Style, init
import datetime
import base64
import json
from PIL import Image, PngImagePlugin
from contextlib import contextmanager
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechConfig
from dotenv import dotenv_values
from threading import Timer
from stability_sdk import client as st_client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as stability_generation
import warnings
import random 


DEBUG=True

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


# no terminal output
@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

def dprint(text:str):
    if DEBUG:
        print(text)

# Define a function to open a file and return its contents as a string
def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

# Define a function to save content to a file
def save_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as outfile:
        outfile.write(content)

#define a function to remove a file
def remove_file(filepath):
    try:
        os.remove(filepath)
        dprint("Il file è stato cancellato con successo.")
    except FileNotFoundError:
        dprint("Errore: Il file "+filepath+" non è stato trovato.")
    except PermissionError:
        dprint("Errore: Non hai i permessi per cancellare il file " + filepath)
    except Exception as e:
        dprint("Errore: Si è verificato un errore:", e)


def image_to_data(im):
    with BytesIO() as output:
        im.save(output, format="PNG")
        data = output.getvalue()
    return data

def get_data(imgURL):
    imageURL = json.loads(requests.get(imgURL).content)["url"]
    data = requests.get(imageURL).content
    stream = BytesIO(data)
    img = Image.open(stream)
    giy = image_to_data(img)
    return giy

def load_image(current_image_number=0):
    if len(images_list) > 0:
        dprint(images_list[current_image]["url"])
        if os.path.exists("images\\"+images_list[current_image_number]["url"]):
            image = Image.open("images\\"+images_list[current_image_number]["url"])
            bio = io.BytesIO()
            image.save(bio, format="PNG")
            window['-CURRENT_IMAGE-'].update(data=bio.getvalue())
            window['-CAPTION-'].update(images_list[current_image_number]["caption"])
            window.refresh()
            return
        else:
            dprint("Image " + images_list[current_image_number]["url"] + " not found")
    else:
        image = Image.open("gui/black.png")
        bio = io.BytesIO()
        image.save(bio, format="PNG")
        window['-CURRENT_IMAGE-'].update(data=bio.getvalue())
        window['-CAPTION-'].update("")
        window.refresh()

def show_loader(key):
    window[key].update(source="gui/ajax-loader.gif")
    window.refresh()

def show_empty(key):
    window[key].update(source="gui/ajax-loader-empty.gif")
    window.refresh()
    
# Define a function to make an API call to the OpenAI ChatCompletion endpoint
def chatgpt(conversation, chatbot, user_input, temperature=0.75, frequency_penalty=0.2, presence_penalty=0):

    # Update conversation by appending the user's input
    conversation.append({"role": "user","content": user_input})

    # Insert prompt into message history
    messages_input = conversation.copy()
    prompt = [{"role": "system", "content": chatbot}]
    messages_input.insert(0, prompt[0])

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        messages=messages_input)

    # Extract the chatbot's response from the API response
    chat_response = completion['choices'][0]['message']['content']

    # Update conversation by appending the chatbot's response
    conversation.append({"role": "assistant", "content": chat_response})

    # Return the chatbot's response
    return chat_response

# Define a function to generate images using the Stable Diffusion API    
def generate_image(payload):
    d = datetime.datetime.now()
    ds = d.isoformat().replace(':','-').replace('.','-')
    image_filename = 'img'+ds+'.png'
    pnginfo = PngImagePlugin.PngInfo()
    config = dotenv_values(".env")
    image_generator = config["IMAGE_GENERATOR_TYPE"]
    if(image_generator == "stablediffusion" or image_generator == "automatic"):
        response = requests.post(url=f'{image_generator_url}/sdapi/v1/txt2img', json=payload)
        r = response.json()
        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))
        for i in r['images']:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

            png_payload = {
                "image": "data:image/png;base64," + i
            }
            response2 = requests.post(url=f'{image_generator_url}/sdapi/v1/png-info', json=png_payload) 
            pnginfo.add_text("parameters", response2.json().get("info"))
            image.save("images\\"+image_filename, pnginfo=pnginfo)
            generate_thumbnail(image_filename)
            images_list.append({"url":image_filename, "caption":payload["prompt"]})
            current_image = len(images_list)-1
            load_image(current_image)
            return image_filename
    elif (image_generator == "stability.ai"):
            # Set up our initial generation parameters.
            os.environ['STABILITY_HOST'] = image_generator_url
            seed = random.randint(1,999999999)
            answers = stability_api.generate(
                prompt=payload["prompt"],
                seed=seed , # If a seed is provided, the resulting generated image will be deterministic.
                                # What this means is that as long as all generation parameters remain the same, you can always recall the same image simply by generating it again.
                                # Note: This isn't quite the case for CLIP Guided generations, which we tackle in the CLIP Guidance documentation.
                steps=payload["steps"], # Amount of inference steps performed on image generation. Defaults to 30.
                cfg_scale=8.0, # Influences how strongly your generation is guided to match your prompt.
                            # Setting this value higher increases the strength in which it tries to match your prompt.
                            # Defaults to 7.0 if not specified.
                width=512, # Generation width, defaults to 512 if not included.
                height=512, # Generation height, defaults to 512 if not included.
                samples=1, # Number of images to generate, defaults to 1 if not included.
                sampler=stability_generation.SAMPLER_K_DPMPP_2M # Choose which sampler we want to denoise our generation with.
                                                            # Defaults to k_dpmpp_2m if not specified. Clip Guidance only supports ancestral samplers.
                                                            # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
            )
            # Set up our warning to print to the console if the adult content classifier is tripped.
            # If adult content classifier is not tripped, save generated images.
            for resp in answers:
                for artifact in resp.artifacts:
                    if artifact.finish_reason == stability_generation.FILTER:
                        warnings.warn(
                            "Your request activated the API's safety filters and could not be processed."
                            "Please modify the prompt and try again.")
                    if artifact.type == stability_generation.ARTIFACT_IMAGE:
                        image = Image.open(io.BytesIO(artifact.binary))
                        parameters = {}
                        parameters["seed"] = seed
                        parameters["Sampler"] = stability_generation.SAMPLER_K_DPMPP_2M
                        parameters["CFG Scale"] = "8.0"
                        parameters["size"] = "512x512"
                        parameters["model hash"] = ""
                        pnginfo.add_text("parameters", str(parameters))
                        image.save("images\\"+image_filename, pnginfo=pnginfo)
                        generate_thumbnail(image_filename)
                        images_list.append({"url":image_filename, "caption":payload["prompt"]})
                        current_image = len(images_list)-1
                        load_image(current_image)
                        return image_filename
    else:
        return ""

                
        

def generate_thumbnail(image_filename):
    size = 65, 65
    with Image.open('images\\'+image_filename) as im:
        im.thumbnail(size)
        im.save("images\\thumbs\\"+image_filename , "PNG")

    
# Define a function to print text in green if it contains certain keywords
def print_colored(agent, text):
    agent_colors = {
        "Mona Graffiti": Fore.YELLOW,
        "Sloane Canvasdale": Fore.CYAN,
    }

    color = agent_colors.get(agent, "")
    print(color + f"{agent}: {text}" + Style.RESET_ALL, end="") 

def simulate_typing(text,  color, chunk_size=5, delay=0.03):
    global running
    for i in range(0, len(text), chunk_size):
        if not running:
            break
        chunk = text[i:i+chunk_size]
        window['-AGENT-CHATLOG-'].print(chunk, text_color=color, end='')
        window['-AGENT-CHATLOG-'].update()
        time.sleep(delay)
        
    if running:
        window['-AGENT-CHATLOG-'].print('\n', text_color=color, end='')


def updateScreen(chat):
    global running
    global current_image
    if running:
        lastMsg = chat[len(chat)-1]
        if lastMsg["agent"] == "Sloane Canvasdale":
            simulate_typing(lastMsg["text"], 'yellow', chunk_size=5, delay=0.02)
        if lastMsg["agent"] == "Mona Graffiti":
            simulate_typing(lastMsg["text"], 'cyan', chunk_size=5, delay=0.02)
        window['-AGENT-CHATLOG-'].update()

def print_png_params(filename):
    with open(filename, 'rb') as f:
        img = PngImagePlugin.PngImageFile(f)
        if img.format == 'PNG':
            parameter = img.text
            prompt = parameter['parameters']
            dprint(f'Parameters: {img.text}')
            dprint ("prompt: "+ prompt)
            return prompt
        else:
            print(f'{filename} is not a PNG image')
            return ''

def initAzureVoice():
    # Creates an instance of a speech config with specified subscription key and service region.
    # Replace with your own subscription key and service region (e.g., "westus").
    
    os.environ["COGNITIVE_SERVICE_KEY"]=config["AZURE_ISABELLA_KEY"]
    speech_key, service_region = config["AZURE_ISABELLA_KEY"], config["AZURE_SPEECH_REGION"]
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    # Creates a speech synthesizer using the default speaker as audio output.
    
    return speech_config


def speakAzure(speech_config:SpeechConfig, text:str="",voice:str="en-GB-OliviaNeural")->bool:
    # Set the voice name, refer to https://aka.ms/speech/voices/neural for full list.
    global speech_synthesizer
    speech_config.speech_synthesis_voice_name = voice
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    result= speech_synthesizer.speak_text_async(text).get()
    # Checks result.
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        dprint("Speech synthesized to speaker for text [{}]".format(text))
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        dprint("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                dprint("Error details: {}".format(cancellation_details.error_details))
        dprint("WTF?")
        return False

def stopSpeakAzure():
    global speech_synthesizer
    if speech_synthesizer != "":
        speech_synthesizer.stop_speaking()

#logica di funzionamento del programma
def logic():
    global config
    global images_list
    global current_image
    global image_generator_url
    global running
    global chat
    global talking
    global wbApi
    global stability_api
    global speech_config
    global speech_synthesizer
    speech_synthesizer = ""

    if running:
        return
    else:
        running = True
    global speech_config
    speech_config = initAzureVoice()
    
    images_list=[]
    specific_word = "Steps:"
    dir1 = './images'
    dir2 = './images/thumbs'

    dir1_files = os.listdir(dir1)
    for file in dir1_files:
        if file.endswith('.png'):
            imgPath = dir1 + '/' + str(file)
            dprint(imgPath)
            input_text = print_png_params(imgPath)
            caption=''
            if specific_word in input_text:
                steps_index = input_text.index(specific_word)
                caption = input_text[:steps_index].rstrip()
            else:
                dprint("No match found.")
            parameters = {"url":str(file), "caption":caption}
            dprint(str(parameters))
            images_list.append(parameters)
            dprint ('--------------------------------------')
    current_image = 0
    load_image()
    config = dotenv_values(".env")
    image_generator_type = config["IMAGE_GENERATOR_TYPE"]
    match image_generator_type:
        case "stability.ai":
            port = config["STABILITY_PORT"]
            host = config["STABILITY_HOST"]
            image_generator_key = config["STABILITY_API_KEY"]
            # Set up our connection to the API.
            stability_api = st_client.StabilityInference(
                key=image_generator_key, # API Key reference.
                verbose=True, # Print debug messages.
                engine="stable-diffusion-xl-beta-v2-2-2", # Set the engine to use for generation.
                # Available engines: stable-diffusion-v1 stable-diffusion-v1-5 stable-diffusion-512-v2-0 stable-diffusion-768-v2-0
                # stable-diffusion-512-v2-1 stable-diffusion-768-v2-1 stable-diffusion-xl-beta-v2-2-2 stable-inpainting-v1-0 stable-inpainting-512-v2-0
            )
        case "stablediffusion":
            port = config["STABLEDIFFUSION_PORT"]
            host = config["STABLEDIFFUSION_HOST"]
            image_generator_key = ""
        case "automatic":
            port = config["AUTOMATIC_PORT"]
            host = config["AUTOMATIC_HOST"]
            image_generator_key = ""
        case "dall-e":
            port = config["DALL_E_PORT"]
            host = config["DALL_E_HOST"]
            image_generator_key = ""
        case _:
            print ("ERROR: NOT RECOGNISED IMAGE GENERATOR, USE STABILITY:AI")
            port = config["STABILITY_PORT"]
            host = config["STABILITY_HOST"]
            image_generator_key = config["STABILITY_API_KEY"]

    # url dell'image generator - Stable diffusion e Automatic devon essere già attivi
    image_generator_url = host + port
    
    # Initialize two empty lists to store the conversations for each chatbot
    conversation1 = []
    conversation2 = []

    agent069_voice = "en-GB-OliviaNeural"
    agent007_voice = "en-US-AmberNeural"

    num_image_desired = 10  # Number of images to be created (you can adjust this value)

    # Read the content of the files containing the chatbots' prompts
    chatbot1 = open_file('bot/Agent007_bot.txt')
    chatbot1.replace('<<NUM_IMAGES>>', str(num_image_desired))
    chatbot2 = open_file('bot/Agent069_bot.txt')

    #cancello un eventuale precedente log
    remove_file("bot/ChatLog.txt")

    #list containg the conversation
    chat=[]

    # Start the conversation with ChatBot1's first message
    user_message = "Hello Sloane Canvasdale, I am Mona Graffiti. How can i help you?"
    talking = "Mona Graffiti"
    try:
        image_path=''
        image_prompt=''
        # Update the loop where chatbots talk to each other
        while running:
            window.refresh()
            voicetext = ''
            voicetext = user_message
            voicetext = voicetext.replace('Response:', '')
            voicetext = voicetext.replace('this for me?', 'this for me ?')
            if voicetext != '':
                print_colored("Mona Graffiti", f"{voicetext}\n\n")
                chat_row ={"agent":"Mona Graffiti", "text":voicetext+"\n", "url":'', "prompt":''}
                chat.append(chat_row)
                if running:
                    updateScreen(chat)
                    result = speakAzure(speech_config, voicetext, agent069_voice)
                voicetext = ''
                talking = 'Sloane Canvasdale'
            response = chatgpt(conversation1, chatbot1, user_message)
            user_message = response
            voicetext = str(user_message)
            voicetext = voicetext.replace('Response:', '')
            if voicetext != '':
                voicetext = voicetext.replace('Image: generate_image:', ' ')
                voicetext = voicetext.replace('Response:', '')
                print_colored("Sloane Canvasdale", f"{voicetext}\n\n")
                chat_row ={"agent":"Sloane Canvasdale", "text":voicetext+"\n", "url":image_path, "prompt":image_prompt}
                chat.append(chat_row)
                if running:
                    updateScreen(chat)
                    result = speakAzure(speech_config, voicetext, agent007_voice)
                talking = 'Mona Graffiti'
                window.refresh()
                image_path=''
                image_prompt=''
                if "generate_image:" in user_message:
                    image_prompt = user_message.split("generate_image:")[1].strip()
                    payload = {   
                    }
                    payload['prompt'] = image_prompt
                    payload['steps'] = 50
                    image_path = generate_image(payload)
                    voicetext = ''
                
            

            response = chatgpt(conversation2, chatbot2, user_message)
            user_message = response

            # if Goodbye in message exit   
            if "Goodbye" in user_message:
                voicetext = ''
                if voicetext != '':
                    print_colored("Mona Graffiti", f"{voicetext}\n\n")
                    chat_row ={"agent":"Mona Graffiti", "text":voicetext, "url":'', "prompt":''}
                    chat.append(chat_row)
                    if running:
                        updateScreen(chat)
                        result = speakAzure(speech_config, voicetext, agent069_voice)
                    voicetext = ''
                    talking = ''
                    window.refresh()
                    running = False
                    break
    finally:
        rt.stop()
    rt.stop()

def beforeExit():
    save_file("bot/ChatLog.txt", str(chat))

def closeProgram():
    global loop
    global running
    loop = False
    running = False
    stopSpeakAzure()
    try:
        rt.stop() # better in a try/finally block to make sure the program ends!
    finally:
        rt.stop()
    beforeExit()
    window.close()

#--------------------------------------------

#sg.theme_previewer()
sg.theme('DarkGrey15')

header_row = [[sg.Image(source="gui/logoRobertoScordinoTrasparenteScrittaBianca-150x150.png", pad=(10,10)),sg.Text('Roberto Scordino', font=('Arial 15')),
               sg.Push()], [sg.Push(), sg.Text('The Lazy Artist Project', pad=30, text_color="#ebb806"), sg.Push()]]
img_column =[[sg.Push(),sg.Image(source="gui/prev.png", pad=(30), key="-PREV-", enable_events=True), sg.Image(source="gui/black.png", key="-CURRENT_IMAGE-"),
              sg.Image(source="gui/next.png", pad=(30),key="-NEXT-", enable_events=True),sg.Push()],
             [sg.Push(),sg.Text('', size=(80,10), key="-CAPTION-", font=('Arial 10'), border_width=2, relief=sg.RELIEF_GROOVE, pad=10),sg.Push()]]

agent069_column = [[sg.Image(source="gui/Agent069.png", size=(512,512), subsample=2, pad=(30,15)),sg.Push()],[sg.Push(),sg.Text('Mona Graffiti', font=('Arial 15'), text_color="#00ffff"),sg.Push()], [sg.Push(),sg.Image(source="gui/ajax-loader-empty.gif", pad=5, key="-AGENT069_GIF-", visible = True),sg.Push()]]
agent007_column = [[sg.Push(),sg.Image(source="gui/Agent007.png", size=(512,512), subsample=2, pad=(30,15))],[sg.Push(),sg.Text('Sloane Canvasdale', font=('Arial 15'), text_color="#ffff00"),sg.Push()], [sg.Push(),sg.Image(source="gui/ajax-loader-empty.gif", pad=5, key="-AGENT007_GIF-", visible = True),sg.Push()]]
global talking
agent_chat_column = [[sg.Push(),sg.Text('AGENTS CHAT LOG', font=('Arial 17'), text_color="#ebb806", pad = 10),sg.Push()],
                     [sg.Push(),sg.Multiline(font=('Arial, 10'),size=(200,15),autoscroll = True, 	disabled=True, write_only=True, key="-AGENT-CHATLOG-"),sg.Push()]]

layout = [  header_row, [sg.Column(agent069_column),sg.Push(),sg.Column(img_column),sg.Push(),sg.Column(agent007_column)], agent_chat_column,
            [sg.Push(),sg.Button('Exit', pad=30)] ]

#window = sg.Window('The Lazy Artist Project', layout, no_titlebar=True, grab_anywhere=True)
window = sg.Window('The Lazy Artist Project', layout, grab_anywhere=False, no_titlebar=True, margins=(0, 0), element_padding=(0, 0), location=(0,0), size=(sg.Window.get_screen_size()),
                   keep_on_top=False, font='_ 25', finalize=True, return_keyboard_events=True)
window.bind("<Control-KeyPress-Delete>", "CTRL-Delete")
window.bind("<Control-KeyPress-period>", "CTRL-Delete")

window['-AGENT-CHATLOG-'].Widget.configure(cursor = None)
window['-AGENT-CHATLOG-'].Widget.configure(padx=5, pady=5)
window['-CAPTION-'].Widget.configure(cursor = None)
window['-CAPTION-'].Widget.configure(padx=5, pady=5)
window['-CURRENT_IMAGE-'].Widget.configure(borderwidth=2)
window['-CURRENT_IMAGE-'].Widget.configure(relief=sg.RELIEF_GROOVE)


absolutepath = os.path.abspath(__file__)
fileDirectory = os.path.dirname(absolutepath)
#Path of parent directory
parentDirectory = os.path.dirname(fileDirectory)
#Navigate to Strings directory
newPath = os.path.join(parentDirectory, 'keys')   

config = dotenv_values(".env")
openai.api_key = config["OPENAI_API_KEY"]


# Initialize colorama
init()

running = False
rt = RepeatedTimer(1, logic) # it auto-starts, no need of rt.start()

loop = True
talking = ''

while loop:  # Event Loop
    event, values = window.read(timeout=100)
    if talking == "Sloane Canvasdale":
        show_empty('-AGENT069_GIF-')
        show_loader('-AGENT007_GIF-')
        window['-AGENT007_GIF-'].UpdateAnimation("gui/ajax-loader.gif",time_between_frames=100)
    if talking == "Mona Graffiti":
        show_empty('-AGENT007_GIF-')
        show_loader('-AGENT069_GIF-')
        window['-AGENT069_GIF-'].UpdateAnimation("gui/ajax-loader.gif",time_between_frames=100)
    if event == sg.WIN_CLOSED:
        loop = False
        break
    elif event != "__TIMEOUT__":
        if event in (sg.WIN_CLOSED, 'Exit'):
            loop = False
            break
        elif event == sg.WIN_CLOSED or event == 'Exit':
            loop = False
            break
        elif event == 'Escape:27':
            loop = False
            break
        elif event == 'CTRL-Delete':
            loop = False
            break
    if not loop:
        break
    if event == 'Word':
        window['-AGENT-CHATLOG-'].widget.config(wrap='word')
    elif event == 'None':
        window['-AGENT-CHATLOG-'].widget.config(wrap='none')
    
    if event == "-PREV-":
        if current_image>0:
            current_image-=1
        else:
            current_image = len(images_list)-1
        load_image(current_image)    

    if event == "-NEXT-":
        if current_image<=len(images_list)-2:
            current_image += 1
        else:
            current_image=0
        load_image(current_image)
closeProgram()