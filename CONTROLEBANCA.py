import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import os
from datetime import datetime

# Configuração inicial da página
st.set_page_config(page_title="Gerenciador de Apostas Premium", page_icon="💰", layout="wide")

# Constantes
ARQUIVO_DADOS = "dados_apostas.db"
BANCA_INICIAL = 100.0
META_LUCRO = 10000.0

# Funções de persistência
def init_db():
    conn = sqlite3.connect(ARQUIVO_DADOS)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao (id INTEGER PRIMARY KEY, banca REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT, valor REAL, odd REAL, retorno REAL, resultado TEXT,
        lucro_prejuizo REAL, casa TEXT, campeonato TEXT, jogo TEXT, mercado TEXT
    )''')
    c.execute('SELECT banca FROM configuracao WHERE id = 1')
    if not c.fetchone():
        c.execute('INSERT INTO configuracao (id, banca) VALUES (1, ?)', (BANCA_INICIAL,))
    conn.commit()
    conn.close()

def carregar_dados():
    init_db()
    conn = sqlite3.connect(ARQUIVO_DADOS)
    c = conn.cursor()
    c.execute('SELECT banca FROM configuracao WHERE id = 1')
    banca = c.fetchone()[0]
    
    c.execute('SELECT id, data, valor, odd, retorno, resultado, lucro_prejuizo, casa, campeonato, jogo, mercado FROM historico ORDER BY id')
    historico = []
    for row in c.fetchall():
        historico.append({
            "id": row[0], "Data": row[1], "Valor": row[2], "Odd": row[3],
            "Retorno": row[4], "Resultado": row[5], "Lucro/Prejuízo": row[6],
            "Casa de Apostas": row[7], "Campeonato": row[8], "Jogo": row[9], "Mercado": row[10]
        })
    conn.close()
    return banca, historico

# Inicializar estado da sessão
if "banca" not in st.session_state:
    banca_salva, historico_salvo = carregar_dados()
    st.session_state.banca = banca_salva
    st.session_state.historico = historico_salvo

# Funções principais
def registrar_aposta(resultado, valor, odd, casa, campeonato, jogo, mercado):
    erros = []
    if valor <= 0:
        erros.append("Valor deve ser positivo.")
    if valor > st.session_state.banca:
        erros.append("Valor excede a banca atual.")
    if odd < 1.01:
        erros.append("Odd mínima é 1.01.")
        
    if erros:
        for erro in erros:
            st.error(erro)
        return False
        
    casa = casa.strip() if casa.strip() else "-"
    campeonato = campeonato.strip() if campeonato.strip() else "-"
    jogo = jogo.strip() if jogo.strip() else "-"
    mercado = mercado.strip() if mercado.strip() else "-"

    retorno = valor * odd
    ganho = retorno - valor if resultado == "Ganhou" else -valor
    st.session_state.banca += ganho
    
    aposta = {
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Valor": float(valor),
        "Odd": float(odd),
        "Retorno": float(retorno),
        "Resultado": resultado,
        "Lucro/Prejuízo": float(ganho),
        "Casa de Apostas": casa.strip(),
        "Campeonato": campeonato.strip(),
        "Jogo": jogo.strip(),
        "Mercado": mercado.strip()
    }
    
    conn = sqlite3.connect(ARQUIVO_DADOS)
    c = conn.cursor()
    c.execute('''INSERT INTO historico (data, valor, odd, retorno, resultado, lucro_prejuizo, casa, campeonato, jogo, mercado)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                     aposta["Data"], aposta["Valor"], aposta["Odd"], aposta["Retorno"], aposta["Resultado"], aposta["Lucro/Prejuízo"],
                     aposta["Casa de Apostas"], aposta["Campeonato"], aposta["Jogo"], aposta["Mercado"]
                 ))
    aposta["id"] = c.lastrowid
    c.execute('UPDATE configuracao SET banca = ? WHERE id = 1', (st.session_state.banca,))
    conn.commit()
    conn.close()

    st.session_state.historico.append(aposta)
    st.success("Aposta registrada com sucesso!")
    return True

# --- SIDEBAR: OPÇÕES ---
st.sidebar.header("🛠️ Opções")

