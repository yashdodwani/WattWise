import os
import requests
import json
import re

def get_power_from_model(brand: str, model: str) -> float | None:
    """
    Estimate the power consumption of an appliance model using an LLM.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return None

        prompt = f"""
        What is the typical power consumption in kilowatts (kW) of a {brand} {model}?
        Provide only the numerical value in kW.
        If you cannot find the value, respond with 0.
        """

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                "messages": [
                    {"role": "system", "content": "You are an expert in home appliance power consumption. You reply ONLY with a number."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            }),
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            power_str = data['choices'][0]['message']['content'].strip()
            
            # Clean the string to ensure it's just a number
            match = re.search(r"(\d+(\.\d+)?)", power_str)
            if match:
                power_kw = float(match.group(1))
                if power_kw == 0:
                    return None
                return power_kw
            
        return None

    except Exception:
        return None

