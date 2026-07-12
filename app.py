import pandas as pd
import streamlit as st
import plotly.express as px
import io
import calendar


# --- FUNÇÃO PARA TRATAR OS DADOS ---
@st.cache_data
def load_and_process_data(file):
    df = pd.read_csv(file)

    meses_map = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }

    df['Mês_Num_Ini'] = df['Mês'].astype(str).str.lower().str.strip().map(meses_map)
    df['Mês_Num_Fim'] = df['Mês.1'].astype(str).str.lower().str.strip().map(meses_map)

    df['HRINI_limpa'] = df['HRINI'].astype(str).str.split(' ').str[-1]
    df['HRFIM_limpa'] = df['HRFIM'].astype(str).str.split(' ').str[-1]

    df['DataHora_Inicio'] = pd.to_datetime(
        df['Ano'].astype(str) + '-' + df['Mês_Num_Ini'].astype(str) + '-' + df['Dia'].astype(str) + ' ' + df[
            'HRINI_limpa']
    )

    df['DataHora_Fim'] = pd.to_datetime(
        df['Ano.1'].astype(str) + '-' + df['Mês_Num_Fim'].astype(str) + '-' + df['Dia.1'].astype(str) + ' ' + df[
            'HRFIM_limpa']
    )

    df = df.sort_values('DataHora_Inicio').reset_index(drop=True)

    df['MINUTOS_CALCULADO'] = (df['DataHora_Fim'] - df['DataHora_Inicio']).dt.total_seconds() / 60

    if 'MINUTOS' not in df.columns:
        df['MINUTOS'] = df['MINUTOS_CALCULADO']

    df['Horas_Desde_Ultimo'] = (df['DataHora_Inicio'] - df['DataHora_Inicio'].shift(1)).dt.total_seconds() / 3600
    df['Corridas_Desde_Ultimo'] = df['CORRIDA'] - df['CORRIDA'].shift(1)

    dias_pt = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    meses_abrev_pt = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    df['Dia_Semana'] = df['DataHora_Inicio'].dt.day_name().map(dias_pt)
    df['Mes_Nome'] = df['DataHora_Inicio'].dt.month.map(meses_abrev_pt)

    colunas_para_remover = ['Mês_Num_Ini', 'Mês_Num_Fim', 'HRINI_limpa', 'HRFIM_limpa', 'MINUTOS_CALCULADO']
    df = df.drop(columns=[col for col in colunas_para_remover if col in df.columns])

    df = df.sort_values('CORRIDA', ascending=False).reset_index(drop=True)

    return df


def converter_df_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Base_Reparos_Limpa')
    return output.getvalue()


# --- CONFIGURAÇÃO DA INTERFACE STREAMLIT ---
st.set_page_config(page_title="Dashboard de Rotina - Reparo de Canal", layout="wide")

st.title("⚙️ Análise de Rotina - Reparo de Canal")
st.markdown("Monitoramento de aderência à rotina programada e estabilidade operacional.")

uploaded_file = st.file_uploader("Faça o upload do seu arquivo .csv", type="csv")