with st.sidebar.expander("📝 Nova Aposta", expanded=True):
    with st.form("form_aposta", clear_on_submit=True):
        valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=0.0)
        odd = st.number_input("Odd", min_value=1.01, step=0.1, value=1.50)
        resultado = st.radio("Resultado", ["Ganhou", "Perdeu"], horizontal=True)
        
        casa = st.text_input("Casa de Apostas (Opcional)")
        campeonato = st.text_input("Campeonato (Opcional)")
        jogo = st.text_input("Jogo (Opcional)")
        mercado = st.text_input("Mercado (Opcional)")
        
        submit_aposta = st.form_submit_button("✅ Registrar Aposta", use_container_width=True)
        
        if submit_aposta:
            registrar_aposta(resultado, valor, odd, casa, campeonato, jogo, mercado)

with st.sidebar.expander("🧮 Calculadora Kelly", expanded=False):
    k_odd = st.number_input("Odd Esperada", min_value=1.01, step=0.1, value=1.50, key="k_odd")
    k_conf = st.slider("Confiança (%)", min_value=1, max_value=100, value=50, key="k_conf")
    
    kelly = (k_odd * (k_conf / 100) - (1 - (k_conf / 100))) / k_odd if k_odd > 0 else 0
    stake_sugerida = st.session_state.banca * kelly * 0.5 if kelly > 0 else 0.0
    
    st.write("---")
    if kelly > 0:
        st.info(f"💡 Sugestão Fixa (2%): R$ {st.session_state.banca * 0.02:.2f}")
        st.success(f"🎯 Sugestão Kelly (50%): R$ {stake_sugerida:.2f}")
    else:
        st.error("⚠️ EV Negativo. Não aposte.")

# Interface Principal
st.title("💰 Gerenciador de Apostas")

# --- DASHBOARD ---
df = pd.DataFrame(st.session_state.historico) if st.session_state.historico else pd.DataFrame(columns=["Data", "Valor", "Odd", "Retorno", "Resultado", "Lucro/Prejuízo", "Casa de Apostas", "Campeonato", "Jogo", "Mercado"])

lucro_total = df['Lucro/Prejuízo'].sum() if not df.empty else 0.0
total_apostado = df['Valor'].sum() if not df.empty else 0.0
roi = (lucro_total / total_apostado * 100) if total_apostado else 0.0
vitorias = len(df[df["Resultado"] == "Ganhou"]) if not df.empty else 0
taxa_acerto = (vitorias / len(df)) * 100 if not df.empty else 0.0
progresso_meta = max(0.0, min(100.0, ((st.session_state.banca - BANCA_INICIAL) / META_LUCRO) * 100)) if META_LUCRO > 0 else 0.0

# Separando o layout em abas para não poluir a tela
tab_dash, tab_hist = st.tabs(["📊 Dashboard de Desempenho", "📋 Histórico e Gestão"])

with tab_dash:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Banca Atual", f"R$ {st.session_state.banca:.2f}", f"{st.session_state.banca - BANCA_INICIAL:.2f} (Lucro)" if st.session_state.banca >= BANCA_INICIAL else f"{st.session_state.banca - BANCA_INICIAL:.2f} (Prejuízo)")
    col2.metric("ROI", f"{roi:.1f}%")
    col3.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
    col4.metric("Progresso da Meta", f"{progresso_meta:.1f}%", f"R$ {st.session_state.banca - BANCA_INICIAL:.2f} / R$ {META_LUCRO:.2f}")
    st.progress(progresso_meta / 100.0)
    
    st.markdown("---")
    st.subheader("📈 Análise de Desempenho")
    
    if not df.empty:
        tab_g1, tab_g2, tab_g3 = st.tabs(["Evolução da Banca", "Lucro/Prejuízo", "Taxa de Vitórias"])
        
        with tab_g1:
            saldo = BANCA_INICIAL
            banca_evolucao = [saldo]
            for lucro in df["Lucro/Prejuízo"]:
                saldo += lucro
                banca_evolucao.append(saldo)
                
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            ax1.plot(banca_evolucao, marker='o', color='dodgerblue')
            ax1.set_title("Evolução da Banca")
            ax1.set_ylabel("Saldo (R$)")
            ax1.grid(True)
            st.pyplot(fig1)
            
        with tab_g2:
            ganhos = df["Lucro/Prejuízo"].apply(lambda x: x if x >= 0 else 0).tolist()
            perdas = df["Lucro/Prejuízo"].apply(lambda x: abs(x) if x < 0 else 0).tolist()
            
            fig2, ax2 = plt.subplots(figsize=(10, 4))
            ax2.bar(range(len(ganhos)), ganhos, color='lime', label="Ganhos")
            ax2.bar(range(len(perdas)), perdas, color='tomato', bottom=ganhos, label="Perdas")
            ax2.set_title("Lucro/Prejuízo por Aposta")
            ax2.set_ylabel("Valor (R$)")
            ax2.legend()
            st.pyplot(fig2)
            
        with tab_g3:
            fig3, ax3 = plt.subplots(figsize=(6, 6))
            vitorias_count = len(df[df["Resultado"] == "Ganhou"])
            derrotas_count = len(df[df["Resultado"] == "Perdeu"])
            if vitorias_count + derrotas_count > 0:
                ax3.pie([vitorias_count, derrotas_count], labels=["Vitórias", "Derrotas"],
                        autopct='%1.1f%%', startangle=90, colors=["mediumseagreen", "orangered"])
                ax3.set_title("Taxa de Vitórias")
                st.pyplot(fig3)
    else:
        st.info("Nenhuma aposta registrada para gerar gráficos.")

