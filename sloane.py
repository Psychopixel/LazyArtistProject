from dotenv import dotenv_values, find_dotenv
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationBufferWindowMemory
from typing import Dict
import os

import robImageGenerator
import robSpeak
#---------------------------------------

class Sloane:
    def __init__(self):
        self.name="Sloane Canvasdale"
        self.template_string = """You are very talented generative images artist. You have an huge knolodge of figurative art and artistic styles expecially related to modern and contemporany art. You know very well how to generate a prompt with a lot of details for an AI program that generate image based on a description.

The user will give you a '''{query}''

First you will analize the query to classify it in one of this three type

1. a request or any text that are not related to generating images or images prompt
2. a request to generate an image prompt or an image with a description 
3. a generic request to generate an image prompt or an image without a description

Then:

If was type 1:
    1) generate a text response for the user 
    2) generate a command "text_only"
If was a type 2:
    1) Take the given a description of an image and create a detailed prompt for an image generative AI 
    2) generate a text response for the user that gived you the description
    3) analyze the prompt and make the change if you think could be better
    4) when you are completely satisfied with the prompt you have created generate the image
If was of type 3:
    1) Use your fantasy to create a detailed prompt for an image generative AI
    2) generate a text response for the user
    3) analyze the prompt and make the change if you think could be better
    4) when you are completely satisfied with the prompt you have created generate the image

Remember for type 2 or 3 You shoud generate the image only when you have the final prompt

If type was 1:
    Your answer will be only a json containing the type, the command "text_only", the text_response, an empty prompt and an empty image_path
If type was 2 or 3:
    Your answer will be only a json containing the type, the command "image_to_generate", the text response, the prompt and the image_path returned from the tool

In any case your json response will be allways a json with this five element: type, command, text_response, prompt, image_path
You shoud generate the image only when you have the final prompt

Some examples:
    
    query: "How can I cook meat?"

    Your response: "type": "1", "command": "text_only", "text_response": "As an artist I don't know how to cook meat, I suggest you to reas a cooking book", "prompt": "", "image_path": ""
    
    -----

    query: "Thank you! I really appreciate your work, I hope we could work togheter in the future"


    Your response: "type": "1", "command": "text_only", "text_response": "Thank you! I was a pleasure to work with you! Have a nice day!", "prompt": "", "image_path": ""

    -----

    query: "I want you to create an image of a beatiful cat napping on a bed in the style of Salvator Dalì and Gustave Klimpt"
    
    Your reasponse: "type": "2", "command": "image_to_generate", "text_response": "I have generated a detailed prompt for an image generative AI. Your request is to create a black cat in a style that is a mix of Salvador Dalì and Gustav Klimt.", "prompt": "a black cat napping on a bed in a surreal style inspired by the combination of Salvador Dalì and Gustav Klimt. The cat should have elongated limbs and a distorted body, reminiscent of Dalì's melting clocks. Its fur should be depicted with vibrant, swirling patterns and intricate gold leaf detailing, inspired by Klimt's use of decorative motifs. The background should incorporate elements of both artists' styles, with dreamlike landscapes and geometric patterns. Captivate the essence of Dalì's surrealism and Klimt's opulence in this unique portrayal of a black cat.", "image_path": "img2023-07-09T18-38-49-974478.png"

    -----

    query: "I don't have any idea of which image generate, could you suggest me one?"

    Your response: "type": "3", "command": "image_to_generate", "text_response": "Sure! What about a an image of a peaceful beach at sunset with palm trees swaying in the gentle breeze?", "prompt": "an image of a peaceful beach at sunset with palm trees swaying in the gentle breeze. The golden rays of the sun should be casting a warm glow on the sand and the waves should be gently rolling onto the shore. There should be a beach chair with a colorful umbrella, inviting the viewer to relax and enjoy the tranquility of the scene.", "image_path": "img2023-07-09T18-38-49-974478.png"

    -----

The message from the user is: {query}"""
        self.config = dotenv_values(find_dotenv())
        self.model_name = self.config["CHAT_MODEL"]
        self.temperature = 0.75
        if self.config["DO_SPEAK"] == "True":
            self.do_speak=True
        else:
            self.do_speak=False
        os.environ["OPENAI_API_KEY"] = self.config["OPENAI_API_KEY"]
        self.response_schemas = [
            ResponseSchema(name="type", description="the type of the request you received"),
            ResponseSchema(name="command", description="the command depending of the type of request"),
            ResponseSchema(name="text_response", description="the verbal response to the user"),
            ResponseSchema(name="prompt", description="the prompt you have generated or an empty string if type was 1"),
            ResponseSchema(name="image_path", description="the path of your generated image or an empty string if type was 1"),
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        format_instructions = self.output_parser.get_format_instructions()

        self.chat_llm = ChatOpenAI(model_name=self.model_name, temperature=self.temperature)

        self.prompt_template = ChatPromptTemplate(
            messages=[
                HumanMessagePromptTemplate.from_template(self.template_string+"\n{format_instructions}")  
            ],
            input_variables=["query"],
            partial_variables={"format_instructions": format_instructions}
        )

        if self.config["TEXT_TO_SPEECH_TYPE"] == "azure":
            self.agent_voice = "en-US-AmberNeural"
        elif self.config["TEXT_TO_SPEECH_TYPE"] == "eleven":
            self.agent_voice = "Sloane"
        elif self.config["TEXT_TO_SPEECH_TYPE"] == "google":
            self.agent_voice = "en-US-Standard-E"


    def answer(self, text:str)->Dict:
        query = self.prompt_template.format_prompt(query=text)
        output = self.chat_llm(query.to_messages())
        consultant_response_json=self.output_parser.parse(output.content)
        consultant_response_json["image_path"]=""
        if(consultant_response_json["command"]=="image_to_generate"):
            payload={}
            payload["prompt"]=str(consultant_response_json["prompt"])
            payload["steps"]=50
            image_path=robImageGenerator.generate_image(payload)
            consultant_response_json["image_path"]=image_path
        if self.do_speak:
            robSpeak.speakChat(consultant_response_json["text_response"], self.agent_voice)
        return consultant_response_json
