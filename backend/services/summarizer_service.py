from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

print("Loading AI Model & Tokenizer (This might take a few seconds...)")

# Define the model we want to use
model_name = "Falconsai/text_summarization"

# Load the tokenizer and the model explicitly
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

print("Model loaded successfully!")

def summarize_text(text):
    # Skip extremely short descriptions
    if not text or len(text.split()) < 15:
        return text or "No content available"

    try:
        # 1. Convert the text into numbers (tokens) the AI can understand
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
        
        # 2. Ask the model to generate the summary tokens
        outputs = model.generate(**inputs, max_length=60, min_length=20, do_sample=False)
        
        # 3. Convert the output tokens back into readable human text
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return summary
    except Exception as e:
        print(f"Summarization error: {e}")
        return text