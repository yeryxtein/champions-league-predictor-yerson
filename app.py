"""Interfaz Streamlit. Todo el contenido del dataset llega desde FastAPI."""
from datetime import date, timedelta
import json
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
        # La primera predicción carga scikit-learn y el modelo en memoria.
        timeout = (3, 40 if route == "/predicciones" else 10)
        response = requests.post(API+route, json=body, timeout=timeout) if body is not None else requests.get(API+route, params=params, timeout=timeout)
        response.raise_for_status()
        return response.content if binary else response.json()
    except requests.RequestException as error:
        message = "No se pudo conectar con la API. Inicia el proyecto con INICIAR.cmd y vuelve a cargar."
        if isinstance(error, requests.ReadTimeout):
            message = "La API tardó demasiado en responder. La primera estimación puede demorar al cargar el modelo. Espera unos segundos y vuelve a intentarlo."
        elif isinstance(error, requests.ConnectTimeout):
            message = "No se pudo establecer la conexión con la API a tiempo. Comprueba que INICIAR.cmd siga abierto."
        if getattr(error, "response", None) is not None:
            try:
                detail = error.response.json().get("detail", message)
                message = detail if isinstance(detail, str) else "Revisa los equipos y la fecha de la consulta."
            except ValueError:
                pass
        st.error(message)
        st.stop()


