# app.py
import streamlit as st
import google.generativeai as genai
import json

# --- Configuração da Página e Estilo ---
st.set_page_config(
    page_title="ExamSynth™ AI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para um visual mais limpo
st.markdown("""
<style>
    .stApp {
        background-color: #F0F2F6;
    }
    .st-emotion-cache-16txtl3 {
        padding: 2rem 1rem 1rem;
    }
    .st-emotion-cache-1y4p8pa {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# --- PROMPT MESTRE: A Persona e as Regras do Agente de IA ---
# Este prompt transforma o Gemini no agente ExamSynth. Ele contém todas as regras originais.
# A instrução final pede uma saída em JSON para garantir um parsing robusto e confiável.
EXAMSYNTH_SYSTEM_PROMPT = """
Você é o ExamSynth™ Clinical, um especialista de IA de elite em sumarizar exames para prontuários. Sua única missão é receber um texto bruto de exames e transformá-lo em um resumo clínico estruturado, seguindo rigorosamente as regras abaixo.

**PRINCÍPIOS E REGRAS GERAIS:**
1.  **Fidelidade e Formato:** Transcreva os dados originais. Use vírgula como decimal (ex: 10,5). Use 'K' para milhares (ex: 340K). Resultados da mesma data devem estar na mesma linha. Use abreviações listadas.
2.  **Análise Condicional:** NÃO faça julgamentos de valor. Apenas sinalize com `*` se o texto fornecer um Valor de Referência (VR) e o resultado estiver fora dele.
3.  **Estrutura de Saída:** A saída final deve ser um texto em Markdown. Comece com o Resumo Laboratorial Geral, seguido pelas Seções Dedicadas e, por fim, o Resumo de Imagem. Use `---` como separador entre as seções.

**MÓDULOS DE PROCESSAMENTO:**

**MÓDULO 1A – RESUMO LABORATORIAL GERAL:**
- **Conteúdo:** Exames que NÃO pertencem às seções dedicadas.
- **Formato:** `DD/MM: [ABREV1 VAL1] [ABREV2 VAL2] | [ABREV_GRUPO_SEGUINTE VALX]...`
- **Exemplo:** `05/05: HB 13,2 HT 39,6 PLAQ 343K | UR 77,6 CR 1,22 | NA 136 K 4,9`

**MÓDULO 1B – SEÇÕES LABORATORIAIS DEDICADAS:**
- **Organização:** Cada seção com seu cabeçalho em negrito. Resultados agrupados por data.
- **Seções:**
    - **CARDIOVASCULAR:** (TROPONINA, CKMB, BNP, etc.)
    - **HORMONAIS:** (TSH, T4L, CORTISOL, PSA, etc.)
    - **SOROLOGIAS:** (HIV, HBsAg, AntiHBs, etc.). **Aplique interpretações padronizadas se o padrão for claro.** Ex: `(Interpretação: HBV Imune(Vac))` para HBsAg NR, AntiHBs R.
    - **REUMATOLÓGICO:** (FAN, FR, AntiDNA, etc.)
    - **ANEMIA ESPECÍFICA:** (FERRITINA, VITB12, etc.)
    - **MARCADORES TUMORAIS:** (CEA, CA 19-9, etc.)

**MÓDULO 2 – RESUMO DE EXAMES DE IMAGEM:**
- **Formato:** `[NOME DO EXAME EM MAIÚSCULAS] (DD/MM/AAAA): [Transcrição da IMPRESSÃO ou CONCLUSÃO].`
- **Exemplo:** `TC DE CRÂNIO (15/05/2024): Sem alterações significativas.`

**LISTA DE ABREVIAÇÕES (Use estas):**
- **Geral:** HB, HT, PLAQ, LEU, NEU%, LIN%; UR, CR, TFG; NA, K, CA, GLI; TGO, TGP, FA, GGT; PCR, VHS; INR, TTPA.
- **Cardio:** TROPONINA I, TROPONINA T, CKMB, BNP, PROBNP.
- **Hormonal:** TSH, T4L, PSA T, PSA L, CORTAM.
- **Sorologia:** HIV12, HBsAg, AntiHBs, AntiHBc TOTAL, VDRL.
- **Reumato:** FAN, FR, AntiDNA, C3, C4.
- **Anemia:** FERR, SATTRANSF, VITB12, FOLATO S.
- **Onco:** CEA, CA 19-9, CA 125, AFP.

**TAREFA FINAL E FORMATO DE SAÍDA OBRIGATÓRIO:**
Analise o texto fornecido pelo usuário. Mesmo que seja caótico, extraia o máximo de informações possível. Gere um objeto JSON contendo duas chaves:
1.  `"structured_summary"`: Uma string contendo o resumo clínico completo e final em formato Markdown, seguindo todas as regras e a ordem dos módulos.
2.  `"parsing_log"`: Uma string descrevendo em bullet points quais informações você conseguiu extrair e, mais importante, quais linhas ou dados você ignorou por não conseguir interpretar ou por não se encaixarem nas categorias. Seja transparente sobre suas limitações.

**NÃO ESCREVA NADA ALÉM DO OBJETO JSON.**
"""

# --- FUNÇÃO DO AGENTE DE IA ---
def chamar_agente_gemini(api_key, texto_clinico):
    """
    Invoca o agente Gemini para processar o texto clínico.
    Retorna o resumo estruturado e o log de parsing.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            system_instruction=EXAMSYNTH_SYSTEM_PROMPT
        )
        # O prompt para o modelo é apenas o texto do usuário
        response = model.generate_content(texto_clinico)

        # Limpa a saída para garantir que seja um JSON válido
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        
        # Tenta parsear a resposta como JSON
        data = json.loads(cleaned_response)
        summary = data.get("structured_summary", "Erro: Chave 'structured_summary' não encontrada na resposta da IA.")
        log = data.get("parsing_log", "Erro: Chave 'parsing_log' não encontrada na resposta da IA.")
        
        return summary, log

    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a API do Gemini: {e}")
        error_details = f"Resposta bruta da API (pode conter erros):\n\n{response.text if 'response' in locals() else 'Nenhuma resposta recebida.'}"
        return "Falha ao gerar o resumo.", error_details


# --- INTERFACE DO STREAMLIT ---

# --- BARRA LATERAL (CONTROLES) ---
with st.sidebar:
    st.image("https://i.imgur.com/2g1L2d2.png", width=250) # Logotipo fictício
    st.header("Configuração do Agente")

    # Entrada da API Key
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("API Key do Gemini carregada com sucesso!", icon="✅")
    except (FileNotFoundError, KeyError):
        st.warning("API Key não encontrada nos segredos.", icon="⚠️")
        api_key = st.text_input("Insira sua API Key do Gemini aqui:", type="password", help="Obtenha sua chave no Google AI Studio.")

    st.divider()
    
    st.header("Fonte dos Dados")
    input_source = st.radio("Escolha como fornecer os dados:", ("Colar Texto", "Fazer Upload de Arquivo .txt"), horizontal=True)
    
    text_input = ""
    if input_source == "Colar Texto":
        text_input = st.text_area("Cole o texto bruto dos exames aqui:", height=250)
    else:
        uploaded_file = st.file_uploader("Selecione um arquivo .txt", type=['txt'])
        if uploaded_file:
            text_input = uploaded_file.getvalue().decode("utf-8")

    gerar_btn = st.button("✨ Gerar Resumo Clínico", use_container_width=True, type="primary")

# --- ÁREA PRINCIPAL (RESULTADOS) ---
st.title("Painel ExamSynth™ AI 🩺")
st.markdown("##### Clarity from Complexity. Insight from Data.")
st.divider()

if gerar_btn:
    if not api_key:
        st.error("A API Key do Gemini é obrigatória para continuar.")
    elif not text_input.strip():
        st.warning("Por favor, forneça os dados dos exames para análise.")
    else:
        with st.spinner("O Agente ExamSynth™ AI está analisando os dados... Por favor, aguarde."):
            summary, log = chamar_agente_gemini(api_key, text_input)
            st.session_state.summary = summary
            st.session_state.log = log

if 'summary' in st.session_state and st.session_state.summary:
    st.success("Análise concluída com sucesso!")
    
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.subheader("📄 Resumo Clínico Gerado")
            st.markdown(st.session_state.summary)
            st.download_button(
                label="📥 Baixar Resumo (.md)",
                data=st.session_state.summary,
                file_name="ExamSynth_Resumo.md",
                mime="text/markdown",
                use_container_width=True
            )

    with col2:
        with st.container(border=True):
            st.subheader("⚙️ Log de Análise do Agente")
            st.markdown(st.session_state.log)
else:
    st.info("Aguardando dados para análise. Configure na barra lateral e clique em 'Gerar Resumo'.")
