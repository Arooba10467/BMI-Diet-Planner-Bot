import gradio as gr
import requests
import PyPDF2
import os
# Load Ohio University Nutrition PDF
def load_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

# Load the document once
pdf_file = "2020_osuhp_bmi-weight_management.pdf"
ohio_doc_text = load_pdf_text(pdf_file)[:2000]  # Trimmed for token limit

# API details
GROQ_API_KEY = os.getenv("key", "gsk_your_default_key")  # Replace with your actual Groq key or set as secret
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Main diet chatbot logic
def diet_chatbot(name, gender, height_cm, weight_kg, proceed, diet_type, spicy, planner_type, lifestyle, user_query):
    try:
        # BMI calculation
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        if bmi < 18.5:
            bmi_category = "underweight"
        elif 18.5 <= bmi < 25:
            bmi_category = "normal"
        elif 25 <= bmi < 30:
            bmi_category = "overweight"
        else:
            bmi_category = "obese"

        if not proceed or proceed.lower() != "y":
            return f"Thank you, {name}. You chose not to proceed with the diet planner. Goodbye!", ""

        # Prompt with document context
        prompt = f"""
You are a helpful diet assistant.


Use ONLY the following Ohio University document to guide your answer. Prioritize facts and recommendations from it.
<<<START_OF_DOCUMENT>>>
{ohio_doc_text}
<<<END_OF_DOCUMENT>>>


User Details:
- Name: {name}
- Gender: {gender}
- Height: {height_cm} cm
- Weight: {weight_kg} kg
- BMI: {bmi:.2f} ({bmi_category})
- Diet Preference: {diet_type}
- Likes Spices: {spicy}
- Plan Type: {planner_type}
- Lifestyle: {lifestyle}

Generate a personalized {planner_type.lower()} diet plan based on these details.
"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=body)

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            response_text = (
                f"👤 **Your BMI**: {bmi:.2f} ({bmi_category})\n\n"
                f"💬 **Diet Plan & Answer:**\n{reply}\n\n"
                "✅ Thank you! You can ask more health-related questions in the chat below."
            )
            return response_text, ""
        else:
            return f"❌ API Error: {response.text}", ""

    except Exception as e:
        return f"❌ Runtime error: {str(e)}", ""

# Function for chat-based follow-up questions
def followup_chat(history, new_question):
    prompt = f"""
You are a helpful health and diet assistant.
If you use any information from the document, mention it came from the 'Ohio Guide'.

Use this Ohio University document for support:

{ohio_doc_text}

Respond to the user's follow-up question below:
Q: {new_question}

Only answer if the question is related to diet, exercise, or health. If not, politely say you only handle health-related topics.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=body)

    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        history.append((new_question, reply))
    else:
        history.append((new_question, f"❌ API Error: {response.text}"))
    return history, ""

# Gradio UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🥗 AI Diet Planner Chatbot
    Welcome! Please provide your details to receive a personalized diet plan based on your BMI and preferences.
    """)

    with gr.Row():
        name = gr.Textbox(label="Your Name", placeholder="e.g., Sarah")
        gender = gr.Radio(choices=["Male", "Female"], label="Gender")

    with gr.Row():
        height = gr.Slider(100, 250, label="Height (cm)", step=1)
        weight = gr.Slider(30, 200, label="Weight (kg)", step=1)

    proceed = gr.Textbox(label="Type 'y' to continue or 'n' to exit", placeholder="y")
    diet = gr.Radio(choices=["vegetarian", "non-vegetarian", "both"], label="Diet Preference")
    spicy = gr.Radio(choices=["Yes", "No"], label="Do you like spicy food?")
    plan_type = gr.Radio(choices=["Week Planner", "Day Planner"], label="Planner Type")
    lifestyle = gr.Textbox(label="Describe your lifestyle briefly", placeholder="e.g., student, office worker, active")
    user_query = gr.Textbox(label="Ask a follow-up question (optional)", placeholder="e.g., How much protein do I need?")
    submit = gr.Button("Generate Diet Plan")
    response_output = gr.Textbox(label="Response", lines=12)
    chat_state = gr.State([])

    submit.click(
        fn=diet_chatbot,
        inputs=[name, gender, height, weight, proceed, diet, spicy, plan_type, lifestyle, user_query],
        outputs=[response_output, chat_state]
    )

    gr.Markdown("""
    ## 💬 Ask More Questions Below:
    Continue the conversation about your health and fitness.
    """)

    chatbot = gr.Chatbot()
    followup_input = gr.Textbox(label="Your question", placeholder="Ask something health-related...")
    followup_submit = gr.Button("Send")

    followup_submit.click(
        fn=followup_chat,
        inputs=[chatbot, followup_input],
        outputs=[chatbot, followup_input]
    )

if __name__ == "__main__":
    demo.launch()