if uploaded_file is not None:
    df_completo = load_and_process_data(uploaded_file)

    st.sidebar.header("Filtros Globais")
    anos_disponiveis = sorted(df_completo['Ano'].unique().tolist())
    anos_selecionados = st.sidebar.multiselect("Selecione o(s) Ano(s)", anos_disponiveis, default=anos_disponiveis)

    df = df_completo[df_completo['Ano'].isin(anos_selecionados)].copy()
    df['Ano_Str'] = df['Ano'].astype(str)

    if not df.empty:
        st.subheader(f"Indicadores Gerais - {', '.join(map(str, anos_selecionados))}")

        total_minutos_exposicao = int(df['MINUTOS'].sum())
        horas_exposicao = total_minutos_exposicao // 60
        minutos_exposicao_restantes = total_minutos_exposicao % 60
        texto_exposicao = f"{horas_exposicao}h {minutos_exposicao_restantes}m"

        media_minutos = df['MINUTOS'].mean()
        media_corridas = df['Corridas_Desde_Ultimo'].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Reparos", len(df))
        c2.metric("Tempo Total Dedicado", texto_exposicao)
        c3.metric("Tempo Médio (Reparo)", f"{media_minutos:.1f} min")
        c4.metric("Média entre Reparos", f"{media_corridas:.1f} corridas")

        st.divider()

        cores_ano = {
            '2024': '#2ca02c',
            '2025': '#ff7f0e',
            '2026': '#9467bd'
        }

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Distribuição do Tempo de Reparo")
            fig1 = px.scatter(df, x='DataHora_Inicio', y='MINUTOS', color='Ano_Str',
                              color_discrete_map=cores_ano, opacity=0.85,
                              labels={'MINUTOS': 'Duração (min)', 'DataHora_Inicio': 'Data', 'Ano_Str': 'Ano'})

            fig1.update_traces(marker=dict(size=9, line=dict(width=1, color='DarkSlateGrey')))
            fig1.add_hline(y=media_minutos, line_dash="dash", line_color="red",
                           annotation_text=f"Média: {media_minutos:.1f}m")
            st.plotly_chart(fig1, use_container_width=True)

        with col_chart2:
            st.markdown("#### Corridas entre Reparos")
            df_plot2 = df.dropna(subset=['Corridas_Desde_Ultimo'])

            fig2 = px.scatter(df_plot2, x='DataHora_Inicio', y='Corridas_Desde_Ultimo', color='Ano_Str',
                              color_discrete_map=cores_ano, opacity=0.85,
                              labels={'Corridas_Desde_Ultimo': 'Qtd. Corridas', 'DataHora_Inicio': 'Data',
                                      'Ano_Str': 'Ano'})

            fig2.update_traces(marker=dict(size=9, line=dict(width=1, color='DarkSlateGrey')))
            fig2.add_hline(y=media_corridas, line_dash="dash", line_color="red",
                           annotation_text=f"Média: {media_corridas:.1f}c")
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.markdown("### 📅 Rotina de Reparo")

        col_macro, col_micro = st.columns(2)

        # --- VISÃO MACRO ---
        with col_macro:
            st.markdown("#### Visão Macro")
            st.caption("Reparos cruzando Meses x Dias da Semana.")

            anos_macro = sorted(df['Ano'].unique().tolist())
            ano_selecionado_macro = st.radio("Selecione o Ano para a Visão Macro:", options=anos_macro, horizontal=True)

            df_macro = df[df['Ano'] == ano_selecionado_macro]

            ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

            if not df_macro.empty:
                df_heatmap = df_macro.groupby(['Mes_Nome', 'Dia_Semana']).size().reset_index(name='Qtd_Reparos')
                heatmap_data = df_heatmap.pivot(index='Mes_Nome', columns='Dia_Semana', values='Qtd_Reparos').fillna(0)

                # O preenchimento explícito com fill_value=0 garante que os 7 dias sempre apareçam
                heatmap_data = heatmap_data.reindex(
                    index=[m for m in ordem_meses if m in heatmap_data.index],
                    columns=ordem_dias, fill_value=0
                )

                escala_macro = [
                    [0.0, 'rgba(128, 128, 128, 0.05)'],
                    [0.01, '#fdebd0'],
                    [1.0, '#e74c3c']
                ]

                fig_heat = px.imshow(
                    heatmap_data,
                    labels=dict(x="Dia da Semana", y="Mês", color="Nº de Reparos"),
                    x=heatmap_data.columns,
                    y=heatmap_data.index,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale=escala_macro
                )
                fig_heat.update_traces(xgap=3, ygap=3)
                fig_heat.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info(f"Sem dados de reparo para o ano de {ano_selecionado_macro}.")

        # --- VISÃO MICRO ---
        with col_micro:
            st.markdown("#### Visão Micro: Calendário de Execução")
            st.caption("Selecione um mês específico para auditar a aderência aos dias programados.")

            col_sel_ano, col_sel_mes = st.columns(2)

            anos_micro = sorted(df['Ano'].unique().tolist())
            with col_sel_ano:
                ano_selecionado_micro = st.selectbox("Ano:", options=anos_micro, key="sb_ano_micro")

            meses_disponiveis = df[df['Ano'] == ano_selecionado_micro]['Mes_Nome'].unique()
            meses_ordenados = [m for m in ordem_meses if m in meses_disponiveis]

            with col_sel_mes:
                mes_selecionado_micro = st.selectbox("Mês:", options=meses_ordenados, key="sb_mes_micro")

            df_mes_calendario = df[(df['Ano'] == ano_selecionado_micro) & (df['Mes_Nome'] == mes_selecionado_micro)]

            if not df_mes_calendario.empty:
                mes_num_cal = df_mes_calendario['DataHora_Inicio'].dt.month.iloc[0]

                cal_matrix = calendar.monthcalendar(ano_selecionado_micro, mes_num_cal)

                # Agrupa os dados extraindo a quantidade de reparos E a lista das corridas do dia
                agrupado_dia = df_mes_calendario.groupby(df_mes_calendario['DataHora_Inicio'].dt.day)
                reparos_por_dia = agrupado_dia.size().to_dict()
                corridas_por_dia = agrupado_dia['CORRIDA'].apply(lambda x: ', '.join(x.astype(str))).to_dict()

                z_data = []
                text_data = []
                hover_data = []  # Array paralelo para alimentar os tooltips

                max_reparos = max(reparos_por_dia.values()) if reparos_por_dia else 1

                for week in cal_matrix:
                    z_week = []
                    text_week = []
                    hover_week = []
                    for day in week:
                        if day == 0:
                            z_week.append(None)
                            text_week.append("")
                            hover_week.append("")
                        else:
                            qtd = reparos_por_dia.get(day, 0)
                            z_week.append(qtd)

                            if qtd == 0:
                                text_week.append(f"<span style='font-size: 13px; color: #888888;'>{day}</span>")
                                hover_week.append(f"<b>Dia {day}</b><br>Nenhum reparo registrado.")
                            else:
                                text_week.append(
                                    f"<b>{day}</b><br><span style='font-size: 15px; color: white;'>{qtd} rep.</span>")
                                corridas_str = corridas_por_dia.get(day, "")
                                hover_week.append(f"<b>Dia {day}</b><br>Reparos: {qtd}<br>Corridas: {corridas_str}")

                    z_data.append(z_week)
                    text_data.append(text_week)
                    hover_data.append(hover_week)

                escala_micro = [
                    [0.0, 'rgba(128, 128, 128, 0.05)'],
                    [0.01, '#3498db'],
                    [1.0, '#154360']
                ]

                fig_cal = px.imshow(
                    z_data,
                    labels=dict(x="", y="", color="Nº de Reparos"),
                    x=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                    y=[f'Sem {i + 1}' for i in range(len(cal_matrix))],
                    color_continuous_scale=escala_micro,
                    zmin=0,
                    zmax=max_reparos,
                    aspect="auto"
                )

                # Ativa o tooltip (hover) usando os dados customizados que criamos
                fig_cal.update_traces(
                    text=text_data,
                    texttemplate="%{text}",
                    customdata=hover_data,
                    hovertemplate="%{customdata}<extra></extra>",
                    xgap=5,
                    ygap=5
                )

                fig_cal.update_layout(
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=False, zeroline=False)
                )

                st.plotly_chart(fig_cal, use_container_width=True)

        st.divider()
        st.markdown("#### Base de Dados Processada")

        colunas_finais = [
            'Ano', 'Mes_Nome', 'Dia_Semana', 'CORRIDA', 'DataHora_Inicio', 'DataHora_Fim',
            'MINUTOS', 'Horas_Desde_Ultimo', 'Corridas_Desde_Ultimo'
        ]

        df_limpo = df[[col for col in colunas_finais if col in df.columns]].copy()
        df_limpo = df_limpo.rename(columns={
            'Mes_Nome': 'Mês',
            'Dia_Semana': 'Dia da Semana',
            'CORRIDA': 'Corrida',
            'DataHora_Inicio': 'Início',
            'DataHora_Fim': 'Fim',
            'MINUTOS': 'Duração (Min)',
            'Horas_Desde_Ultimo': 'Horas Desde Anterior',
            'Corridas_Desde_Ultimo': 'Corridas Desde Anterior'
        })

        if 'Horas Desde Anterior' in df_limpo.columns:
            df_limpo['Horas Desde Anterior'] = df_limpo['Horas Desde Anterior'].round(1)

        st.dataframe(df_limpo, use_container_width=True, hide_index=True)

        excel_data = converter_df_para_excel(df_limpo)
        st.download_button(
            label="📥 Baixar Base Limpa (.xlsx)",
            data=excel_data,
            file_name="base_reparo_canal_rotina.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )