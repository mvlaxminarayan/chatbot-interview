from dotenv import load_dotenv, find_dotenv
from langchain.llms import HuggingFaceHub, OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import warnings
from typing import List
from langchain import FewShotPromptTemplate


warnings.filterwarnings("ignore")


def llm_inference(
    model_type: str,
    input_variables_list: List[str] = [],
    prompt_template: str = "",
    openai_model_name: str = "",
    hf_repo_id: str = "",
    inference_type : str = "",
    temperature: float = 0.1,
    max_length: int = 64,
    interview_phase: str = ""
) -> str:
    """Call HuggingFace/OpenAI model for inference

    Given a question, prompt_template, and other parameters, this function calls the relevant
    API to fetch LLM inference results.

    Args:
        model_str: Denotes the LLM vendor's name. Can be either 'huggingface' or 'openai'
        input_variables_list: List of the name of input variables for the prompt.
        prompt_template(Optional): A template for the prompt.
        hf_repo_id: The Huggingface model's repo_id.
        inference_type: Two options, first "evaluation" to evaluate answer privided by the candidate, second generate questions
        temperature: (Default: 1.0). Range: Float (0.0-100.0). The temperature of the sampling operation. 1 means regular sampling, 0 means always take the highest score, 100.0 is getting closer to uniform probability.
        max_length: Integer to define the maximum length in tokens of the output summary.

    Returns:
        A Python string which contains the inference result.

    HuggingFace repo_id examples:
        - mistralai/Mistral-7B-Instruct-v0.1
        - google/flan-t5-xxl
        - tiiuae/falcon-7b-instruct


    """
    # Please ensure you have a .env file available with 'HUGGINGFACEHUB_API_TOKEN' and 'OPENAI_API_KEY' values.
    load_dotenv(find_dotenv())
    if inference_type == "evaluation":
      prompt = prompt_template
    else:
      prompt = PromptTemplate(
          template=prompt_template, input_variables=input_variables_list
    )

    if model_type == "openai":
        # https://api.python.langchain.com/en/stable/llms/langchain.llms.openai.OpenAI.html#langchain.llms.openai.OpenAI
        llm = OpenAI(
            model_name=openai_model_name, temperature=temperature, max_tokens=max_length
        )
        llm_chain = LLMChain(prompt=prompt, llm=llm)

        if inference_type == "evaluation":
          return llm_chain.run(
            position = input_variables_list[0],
            question=input_variables_list[1],
            answer=input_variables_list[2],

            )
        else:
            return llm_chain.predict(
                position=input_variables_list[0],
                candidate_profile=input_variables_list[1],
                n_results=input_variables_list[2],
                interview_phase=interview_phase
        )

    elif model_type == "huggingface":
        # https://python.langchain.com/docs/integrations/llms/huggingface_hub
        llm = HuggingFaceHub(
            repo_id=hf_repo_id,
            model_kwargs={"temperature": temperature, "max_length": max_length} )
        llm_chain = LLMChain(prompt=prompt, llm=llm)

        if inference_type == "evaluation":
          return llm_chain.run(
            position = input_variables_list[0],
            question=input_variables_list[1],
            answer=input_variables_list[2],

            )
        else:
            return llm_chain.predict(
                position=input_variables_list[0],
                candidate_profile=input_variables_list[1],
                n_results=input_variables_list[2],
                interview_phase=interview_phase
        )

    else:
        print(
            "Please use the correct value of model_type parameter: It can have a value of either openai or huggingface"
        )

        return ""