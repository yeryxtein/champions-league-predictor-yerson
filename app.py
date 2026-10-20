"""Interfaz Streamlit. Todo el contenido del dataset llega desde FastAPI."""
from datetime import date, timedelta
import os
import pandas as pd
import requests
import streamlit as st

API = os.environ.get("CHAMPIONS_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Champions Lab", page_icon="⚽", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1340px; padding-top: 2.4rem;}
h1 {letter-spacing: -.035em; font-weight: 750;}
h2,h3 {letter-spacing: -.018em;}
[data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700;}
[data-testid="stSidebar"] {border-right: 1px solid #dbe4f1;}
div[data-testid="stAlert"] p {font-size: 1rem;}
</style>""", unsafe_allow_html=True)


def request_api(route, params=None, body=None, binary=False):
    try:
        response = requests.post(API+route, json=body, timeout=10) if body is not None else requests.get(API+route, params=params, timeout=10)
        response.raise_for_status()
        return response.content if binary else response.json()
    except requests.RequestException as error:
        message = "No se pudo conectar con la API. Inicia el proyecto con INICIAR.cmd y vuelve a cargar."
        if getattr(error, "response", None) is not None:
            try:
                detail = error.response.json().get("detail", message)
                message = detail if isinstance(detail, str) else "Revisa los equipos y la fecha de la consulta."
            except ValueError:
                pass
        st.error(message)
        st.stop()


catalog = request_api("/equipos")
with st.sidebar:
    st.title("Champions Lab")
    st.caption("Proyecto de Machine Learning")
    page = st.radio("Navegación", ["Explorar partidos", "Comparar equipos", "Calidad de los datos", "Avance del proyecto"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Datos históricos**")
    st.write("2016/17 a 2023/24")
    st.caption("Grupos y eliminatorias. Marcadores a 90 minutos.")
    st.link_button("Ver documentación de la API", API+"/docs", use_container_width=True)
    st.caption("Versión 0.1 · API y exploración listas. Modelo predictivo pendiente.")


def display_matches(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay partidos con estos filtros. Prueba otra temporada o equipo.")
        return
    df["Marcador 90 min"] = df.goles_local_90.astype(str) + " - " + df.goles_visitante_90.astype(str)
    view = df.rename(columns={"fecha":"Fecha", "temporada":"Temporada", "local":"Local", "visitante":"Visitante", "fase":"Fase", "resultado":"Resultado", "fuente":"Fuente"})
    st.dataframe(view[["Fecha", "Temporada", "Local", "Marcador 90 min", "Visitante", "Resultado", "Fase", "Fuente"]],
        hide_index=True, use_container_width=True, height=405,
        column_config={"Fuente":st.column_config.LinkColumn("Fuente", display_text="Consultar")})


if page == "Explorar partidos":
    st.title("Explorar partidos")
    st.write("Consulta los resultados históricos que servirán para construir el modelo.")
    filters = st.columns([1.2,1.8,1.1,1.2])
    season = filters[0].selectbox("Temporada", ["Todas"]+list(reversed(catalog["temporadas"])))
    team = filters[1].selectbox("Equipo", ["Todos"]+catalog["equipos"])
    result = filters[2].selectbox("Resultado", ["Todos", "Local", "Empate", "Visitante"])
    phase = filters[3].selectbox("Fase", ["Todas"]+catalog["fases"])
    params = {k:v for k,v in {"temporada":season,"equipo":team,"resultado":result,"fase":phase}.items() if v not in ["Todos","Todas"]}
    summary = request_api("/resumen", params)
    metrics = st.columns(4)
    for slot,label,value in zip(metrics,["Partidos","Equipos","Goles a 90 min","Goles por partido"],[summary["partidos"],summary["equipos"],summary["goles"],summary["promedio_goles"]]):
        slot.metric(label,value)
    st.caption("Local y visitante son las designaciones de la fuente. Algunas eliminatorias se jugaron en sede neutral.")
    result_rows = [{"Resultado":k,"Partidos":v} for k,v in summary["resultados"].items()]
    a,b = st.columns([2.4,1])
    with a:
        st.subheader("Partidos del historial")
        matches = request_api("/partidos", params)
        display_matches(matches["partidos"])
        st.download_button("Descargar selección en CSV", request_api("/descargar", params, binary=True), file_name="partidos_champions.csv", mime="text/csv")
    with b:
        st.subheader("Resultados a 90 minutos")
        if summary["partidos"]:
            st.bar_chart(pd.DataFrame(result_rows), x="Resultado", y="Partidos", color="#185BCE", height=300)
            for item in result_rows:
                st.write(f'**{item["Resultado"]}:** {item["Partidos"]} ({item["Partidos"]/summary["partidos"]:.1%})')
        else:
            st.info("Sin datos para graficar.")
    st.caption("Fuente: OpenFootball, licencia CC0. Datos hasta el 1 de junio de 2024.")

elif page == "Comparar equipos":
    st.title("Comparar equipos")
    st.write("Revisa hasta cinco partidos anteriores a una fecha de corte. Este resumen histórico todavía no predice un ganador.")
    with st.form("compare"):
        a,b,c = st.columns([1.5,1.5,1.1])
        local = a.selectbox("Equipo local", catalog["equipos"], index=catalog["equipos"].index("Real Madrid"))
        away = b.selectbox("Equipo visitante", catalog["equipos"], index=catalog["equipos"].index("Manchester City"))
        cut = c.date_input("Fecha de corte (exclusiva)", value=date(2024,4,9), min_value=date.fromisoformat(catalog["fecha_desde"])+timedelta(days=1), max_value=date.fromisoformat(catalog["fecha_hasta"])+timedelta(days=1), format="DD/MM/YYYY")
        sent = st.form_submit_button("Comparar historial", type="primary")
    if sent:
        if local == away:
            st.error("Selecciona dos equipos diferentes para comparar.")
        else:
            with st.spinner("Consultando el historial en la API..."):
                data=request_api("/comparaciones", body={"local":local,"visitante":away,"fecha":cut.isoformat()})
            st.caption(f'Solo se incluyen encuentros anteriores al {cut.strftime("%d/%m/%Y")}. Historial de Champions, sin otras competiciones.')
            for col,side in zip(st.columns(2),["local","visitante"]):
                item=data[side]
                with col:
                    st.subheader(item["equipo"])
                    st.write(f'**{item["partidos_usados"]} partidos utilizados** · {item["victorias"]} victorias · {item["empates"]} empates · {item["derrotas"]} derrotas')
                    if item["partidos_usados"] < 5:
                        st.warning("Hay menos de cinco partidos previos disponibles en este dataset.")
                    p,q=st.columns(2)
                    p.metric("Goles a favor / partido",item["promedio_goles_favor"] if item["promedio_goles_favor"] is not None else "Sin datos")
                    q.metric("Goles en contra / partido",item["promedio_goles_contra"] if item["promedio_goles_contra"] is not None else "Sin datos")
                    frame=pd.DataFrame(item["ultimos_partidos"]).rename(columns={"fecha":"Fecha","rival":"Rival","condicion":"Condición","goles_favor":"GF","goles_contra":"GC","resultado_equipo":"Resultado"})
                    st.dataframe(frame,hide_index=True,use_container_width=True)
    st.info("Próxima etapa: entrenar y evaluar el modelo antes de habilitar probabilidades de victoria.")

elif page == "Calidad de los datos":
    st.title("Calidad y procedencia")
    report=request_api("/calidad")
    st.write("Controles realizados sobre la copia descargada. La integridad estructural no equivale a verificar cada resultado contra UEFA.")
    cols=st.columns(4)
    for col,label,value in zip(cols,["Partidos procesados","Duplicados","Campos exportados vacíos","Prórrogas identificadas"],[report["partidos"],report["duplicados"],report["faltantes_campos_exportados"],report["prorrogas"]]):
        col.metric(label,value)
    a,b=st.columns([1,1.5])
    with a:
        st.subheader("Cobertura por temporada")
        st.dataframe(pd.DataFrame([{"Temporada":k,"Partidos":v} for k,v in report["temporadas"].items()]),hide_index=True,use_container_width=True)
    with b:
        st.subheader("Preparación realizada")
        st.write(f'Conversión de ocho archivos de texto a CSV. {report["nombres_unificados"]} variantes de nombres unificadas mediante un mapa explícito.')
        st.write(f'{report["prorrogas"]} partidos con prórroga, incluidos {report["penales"]} con tanda de penales. Se conserva el marcador de los 90 minutos y el texto original.')
        st.write("Verificación de fechas, días de semana, partidos duplicados y conteos declarados por la fuente. Cada fila conserva un enlace a su línea original.")
        st.link_button("Abrir fuente original", report["fuente"]["repositorio"])
        st.caption("Versión del repositorio: "+report["fuente"]["commit"][:12]+" · Licencia CC0-1.0")
    st.subheader("Límites que debemos tener en cuenta")
    for item in report["limitaciones"]:
        st.write("- "+item)

else:
    st.title("Avance del proyecto")
    st.write("Sistema de predicción de resultados de Champions League")
    st.success("Primera versión funcional: dataset preparado, API propia e interfaz conectada.")
    st.subheader("Objetivos y evidencia disponible")
    st.dataframe(pd.DataFrame([
        {"Objetivo":"Preparar datos","Estado":"Primera versión lista","Evidencia":"8 temporadas, CSV, diccionario y reporte de calidad"},
        {"Objetivo":"Construir variables previas","Estado":"En progreso","Evidencia":"Consulta de los últimos 5 partidos anteriores al corte"},
        {"Objetivo":"Entrenar y evaluar","Estado":"Pendiente","Evidencia":"Plan temporal y modelos propuestos"},
        {"Objetivo":"Desarrollar API propia","Estado":"Consulta implementada","Evidencia":"Datos, resumen, calidad y comparación por HTTP"},
        {"Objetivo":"Crear interfaz con UI/UX","Estado":"Prototipo funcional","Evidencia":"Filtros, tablas, descarga, estados vacíos y validación"},
        {"Objetivo":"Analizar resultados del modelo","Estado":"Pendiente","Evidencia":"Sin métricas predictivas todavía"},
    ]),hide_index=True,use_container_width=True)
    st.subheader("Recorrido para la exposición")
    st.write("1. Filtra una temporada y muestra los resultados en **Explorar partidos**.")
    st.write("2. Revisa los conteos y la procedencia en **Calidad de los datos**.")
    st.write("3. Compara dos equipos antes de una fecha y explica por qué se excluye el partido que se quiere predecir.")
    st.write("4. Abre **la documentación de la API** y ejecuta una consulta GET /resumen.")
    st.subheader("Siguiente entrega")
    st.write("Construir la tabla de variables para entrenamiento. Comparar una referencia simple, regresión logística y Random Forest con separación temporal. Después habilitar /predicciones y probar la interfaz con compañeros.")
    st.info("No se ha entrenado un modelo. La comparación histórica no calcula probabilidades ni demuestra capacidad predictiva.")