catalog = request_api("/equipos")
model_info = request_api("/modelo")
with st.sidebar:
    st.title("Champions Lab")
    st.caption("Proyecto de Machine Learning")
    page = st.radio("Navegación", ["Explorar partidos", "Comparar equipos", "Predicción experimental", "Evaluación de mejoras", "Calidad de los datos", "Avance del proyecto"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Datos históricos**")
    st.write(f'{catalog["temporadas"][0]} a {catalog["temporadas"][-1]}')
    st.caption("Fase de grupos/liga y eliminatorias. Marcadores a 90 minutos.")
    st.link_button("Ver documentación de la API", API+"/docs", width="stretch")
    st.caption("Versión 0.4 · Modelo: " + ("entrenado" if model_info.get("estado") == "entrenado" else "pendiente") + ".")


def display_matches(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay partidos con estos filtros. Prueba otra temporada o equipo.")
        return
    df["Marcador 90 min"] = df.goles_local_90.astype(str) + " - " + df.goles_visitante_90.astype(str)
    view = df.rename(columns={"fecha":"Fecha", "temporada":"Temporada", "local":"Local", "visitante":"Visitante", "fase":"Fase", "resultado":"Resultado", "fuente":"Fuente"})
    st.dataframe(view[["Fecha", "Temporada", "Local", "Marcador 90 min", "Visitante", "Resultado", "Fase", "Fuente"]],
        hide_index=True, width="stretch", height=405,
        column_config={"Fuente":st.column_config.LinkColumn("Fuente", display_text="Consultar")})


if page == "Explorar partidos":
    st.title("Explorar partidos")
    st.write("Consulta los resultados históricos utilizados para preparar y evaluar el modelo.")
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
    st.caption(f'Fuente: OpenFootball, licencia CC0. Datos hasta el {date.fromisoformat(catalog["fecha_hasta"]).strftime("%d/%m/%Y")}.')

elif page == "Comparar equipos":
    st.title("Comparar equipos")
    st.write("Consulta la forma reciente de cada equipo y todos sus enfrentamientos directos disponibles antes de la fecha elegida.")
    with st.form("compare"):
        a,b,c = st.columns([1.5,1.5,1.1])
        local = a.selectbox("Equipo A", catalog["equipos"], index=catalog["equipos"].index("Real Madrid"))
        away = b.selectbox("Equipo B", catalog["equipos"], index=catalog["equipos"].index("Manchester City"))
        cut = c.date_input("Analizar partidos anteriores al", value=date.fromisoformat(catalog["fecha_hasta"])+timedelta(days=1), min_value=date.fromisoformat(catalog["fecha_desde"])+timedelta(days=1), max_value=date.fromisoformat(catalog["fecha_hasta"])+timedelta(days=1), format="DD/MM/YYYY", help="Se excluyen los partidos de ese día y los posteriores. La fecha máxima incluye todo el historial disponible.")
        sent = st.form_submit_button("Comparar historial", type="primary")
    if sent:
        st.session_state.pop("comparison_result", None)
        if local == away:
            st.error("Selecciona dos equipos diferentes para comparar.")
        else:
            with st.spinner("Consultando el historial en la API..."):
                st.session_state["comparison_result"]=request_api("/comparaciones", body={"local":local,"visitante":away,"fecha":cut.isoformat()})
    if "comparison_result" in st.session_state:
        data = st.session_state["comparison_result"]
        result_date = date.fromisoformat(data["fecha_corte"]).strftime("%d/%m/%Y")
        st.subheader(f'{data["local"]["equipo"]} frente a {data["visitante"]["equipo"]}')
        st.caption(f'Resultados de la última consulta: partidos anteriores al {result_date}. Si cambias los filtros, pulsa Comparar historial de nuevo.')
        recent_tab, direct_tab = st.tabs(["Últimos 5 partidos", "Enfrentamientos directos"])
        with recent_tab:
            st.write("Cada equipo tiene su propio historial de hasta cinco partidos, contra distintos rivales.")
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
                    st.dataframe(frame,hide_index=True,width="stretch")
        with direct_tab:
            h2h = data.get("enfrentamientos_directos")
            if h2h is None:
                st.warning("La API abierta corresponde a la versión anterior. Detén la terminal con Ctrl+C y vuelve a ejecutar INICIAR.cmd para ver los enfrentamientos directos.")
            else:
                st.write("Aquí se incluyen únicamente los partidos entre estos dos equipos, con cualquiera de ellos como local.")
                cols = st.columns(4)
                cols[0].metric("Enfrentamientos", h2h["partidos"])
                cols[1].metric(f'Victorias · {h2h["equipo_a"]}', h2h["victorias_equipo_a"])
                cols[2].metric("Empates", h2h["empates"])
                cols[3].metric(f'Victorias · {h2h["equipo_b"]}', h2h["victorias_equipo_b"])
                if not h2h["partidos"]:
                    st.info("No hay enfrentamientos directos entre estos equipos antes de la fecha elegida en este dataset. Puedes consultar su forma reciente en la otra pestaña.")
                else:
                    st.write(f'**Goles a 90 minutos:** {h2h["equipo_a"]}: {h2h["goles_equipo_a"]} · {h2h["equipo_b"]}: {h2h["goles_equipo_b"]}')
                    display_matches(h2h["encuentros"])
                    csv = pd.DataFrame(h2h["encuentros"]).to_csv(index=False).encode("utf-8-sig")
                    st.download_button("Descargar enfrentamientos en CSV", csv, file_name="enfrentamientos_champions.csv", mime="text/csv", key="download_h2h")
                st.caption(h2h["nota"])
                st.caption("Un partido puede figurar como empate a 90 minutos aunque un equipo haya ganado en la prórroga o en los penales.")
    else:
        st.info("Selecciona dos equipos y pulsa Comparar historial para ver las dos pestañas de resultados.")
    st.caption(f'Cobertura: {catalog["temporadas"][0]} a {catalog["temporadas"][-1]}, solo Champions. Esta comparación describe el historial disponible. Las estimaciones del modelo están en Predicción experimental.')

elif page == "Predicción experimental":
    st.title("Predicción experimental")
    st.write("El modelo estima el resultado **a 90 minutos**: victoria del local, empate o victoria del visitante.")
    if model_info.get("estado") != "entrenado":
        st.session_state.pop("prediction_result", None)
        st.info("El modelo no está disponible. Revisa el estado indicado antes de calcular una estimación.")
        st.caption(model_info.get("mensaje", "Estado del modelo pendiente."))
    else:
        validation = model_info["validacion"]["metricas"]
        evaluation = model_info["prueba"]
        test_metrics = evaluation["metricas_modelo"]
        baseline = evaluation["metricas_referencia"]
        st.caption(f'Modelo seleccionado: {model_info["modelo"]}. Se eligió con la temporada 2023-24 y se evaluó en 2024-25 ({test_metrics["partidos"]} partidos utilizables).')
        a,b,c,d = st.columns(4)
        a.metric("Exactitud en prueba", f'{test_metrics["accuracy"]:.1%}')
        b.metric("F1 macro en prueba", f'{test_metrics["f1_macro"]:.3f}')
        c.metric("Exactitud referencia", f'{baseline["accuracy"]:.1%}')
        d.metric("F1 macro referencia", f'{baseline["f1_macro"]:.3f}')
        if not evaluation["supera_referencia_f1_macro"]:
            st.warning("En la prueba, este modelo no superó la referencia simple en F1 macro. Interpreta sus resultados con cautela.")
        if test_metrics["matriz_confusion"][1][1] == 0 and test_metrics["soporte"]["Empate"]:
            st.warning(f'Limitación observada: el modelo no acertó ninguno de los {test_metrics["soporte"]["Empate"]} empates de la prueba. La mejora global frente a la referencia es modesta.')
        st.caption("Estas métricas pertenecen al modelo evaluado; el modelo reajustado con todos los datos todavía no tiene una prueba futura independiente.")
        with st.expander("Cómo se evaluó el modelo"):
            st.write("Se seleccionó por F1 macro en 2023-24, sin usar 2024-25 para elegirlo. La prueba exige cinco antecedentes por equipo y excluye sedes no auditadas.")
            st.dataframe(pd.DataFrame([
                {"Modelo":name,"Exactitud":metrics["accuracy"],"F1 macro":metrics["f1_macro"],"Log loss":metrics["log_loss"]}
                for name,metrics in validation.items()
            ]),hide_index=True,width="stretch")
            st.caption("Comparación de candidatos en validación 2023-24. La referencia usa las frecuencias de resultados del entrenamiento.")
            confusion = pd.DataFrame(test_metrics["matriz_confusion"],index=test_metrics["orden_clases"],columns=test_metrics["orden_clases"])
            st.dataframe(confusion,width="stretch")
            st.caption("Matriz de la prueba 2024-25: filas = resultado real; columnas = resultado estimado.")
        st.caption(f'Datos disponibles hasta {catalog["fecha_hasta"]}. Una fecha posterior usa ese historial; el sistema no consulta plantillas ni partidos actuales.')
        last_date = date.fromisoformat(catalog["fecha_hasta"])
        first_date = date.fromisoformat(model_info["artefactos"]["evaluado"]["entrenado_hasta"]) + timedelta(days=1)
        default_date = min(max(date.today(), last_date + timedelta(days=1)), last_date + timedelta(days=365))
        if st.button("Cargar ejemplo histórico", key="load_prediction_example"):
            st.session_state["predict_local"] = "Real Madrid"
            st.session_state["predict_away"] = "Manchester City"
            st.session_state["predict_date"] = date(2025, 2, 19)
            st.session_state["predict_neutral"] = False
            st.session_state.pop("prediction_result", None)
        st.caption("Ejemplo para la demostración: Real Madrid–Manchester City, 19/02/2025. Carga los datos y pulsa Calcular estimación.")
        for key, value in {"predict_local": "Real Madrid", "predict_away": "Manchester City", "predict_date": default_date, "predict_neutral": False}.items():
            if key not in st.session_state:
                st.session_state[key] = value
        with st.form("prediction"):
            x,y,z = st.columns([1.4,1.4,1])
            local = x.selectbox("Equipo local", catalog["equipos"], key="predict_local")
            away = y.selectbox("Equipo visitante", catalog["equipos"], key="predict_away")
            target_date = z.date_input("Fecha del escenario", min_value=first_date, max_value=last_date+timedelta(days=365), format="DD/MM/YYYY", key="predict_date", help="Solo se usan partidos anteriores a este día y un modelo entrenado antes de esta fecha.")
            neutral = st.checkbox("El partido se juega en sede neutral", key="predict_neutral", help="Este primer modelo no admite sedes neutrales porque el dataset no las marca de forma uniforme.")
            sent = st.form_submit_button("Calcular estimación", type="primary")
        if sent:
            st.session_state.pop("prediction_result", None)
            if local == away:
                st.error("Selecciona dos equipos diferentes.")
            elif neutral:
                st.error("Este primer modelo no admite partidos en sede neutral.")
            else:
                with st.spinner("Calculando la estimación en la API. La primera consulta puede tardar unos segundos..."):
                    st.session_state["prediction_result"] = request_api("/predicciones", body={"local":local,"visitante":away,"fecha":target_date.isoformat(),"sede_neutral":False})
        if "prediction_result" in st.session_state:
            result = st.session_state["prediction_result"]
            st.subheader(f'{result["local"]} frente a {result["visitante"]}')
            st.caption(f'Escenario consultado para el {date.fromisoformat(result["fecha_corte"]).strftime("%d/%m/%Y")}; modelo {result["version_modelo"]}, entrenado hasta {result["entrenado_hasta"]}.')
            if result.get("emitido_utc"):
                st.caption(f'Estimación emitida el {result["emitido_utc"]} (UTC). La descarga conserva la fecha de emisión y la versión utilizada.')
            st.caption("Estos son los resultados de la última consulta. Si cambias los equipos o la fecha, pulsa Calcular estimación de nuevo.")
            labels = [("Local",f'Gana {result["local"]}'),("Empate","Empate"),("Visitante",f'Gana {result["visitante"]}')]
            for slot,(key,label) in zip(st.columns(3),labels):
                slot.metric(label, f'{result["probabilidades"][key]:.1%}')
            st.write(f'**Resultado con mayor probabilidad estimada:** {dict(labels)[result["resultado_mas_probable"]]}')
            for warning in result["advertencias"]:
                st.caption("• " + warning)
            with st.expander("Qué datos usó el modelo"):
                rows = []
                for side in ["local", "visitante"]:
                    history = result["historial"][side]
                    rows.append({
                        "Equipo": history["equipo"],
                        "Partidos previos": history["partidos_usados"],
                        "Último partido usado": history["fecha_ultimo_partido"],
                        "Puntos / partido": result["variables"][f"{side}_puntos_5"],
                        "Goles a favor / partido": result["variables"][f"{side}_goles_favor_5"],
                        "Goles en contra / partido": result["variables"][f"{side}_goles_contra_5"],
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
                st.caption("Puntos: 3 por victoria, 1 por empate y 0 por derrota. Los promedios usan los últimos cinco partidos de Champions de cada equipo, contra cualquier rival. Los enfrentamientos directos todavía no son una variable del modelo.")
            st.download_button("Descargar estimación (JSON)", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"), file_name=f'estimacion_{result["fecha_corte"]}.json', mime="application/json", key="download_prediction")
        st.info("Son estimaciones experimentales basadas en cinco partidos previos de cada equipo. No garantizan el marcador ni consideran lesiones o alineaciones.")

elif page == "Evaluación de mejoras":
    st.title("Evaluación de mejoras")
    st.write("Comparación de nuevas variables y modelos mediante una prueba retrospectiva de 2025-26.")
    experiment = request_api("/experimentos/mejoras")
    if experiment.get("estado") != "evaluado":
        st.info(experiment.get("mensaje", "La evaluación todavía está pendiente."))
    else:
        test = experiment["prueba"]
        scores = test["metricas"]
        st.caption(f'La selección utilizó las temporadas {", ".join(experiment["validacion"]["temporadas"])}. Receta seleccionada: {experiment["elegido"]}.')
        a,b,c = st.columns(3)
        a.metric("Partidos de prueba disponibles", test["total"])
        b.metric("Partidos evaluados", test["utilizables"])
        c.metric("Partidos excluidos", test["excluidos"])
        st.caption("Los tres modelos se ajustaron con los mismos partidos elegibles anteriores a 2025-26 y se probaron en los mismos encuentros.")
        labels = {"elegido": "Modelo seleccionado", "rf6": "Random Forest con 6 variables", "referencia": "Referencia de clase mayoritaria"}
        rows = []
        for role, label in labels.items():
            metrics = scores[role]
            draws = metrics["empates"]
            rows.append({
                "Modelo": label,
                "Exactitud": f'{metrics["accuracy"]:.1%}',
                "F1 macro": round(metrics["f1_macro"], 3),
                "Log loss": round(metrics["log_loss"], 3),
                "Empates acertados": draws["aciertos"],
                "Empates reales": draws["reales"],
                "Empates pronosticados": draws["predichos"],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Exactitud y F1 macro se interpretan mejor cuanto mayores son. Log loss evalúa las probabilidades y se interpreta mejor cuanto menor es. Los empates acertados deben leerse junto a los reales y los pronosticados.")
        selected, base = scores["elegido"], scores["rf6"]
        st.write(f'Frente a Random Forest con seis variables, el modelo seleccionado presenta una diferencia de {(selected["accuracy"]-base["accuracy"])*100:+.2f} puntos porcentuales de exactitud, {selected["f1_macro"]-base["f1_macro"]:+.3f} de F1 macro y {selected["log_loss"]-base["log_loss"]:+.3f} de log loss.')
        st.info("La pantalla Predicción experimental utiliza el modelo de la primera versión. Aquí se documentan los resultados de la evaluación ampliada para decidir la siguiente versión.")
        with st.expander("Selección anterior a la prueba"):
            st.write("Se compararon cinco recetas. Cada temporada de validación se predijo con un modelo entrenado en temporadas anteriores. Se eligió por la media de F1 macro, con desempate por menor log loss y luego por nombre.")
            validation_rows = []
            for name, metrics in experiment["validacion"]["candidatos"].items():
                validation_rows.append({"Receta": name, "F1 macro medio": metrics["f1_macro_medio"], "Log loss medio": metrics["log_loss_medio"]})
            st.dataframe(pd.DataFrame(validation_rows), hide_index=True, width="stretch")
            st.write(f'Variables del modelo seleccionado ({len(experiment["variables_elegido"])}):')
            st.write(", ".join(experiment["variables_elegido"]))
        with st.expander("Resultados por clase"):
            matrix = pd.DataFrame(selected["matriz_confusion"], index=selected["orden_clases"], columns=selected["orden_clases"])
            st.dataframe(matrix, width="stretch")
            st.caption("Modelo seleccionado. Filas = resultado real. Columnas = resultado estimado.")
            if test["motivos_exclusion"]:
                st.write("Motivos de exclusión")
                st.dataframe(pd.DataFrame([{"Motivo": reason, "Partidos": count} for reason,count in test["motivos_exclusion"].items()]), hide_index=True, width="stretch")
        st.subheader("Alcance de la evaluación")
        for limitation in experiment["limitaciones"]:
            st.write("• " + limitation)
        st.download_button("Descargar evaluación (JSON)", json.dumps(experiment, ensure_ascii=False, indent=2).encode("utf-8"), file_name="evaluacion_mejoras_2025-26.json", mime="application/json", key="download_experiment")

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
        st.dataframe(pd.DataFrame([{"Temporada":k,"Partidos":v} for k,v in report["temporadas"].items()]),hide_index=True,width="stretch")
    with b:
        st.subheader("Preparación realizada")
        st.write(f'Conversión de {len(report["temporadas"])} archivos de texto a CSV. {report["nombres_unificados"]} variantes de nombres unificadas mediante un mapa explícito.')
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
    st.success("API e interfaz: exploración, forma reciente, enfrentamientos directos, predicción experimental y evaluación ampliada.")
    st.subheader("Objetivos y evidencia disponible")
    st.dataframe(pd.DataFrame([
        {"Objetivo":"Preparar datos","Estado":"Primera versión lista","Evidencia":f'{len(catalog["temporadas"])} temporadas, CSV, diccionario y reporte de calidad'},
        {"Objetivo":"Construir variables previas","Estado":"Comparación histórica lista","Evidencia":"Últimos 5 partidos y todos los cruces directos anteriores al corte"},
        {"Objetivo":"Entrenar y evaluar","Estado":"Modelo entrenado" if model_info.get("estado") == "entrenado" else "Pendiente","Evidencia":"Métricas de prueba 2024-25" if model_info.get("estado") == "entrenado" else "Plan temporal y código inicial"},
        {"Objetivo":"Desarrollar API propia","Estado":"Implementada","Evidencia":"Datos, resumen, calidad, comparación y predicción por HTTP"},
        {"Objetivo":"Crear interfaz con UI/UX","Estado":"Prototipo funcional","Evidencia":"Filtros, tablas, descarga, estados vacíos y validación"},
        {"Objetivo":"Analizar resultados del modelo","Estado":"En progreso" if model_info.get("estado") == "entrenado" else "Pendiente","Evidencia":"Comparación con referencia simple" if model_info.get("estado") == "entrenado" else "Sin métricas predictivas todavía"},
    ]),hide_index=True,width="stretch")
    st.subheader("Recorrido para la exposición")
    st.write("1. Filtra una temporada y muestra los resultados en **Explorar partidos**.")
    st.write("2. Revisa los conteos y la procedencia en **Calidad de los datos**.")
    st.write("3. Compara Real Madrid y Manchester City con corte 02/06/2024. Abre Enfrentamientos directos y muestra los 8 cruces disponibles a 90 minutos.")
    st.write("4. En **Predicción experimental**, pulsa **Cargar ejemplo histórico** y luego **Calcular estimación**. Explica las probabilidades y abre **Qué datos usó el modelo**.")
    st.write("5. Abre **la documentación de la API** y ejecuta una consulta GET /resumen o POST /predicciones.")
    st.write("6. En **Evaluación de mejoras**, revisa la comparación retrospectiva de 2025-26 y sus resultados por clase.")
    st.subheader("Siguiente entrega")
    if model_info.get("estado") == "entrenado":
        st.write("Auditar más sedes, mejorar variables y comprobar la calibración de probabilidades. El modelo reajustado necesita una prueba futura independiente.")
        st.info("Las estimaciones del modelo son experimentales. Los enfrentamientos directos son un resumen descriptivo.")
    else:
        st.write("Incorporar y validar las temporadas 2024-25 y 2025-26. Completar la tabla de variables y comparar una referencia simple, regresión logística y Random Forest con separación temporal.")
        st.info("No se ha entrenado un modelo. La comparación histórica no calcula probabilidades ni demuestra capacidad predictiva.")
