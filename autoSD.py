import PySimpleGUI as sg
from io import BytesIO
import io
import os
import re
import json
from PIL import Image
import openai
import time
import sys
from colorama import Fore, Style, init
from PIL import Image, PngImagePlugin
from dotenv import dotenv_values, find_dotenv
from threading import Timer
import robAiUtility
import robSpeak
import psutil
from sloane import Sloane
from mona import Mona

DEBUG=True
DO_SPEAK=True

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

    
def load_image(current_image_number=0):
    directory_separator=os.path.sep
    if len(images_list) > 0:
        dprint(images_list[current_image]["url"])
        if os.path.exists("images"+directory_separator+images_list[current_image_number]["url"]):
            image = Image.open("images"+directory_separator+images_list[current_image_number]["url"])
            bio = io.BytesIO()
            image.save(bio, format="PNG")
            try:
                window['-CURRENT_IMAGE-'].update(data=bio.getvalue())
                window['-CAPTION-'].update(images_list[current_image_number]["caption"])
                window.refresh()
            except:
                pass
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
    model = config["CHAT_MODEL"]
    # Extract the chatbot's response from the API response
    chat_response = robAiUtility.get_completion_from_messages(
        messages=messages_input,
        model=model,
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        max_tokens = 250,
        )
    conversation.append({"role": "assistant", "content": chat_response})

    # Return the chatbot's response
    return chat_response
    
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
    try:
        for i in range(0, len(text), chunk_size):
            if running:
                chunk = text[i:i+chunk_size]
                window['-AGENT-CHATLOG-'].print(chunk, text_color=color, end='')
                window['-AGENT-CHATLOG-'].update()
                time.sleep(delay)
            
        if running:
            window['-AGENT-CHATLOG-'].print('\n', text_color=color, end='')
    except:
        pass
    finally:
        pass

def split_string(input_string):
    split_chars = ["\n", "."]  # Characters to split the string

    # Join the split characters into a regular expression pattern
    pattern = "|".join(map(re.escape, split_chars))

    # Split the input string using the pattern
    split_list = re.split(pattern, input_string)

    # Remove any empty strings from the split list
    split_list = [string for string in split_list if string]

    return split_list

def updateScreen(chat):
    global running
    global current_image
    try:
        if running:
            lastMsg = chat[len(chat)-1]
            if lastMsg["agent"] == "Sloane Canvasdale":
                simulate_typing(lastMsg["text"], 'yellow', chunk_size=5, delay=0.02)
            if lastMsg["agent"] == "Mona Graffiti":
                simulate_typing(lastMsg["text"], 'cyan', chunk_size=5, delay=0.02)
            window['-AGENT-CHATLOG-'].update()
    except:
        pass
# muove la finestra al centro dell schermo
def move_window_center(window):
    screen_width, screen_height = window.get_screen_size()
    win_width, win_height = window.size
    x,y = (screen_width-win_width)/2, (screen_height-win_height)/2
    window.move(x,y)

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


#logica di funzionamento del programma
def logic():
    global config
    global images_list
    global current_image
    global image_generator_url
    global running
    global chat
    global talking
    global stability_api
    global loop

    if config["TEXT_TO_SPEECH_TYPE"] == "azure":
        agent069_voice = "en-GB-OliviaNeural"
        agent007_voice = "en-US-AmberNeural"
    elif config["TEXT_TO_SPEECH_TYPE"] == "eleven":
        agent069_voice = "Mona"
        agent007_voice = "Sloane"
    elif config["TEXT_TO_SPEECH_TYPE"] == "google":
        agent069_voice = "en-US-Standard-C"
        agent007_voice = "en-US-Standard-E"
    

    mona = Mona()
    sloane = Sloane()

    if running:
        return
    else:
        running = True

    
    images_list=[]
    specific_word = "Steps:"
    directory_separator=os.path.sep
    dir1 = 'images'

    dir1_files = os.listdir(dir1)
    for file in dir1_files:
        if file.endswith('.png'):
            imgPath = dir1 + directory_separator + str(file)
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

    #list containg the conversation
    chat=[]
   
    # Start the conversation with ChatBot1's first message
    user_message = "Hello Sloane Canvasdale, I am Mona Graffiti. How can i help you?"
    talking = "Mona Graffiti"
    window.refresh()
    if config["DO_SPEAK"]=="True":
        robSpeak.speakChat(user_message, agent069_voice)
    chat_row ={"agent":"Mona Graffiti", "text":user_message+"\n", "url":'', "prompt":''}
    chat.append(chat_row)
    updateScreen(chat)
    window.refresh()
    mona_answer = {}
    mona_answer["command"]="text_only"
    mona_answer["text_response"]=user_message
    try:
        # Update the loop where chatbots talk to each other
        while running:
            # Sloane
            talking = 'Sloane Canvasdale'
            sloane_answer = sloane.answer(mona_answer["text_response"])
            window.refresh()
            chat_row ={"agent":"Sloane Canvasdale", "text":sloane_answer["text_response"]+"\n", "url":sloane_answer["image_path"], "prompt":sloane_answer["prompt"]}
            if sloane_answer["image_path"]!="":
                images_list.append({"url":sloane_answer["image_path"], "caption":sloane_answer["prompt"]})
                current_image = len(images_list)-1
                load_image(current_image)
            chat.append(chat_row)
            updateScreen(chat)
            window.refresh()
            
            # Mona
            talking = 'Mona Graffiti'
            mona_answer = mona.answer(sloane_answer["text_response"])
            window.refresh()
            chat_row ={"agent":"Mona Graffiti", "text":mona_answer["text_response"]+"\n", "url":"", "prompt":""}
            chat.append(chat_row)
            updateScreen(chat)
            window.refresh()
            if mona_answer["command"]=="goodbye":
                closeProgram()
    finally:
        pass

