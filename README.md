# Lazy Artist Project

artist bot that create images autonomously

This is a modification and implementation of a script from Kristian from https://www.youtube.com/c/AllAboutAI kris@allabtai.com

you should have an .env file in the path up to this repository. the .env should be like this

# -------------------------------------------------------------------------------------------------
# define which image generator to use, could be: stability.ai, stablediffusion, automatic, dall-e
IMAGE_GENERATOR_TYPE=stability.ai
# stable diffusion should already been started
STABLEDIFFUSION_PORT=your stable diffusion port goes here
# you can also use automatic, should already been started
STABLEDIFFUSION_HOST=http://127.0.0.1:
AUTOMATIC_PORT=7860
AUTOMATIC_HOST=http://127.0.0.1:
# stabilityai
STABILITY_HOST=grpc.stability.ai:
STABILITY_PORT=443
STABILITY_API_KEY= you stabilityai key goes here
# Dall-e not yet implemented
DALL_E_PORT=dall-e_port_here
DALL_E_HOST=dall-e_host_here
# openai
OPENAI_API_KEY=your openai key goes here
CHAT_MODEL=gpt-3.5-turbo-16k
# tts
TEXT_TO_SPEECH_TYPE=azure
AZURE_SPEECH_API_KEY=your azure key goes here
AZURE_SPEECH_ENDPOINT= your endpoint for azure speech goes here
AZURE_SPEECH_REGION= your azure region goes here
ELEVEN_API_KEY=your elevenlabs key goes here
# ----------------------------------------------------------------------------------------------------


it's still a working in progress, if you find bugs please let me know

there are many things I want to add or change

1. options to change image generator model (for now stabilityai and local Stable Diffusion) I want to add more
2. options to change the TTS model (for now Azure and elevenlabs) I want to add AWS and an open source python library
3. options to change the LLM model (for now openai) I want to add local free model and other online LLM
4. make the gui responsive
5. use Langchain framework
6. rengineering all

   if someone want to contribute feel free to contact me at info@robertoscordino.it