with tab_hist:
    st.subheader("📋 Tabela de Apostas")
    
    if not df.empty:
        with st.expander("🔍 Filtros da Tabela"):
            f_col1, f_col2, f_col3 = st.columns(3)
            filtro_resultado = f_col1.selectbox("Resultado", ["Todos", "Ganhou", "Perdeu"])
            filtro_casa = f_col2.selectbox("Casa de Apostas", ["Todas"] + sorted(df["Casa de Apostas"].unique().tolist()))
            filtro_camp = f_col3.selectbox("Campeonato", ["Todos"] + sorted(df["Campeonato"].unique().tolist()))
            
        df_filtrado = df.copy()
        if filtro_resultado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Resultado"] == filtro_resultado]
        if filtro_casa != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Casa de Apostas"] == filtro_casa]
        if filtro_camp != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Campeonato"] == filtro_camp]
            
        df_display = df_filtrado.drop(columns=["id"], errors='ignore')
        st.dataframe(df_display, use_container_width=True, hide_index=False)
        
        st.markdown("---")
        st.subheader("⚙️ Ações e Gerenciamento")
        c_action1, c_action2, c_action3 = st.columns([2, 1, 1])
        
        with c_action1:
            # Cria um seletor legível em vez de só exibir índices
            opcoes_excluir = ["Nenhuma"]
            for i, row in df.iterrows():
                texto = f"{i} - {row['Data']} | {row['Jogo']} ({row['Resultado']})"
                opcoes_excluir.append(texto)
                
            aposta_excluir = st.selectbox("Selecione a aposta para excluir:", opcoes_excluir)
            if st.button("🗑️ Excluir Aposta Selecionada", use_container_width=True):
                if aposta_excluir != "Nenhuma":
                    idx = int(aposta_excluir.split(" - ")[0])
                    aposta_removida = st.session_state.historico.pop(idx)
                    
                    # Subtrair o Lucro/Prejuízo devolve o valor ou cancela o ganho automaticamente
                    st.session_state.banca -= aposta_removida["Lucro/Prejuízo"]
                        
                    conn = sqlite3.connect(ARQUIVO_DADOS)
                    c = conn.cursor()
                    c.execute('DELETE FROM historico WHERE id = ?', (aposta_removida["id"],))
                    c.execute('UPDATE configuracao SET banca = ? WHERE id = 1', (st.session_state.banca,))
                    conn.commit()
                    conn.close()

                    st.success("Aposta excluída com sucesso!")
                    st.rerun()
                    
        with c_action2:
            st.write("")
            st.write("")
            df_csv = df.drop(columns=["id"], errors='ignore')
            csv = df_csv.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Baixar CSV", data=csv, file_name="historico_apostas.csv", mime="text/csv", use_container_width=True)
            
        with c_action3:
            st.write("")
            st.write("")
            if st.button("🔥 Limpar Histórico Total", type="primary", use_container_width=True):
                st.session_state.historico = []
                st.session_state.banca = BANCA_INICIAL
                
                conn = sqlite3.connect(ARQUIVO_DADOS)
                c = conn.cursor()
                c.execute('DELETE FROM historico')
                c.execute('UPDATE configuracao SET banca = ? WHERE id = 1', (BANCA_INICIAL,))
                conn.commit()
                conn.close()

                st.success("Histórico apagado!")
                st.rerun()
    else:
        st.info("Nenhuma aposta registrada ainda. Adicione uma aposta pelo menu lateral!")