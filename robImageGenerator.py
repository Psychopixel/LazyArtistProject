version="<!#FV> 0.0.0 </#FV>"
from PIL import Image, PngImagePlugin
import requests, json
from dotenv import dotenv_values, find_dotenv
from io import BytesIO
import io
from PIL import PngImagePlugin
import datetime
import base64
import os
import random
import sys
from stability_sdk import client as st_client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as stability_generation
import warnings

def init():
    global stability_api
    global image_generator_url
    global config
    if (find_dotenv()==""):
        print("File Configurazione mancante")
        sys.exit(1)
    config = dotenv_values(find_dotenv())
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

# Define a function to generate images using the Stable Diffusion API    
def generate_image(payload):
    global stability_api
    global image_generator_url
    global config
    init()
    d = datetime.datetime.now()
    ds = d.isoformat().replace(':','-').replace('.','-')
    image_filename = 'img'+ds+'.png'
    pnginfo = PngImagePlugin.PngInfo()
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
                        parameters["prompt"] = payload["prompt"]
                        parameters["Steps"] = str(payload["steps"])
                        parameters["Sampler"] = "SAMPLER_K_DPMPP_2M"
                        parameters["CFG Scale"] = "8"
                        parameters["Seed"] =str(seed)
                        parameters["Size"] = "512x512"
                        parameters["Model hash"] = "?"
                        parameters["Model"] = "stabilityai"
                        pnginfo.add_text("parameters", str(parameters))
                        image.save("images\\"+image_filename, pnginfo=pnginfo)
                        generate_thumbnail(image_filename)
                        return image_filename
                    
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