from config import MODEL_NAME
from core.utils import build_conversation_text, safe_str
from integrations.llm import obtener_cliente_azure


def llamada_user_simulator(
        prompt_cliente, historia, max_output_tokens=100, model=MODEL_NAME
):
    prompt_cliente = safe_str(prompt_cliente).strip()
    conv = build_conversation_text(historia)
    user_turn = f"""
CONVERSACION HASTA AHORA:
{conv}
INSTRUCCIONES:
- Te toca responder COMO CLIENTE al ULTIMO mensaje del BANCO.
- Devuelve SOLO el texto del cliente (sin prefijos tipo "Cliente:", "Usuario:", etc.).
- No termines la conversacion (no digas "fin"/"adios") a menos que sea estrictamente necesario.
- Responde SIEMPRE de forma breve y solo lo necesario. No uses frases largas.
""".strip()
    resp = obtener_cliente_azure().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_cliente},
            {"role": "user", "content": user_turn},
        ],
        max_tokens=max_output_tokens,
        temperature=0.7,
        stop=None,
    )
    return (resp.choices[0].message.content or "").strip()