def beforeExit():
    try:
        save_file("bot/ChatLog.txt", str(chat))
    except:
        pass

def closeProgram():
    global loop
    global running
    loop = False
    running = False
    robSpeak.stopSpeak()
    try:
        rt.stop() # better in a try/finally block to make sure the program ends!
    finally:
        rt.stop()
    beforeExit()
    window.close()
    os._exit(os.EX_OK)

#--------------------------------------------
global config
if (find_dotenv()==""):
    print("File Configurazione mancante")
    sys.exit(1)

config = dotenv_values(find_dotenv())
#sg.theme_previewer()
sg.theme('DarkGrey15')

header_row = [[sg.Image(source="gui/logoRobertoScordinoTrasparenteScrittaBianca-85x93.png", pad=(20,10)),sg.Text('Roberto Scordino', font=('Arial 15')),
               sg.Push()], [sg.Push(), sg.Text('The Lazy Artist Project', pad=0, text_color="#ebb806"), sg.Push()]]
img_column =[[sg.Push(),sg.Image(source="gui/prev.png", pad=(10), key="-PREV-", enable_events=True), sg.Image(source="gui/black.png", key="-CURRENT_IMAGE-", size=(512,512), pad=(0,0)),
              sg.Image(source="gui/next.png", pad=(10),key="-NEXT-", enable_events=True),sg.Push()],
             [sg.Push(),sg.Text('', size=(80,10), key="-CAPTION-", font=('Arial 10'), border_width=2, relief=sg.RELIEF_GROOVE, pad=10),sg.Push()]]
if(psutil.MACOS):
    subSample=3
else:
    subSample=2
agent069_column = [[sg.Image(source="gui/Agent069.png", size=(512,512), subsample=subSample, pad=(10,0)),sg.Push()],[sg.Push(),sg.Text('Mona Graffiti', font=('Arial 15'), text_color="#00ffff"),sg.Push()], [sg.Push(),sg.Image(source="gui/ajax-loader-empty.gif", pad=5, key="-AGENT069_GIF-", visible = True),sg.Push()]]
agent007_column = [[sg.Push(),sg.Image(source="gui/Agent007.png", size=(512,512), subsample=subSample, pad=(10,0))],[sg.Push(),sg.Text('Sloane Canvasdale', font=('Arial 15'), text_color="#ffff00"),sg.Push()], [sg.Push(),sg.Image(source="gui/ajax-loader-empty.gif", pad=5, key="-AGENT007_GIF-", visible = True),sg.Push()]]

agent_chat_column = [[sg.Push(),sg.Text('AGENTS CHAT LOG', font=('Arial 15'), text_color="#ebb806", pad = 5),sg.Push()],
                     [sg.Push(),sg.Multiline(font=('Arial, 10'),size=(170,10),autoscroll = True, disabled=True, write_only=True, key="-AGENT-CHATLOG-"),sg.Push()]]

layout = [  header_row, [sg.Column(agent069_column),sg.Push(),sg.Column(img_column),sg.Push(),sg.Column(agent007_column)], agent_chat_column,
            [sg.Push(),sg.Button('Exit', pad=30)] ]

w,h = sg.Window.get_screen_size()
titleBar = not psutil.MACOS
resizable=psutil.MACOS
window = sg.Window('The Lazy Artist Project', layout, grab_anywhere=False, no_titlebar=titleBar, margins=(0, 0), element_padding=(0, 0), location=(0,0), size=(w,h),
                   keep_on_top=False, font='_ 25', finalize=True, return_keyboard_events=True, resizable=resizable).Finalize()
window.Maximize()
window.bind("<Control-KeyPress-Delete>", "CTRL-Delete")
window.bind("<Control-KeyPress-period>", "CTRL-Delete")

window['-AGENT-CHATLOG-'].Widget.configure(cursor = None)
window['-AGENT-CHATLOG-'].Widget.configure(padx=5, pady=5)
window['-CAPTION-'].Widget.configure(cursor = None)
window['-CAPTION-'].Widget.configure(padx=5, pady=5)
window['-CURRENT_IMAGE-'].Widget.configure(borderwidth=2)
window['-CURRENT_IMAGE-'].Widget.configure(relief=sg.RELIEF_GROOVE)

move_window_center(window)

absolutepath = os.path.abspath(__file__)
fileDirectory = os.path.dirname(absolutepath)
#Path of parent directory
parentDirectory = os.path.dirname(fileDirectory)
#Navigate to Strings directory
newPath = os.path.join(parentDirectory, 'keys')   

openai.api_key = config["OPENAI_API_KEY"]

global talking
# Initialize colorama
init()

robSpeak.init()

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
            closeProgram()
            break
        elif event == sg.WIN_CLOSED or event == 'Exit':
            loop = False
            closeProgram()
            break
        elif event == 'Escape:27':
            loop = False
            closeProgram()
            break
        elif event == 'CTRL-Delete':
            loop = False
            closeProgram()
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

