from dotenv import dotenv_values, find_dotenv
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    PromptTemplate,
)
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import os
import robSpeak
from typing import Dict

#-------------------------------------------------------------
class Mona:
    def __init__(self):
        self.name="Mona Graffiti"
        self.template_string = """Your name is Mona Graffiti. You are an expert art director with 30 years of experience. You are expert of history of art. 
Your preferred artist vary from Liu Wei, Damien Hirst, Keith Haring, Georgia O’Keeffe, Andy Warhol, Tamara de Lempicka, Frida Kahlo and all the best painter in history.
Your friend Sloane Canvasdale can create images when you tell him to. Your task is tell Sloane Canvasdale to create the images you describe to her.
You must describe the image in a very detailed way but try not to exceed 600 characters. Artstyle, artist, lenses, colors, etc.
If you don't know which kind of image you want, ask Sloane to use her fantasy to create an image.

When you don't want more image from Sloane use the command 'goodbay' otherwise use the command 'text_only'

{chat_history}


Your answer must allways be as this
\n{format_instructions}\n

The message from Sloane is: {input}
"""

        self.config = dotenv_values(find_dotenv())
        self.model_name = self.config["CHAT_MODEL"]
        self.temperature = 0.75
        if self.config["DO_SPEAK"] == "True":
            self.do_speak=True
        else:
            self.do_speak=False
        os.environ["OPENAI_API_KEY"] = self.config["OPENAI_API_KEY"]
        self.response_schemas = [
            ResponseSchema(name="command", description="the command that could be 'text_only' or 'goodbye'"),
            ResponseSchema(name="text_response", description="the verbal response"),
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        format_instructions = self.output_parser.get_format_instructions()

        self.chat_llm = ChatOpenAI(model_name=self.model_name, temperature=self.temperature)
        self.memory = ConversationBufferMemory(memory_key="chat_history")

        self.prompt_template = PromptTemplate(
            template=self.template_string+"\n{format_instructions}",
            input_variables=["chat_history", "input"],
            partial_variables={"format_instructions": format_instructions}
        )

        self.conversation = ConversationChain(  
            llm=self.chat_llm,
            verbose=True,
            prompt=self.prompt_template,
            memory=self.memory
        )

        if self.config["TEXT_TO_SPEECH_TYPE"] == "azure":
            self.agent_voice = "en-GB-OliviaNeural"
        elif self.config["TEXT_TO_SPEECH_TYPE"] == "eleven":
            self.agent_voice = "Mona"
        elif self.config["TEXT_TO_SPEECH_TYPE"] == "google":
            self.agent_voice = "en-US-Standard-C"


    def answer(self, text:str)->Dict:
        output = self.conversation.predict(input=text)
        consultant_response_json=self.output_parser.parse(output)
        if self.do_speak:
            robSpeak.speakChat(consultant_response_json["text_response"], self.agent_voice)
        return consultant_response_json
