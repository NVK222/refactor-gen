import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import traceback

BASE_MODEL_ID = "Qwen/CodeQwen1.5-7B"
model_path = "../merged_model"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="Qwen Backend")

print(f"Initializing Backend on {DEVICE}...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

try:
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.chat_template = (
        "{% for message in messages %}"
        "{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>\n'}}"
        "{% endfor %}"
        "{% if add_generation_prompt %}"
        "{{'<|im_start|>assistant\n'}}"
        "{% endif %}"
    )
    
    tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading {BASE_MODEL_ID} into VRAM...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        #quantization_config=bnb_config,
        device_map={"": 0},
        trust_remote_code=True,
    )
    model.eval()
except Exception as e:
    print(f"Loading Error: {e}")
    traceback.print_exc()

class GenerateRequest(BaseModel):
    prompt: str
    language: str

class RefactorRequest(BaseModel):
    code: str
    instruction: str

def generate_response(system_prompt: str, user_prompt: str):
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(DEVICE)
    stop_tokens = ["<|im_end|>", "<|endoftext|>", "<file_sep>", "assistant\n", "<fim_middle>", "<fim_suffix>", "Next Instruction"]
    
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256, 
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>"),
            use_cache=True,
        )
    
    generated_ids = [out[len(ins):] for ins, out in zip(inputs.input_ids, outputs)]
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    for stop_word in stop_tokens:
        response = response.split(stop_word)[0]
    response = response.strip()
    
    del inputs, outputs
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    return response

@app.get("/health")
def health():
    return {"status": "online", "model": "Qwen-1.5-7B", "device": DEVICE}

@app.post("/generate")
async def generate(req: GenerateRequest):
    print("Trying to generate")
    system = f"You are an expert {req.language} developer. Respond with ONLY, no markdown tags, no conversational text before and after the code."
    try:
        raw_code = generate_response(system, req.prompt)
        clean_code = raw_code.replace(f"```" + req.language, "").replace("```", "").strip()
        return {"generated_code": clean_code}
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error:{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refactor")
async def refactor(req: RefactorRequest):
    system = "You are a senior engineer. Refactor the code for better performance and readability. Respond with code ONLY,no markdown tags, no conversational text before and after the code."
    user = f"Instruction: {req.instruction}\n\nCode:\n{req.code}"
    try:
        raw_code = generate_response(system, user)
        clean_code = raw_code.replace("```", "").strip()
        return {"refactored_code": clean_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
