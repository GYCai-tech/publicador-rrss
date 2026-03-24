import streamlit as st
from src.auth import check_password

# Verificar autenticación
if not check_password():
    st.stop()

import pandas as pd
from datetime import datetime
from src.db_config import get_all_email_send_logs, get_email_send_results, get_email_send_stats, mark_email_as_bounced
from src.graph_mail import fetch_ndr_bounces
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Dashboard de Envíos", page_icon="📊")

st.title("📊 Dashboard de Envíos de Email")
st.markdown("Visualiza estadísticas y resultados de tus operaciones de envío masivo de correos electrónicos.")

# Obtener estadísticas generales
try:
    stats = get_email_send_stats()
except Exception as e:
    st.error(f"Error al cargar estadísticas: {e}")
    stats = {
        'total_send_operations': 0,
        'total_emails_attempted': 0,
        'total_successful': 0,
        'total_failed': 0,
        'success_rate': 0
    }

# ==================== SECCIÓN 1: MÉTRICAS GENERALES ====================
st.header("📈 Métricas Generales")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total de Operaciones",
        value=stats['total_send_operations'],
        help="Número total de operaciones de envío masivo realizadas"
    )

with col2:
    st.metric(
        label="Emails Enviados",
        value=stats['total_successful'],
        delta=f"{stats['success_rate']:.1f}% tasa de éxito",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="Emails Fallidos",
        value=stats['total_failed'],
        delta=f"{100 - stats['success_rate']:.1f}% tasa de fallo",
        delta_color="inverse"
    )

with col4:
    st.metric(
        label="Total Procesados",
        value=stats['total_emails_attempted'],
        help="Número total de emails procesados (exitosos + fallidos)"
    )

# ==================== SECCIÓN 1b: DETECCIÓN DE REBOTES NDR ====================
st.header("📨 Detección de Rebotes")
st.markdown(
    "Busca en la bandeja del remitente los correos de error **'Undeliverable'** que llegan "
    "cuando un destinatario no existe, y los registra como fallos en este dashboard."
)

col_ndr1, col_ndr2 = st.columns([2, 1])
with col_ndr1:
    ndr_hours = st.slider("Buscar rebotes de las últimas N horas", min_value=1, max_value=168, value=48, step=1)
with col_ndr2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_ndr = st.button("🔍 Buscar rebotes ahora", use_container_width=True)

if run_ndr:
    with st.spinner("Leyendo bandeja de entrada en busca de rebotes..."):
        try:
            bounces = fetch_ndr_bounces(since_hours=ndr_hours)
        except Exception as e:
            st.error(f"Error al leer bandeja: {e}")
            bounces = []

    if not bounces:
        st.success("No se encontraron rebotes en el período seleccionado.")
    else:
        st.warning(f"Se encontraron **{len(bounces)} rebote(s)**. Actualizando dashboard...")
        updated_total = 0
        rows = []
        for b in bounces:
            n = mark_email_as_bounced(
                recipient_email=b['failed_email'],
                error_message=f"NDR recibido: {b['ndr_subject']}"
            )
            updated_total += n
            rows.append({
                'Email fallido': b['failed_email'],
                'Asunto original': b['original_subject'],
                'Rebote recibido': b['received_at'],
                'Registros actualizados': n
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if updated_total > 0:
            st.success(f"✅ {updated_total} registro(s) marcados como fallidos por rebote NDR. Recarga la página para ver las estadísticas actualizadas.")
        else:
            st.info("Los rebotes encontrados no coinciden con envíos registrados en el dashboard (puede que sean anteriores al período de logs).")

st.markdown("---")

# ==================== SECCIÓN 2: GRÁFICOS ====================
if stats['total_emails_attempted'] > 0:
    st.header("📊 Visualizaciones")

    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        # Gráfico de pastel: Exitosos vs Fallidos
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Exitosos', 'Fallidos'],
            values=[stats['total_successful'], stats['total_failed']],
            marker=dict(colors=['#00D26A', '#FF4B4B']),
            hole=.4
        )])
        fig_pie.update_layout(
            title="Distribución de Resultados",
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_graph2:
        # Gráfico de gauge: Tasa de éxito
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=stats['success_rate'],
            title={'text': "Tasa de Éxito (%)"},
            delta={'reference': 100, 'increasing': {'color': "#00D26A"}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "#00D26A"},
                'steps': [
                    {'range': [0, 50], 'color': "#FFE5E5"},
                    {'range': [50, 75], 'color': "#FFF4CC"},
                    {'range': [75, 100], 'color': "#E5F6E5"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

# ==================== SECCIÓN 3: HISTORIAL DE ENVÍOS ====================
st.header("📜 Historial de Envíos")

try:
    logs = get_all_email_send_logs()
except Exception as e:
    st.error(f"Error al cargar historial: {e}")
    logs = []

if logs:
    # Crear DataFrame para mostrar
    df_logs = pd.DataFrame(logs)

    # Formatear fechas
    df_logs['started_at'] = pd.to_datetime(df_logs['started_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
    df_logs['completed_at'] = pd.to_datetime(df_logs['completed_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # Calcular tasa de éxito por operación
    df_logs['success_rate'] = (df_logs['successful_count'] / df_logs['total_recipients'] * 100).round(2)

    # Filtros
    col_filter1, col_filter2 = st.columns(2)

    with col_filter1:
        filter_platform = st.multiselect(
            "Filtrar por plataforma",
            options=df_logs['platform'].unique(),
            default=df_logs['platform'].unique()
        )

    with col_filter2:
        filter_date = st.date_input(
            "Filtrar por fecha (desde)",
            value=None,
            help="Mostrar envíos desde esta fecha"
        )

    # Aplicar filtros
    df_filtered = df_logs[df_logs['platform'].isin(filter_platform)]
    if filter_date:
        df_filtered = df_filtered[pd.to_datetime(df_filtered['started_at']) >= pd.to_datetime(filter_date)]

    # Mostrar tabla resumen
    st.dataframe(
        df_filtered[[
            'id', 'platform', 'subject', 'started_at', 'total_recipients',
            'successful_count', 'failed_count', 'success_rate'
        ]].rename(columns={
            'id': 'ID',
            'platform': 'Plataforma',
            'subject': 'Asunto',
            'started_at': 'Fecha de Envío',
            'total_recipients': 'Total',
            'successful_count': 'Exitosos',
            'failed_count': 'Fallidos',
            'success_rate': 'Tasa de Éxito (%)'
        }),
        use_container_width=True,
        hide_index=True
    )

    # ==================== SECCIÓN 4: DETALLES DE UN ENVÍO ====================
    st.header("🔍 Detalles de Envío")

    selected_log_id = st.selectbox(
        "Selecciona un envío para ver detalles:",
        options=df_filtered['id'].tolist(),
        format_func=lambda x: f"ID {x} - {df_filtered[df_filtered['id']==x]['subject'].values[0][:50]}..."
    )

    if selected_log_id:
        # Obtener información del log seleccionado
        selected_log = df_filtered[df_filtered['id'] == selected_log_id].iloc[0]

        # Mostrar métricas del envío seleccionado
        col_detail1, col_detail2, col_detail3, col_detail4 = st.columns(4)

        with col_detail1:
            st.metric("Total Destinatarios", selected_log['total_recipients'])

        with col_detail2:
            st.metric("Exitosos", selected_log['successful_count'], delta_color="normal")

        with col_detail3:
            st.metric("Fallidos", selected_log['failed_count'], delta_color="inverse")

        with col_detail4:
            st.metric("Tasa de Éxito", f"{selected_log['success_rate']:.1f}%")

        # Obtener resultados individuales
        try:
            results = get_email_send_results(selected_log_id)

            if results:
                st.subheader("📋 Resultados Individuales")

                # Crear pestañas para exitosos y fallidos
                tab_success, tab_failed = st.tabs(["✅ Exitosos", "❌ Fallidos"])

                with tab_success:
                    successful_results = [r for r in results if r['success']]
                    if successful_results:
                        st.write(f"**{len(successful_results)} emails enviados exitosamente:**")
                        df_success = pd.DataFrame(successful_results)
                        st.dataframe(
                            df_success[['recipient_email', 'sent_at']].rename(columns={
                                'recipient_email': 'Email',
                                'sent_at': 'Enviado en'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )

                        # Botón para exportar exitosos
                        csv_success = df_success['recipient_email'].to_csv(index=False, header=['email'])
                        st.download_button(
                            label="📥 Descargar lista de exitosos (CSV)",
                            data=csv_success,
                            file_name=f"exitosos_{selected_log_id}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No hay emails exitosos en este envío.")

                with tab_failed:
                    failed_results = [r for r in results if not r['success']]
                    if failed_results:
                        st.write(f"**{len(failed_results)} emails fallidos:**")
                        df_failed = pd.DataFrame(failed_results)
                        st.dataframe(
                            df_failed[['recipient_email', 'error_code', 'error_message', 'sent_at']].rename(columns={
                                'recipient_email': 'Email',
                                'error_code': 'Código de Error',
                                'error_message': 'Mensaje de Error',
                                'sent_at': 'Intentado en'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )

                        # Análisis de errores
                        st.subheader("📈 Análisis de Errores")
                        error_counts = df_failed['error_code'].value_counts()

                        fig_errors = px.bar(
                            x=error_counts.index,
                            y=error_counts.values,
                            labels={'x': 'Tipo de Error', 'y': 'Cantidad'},
                            title="Distribución de Tipos de Error"
                        )
                        st.plotly_chart(fig_errors, use_container_width=True)

                        # Botón para exportar fallidos
                        csv_failed = df_failed[['recipient_email', 'error_code', 'error_message']].to_csv(index=False)
                        st.download_button(
                            label="📥 Descargar lista de fallidos (CSV)",
                            data=csv_failed,
                            file_name=f"fallidos_{selected_log_id}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success("¡Todos los emails se enviaron exitosamente!")
            else:
                st.info("No hay resultados individuales disponibles para este envío.")

        except Exception as e:
            st.error(f"Error al cargar resultados individuales: {e}")

else:
    st.info("No hay historial de envíos aún. Los envíos masivos se registrarán automáticamente aquí.")

# ==================== SECCIÓN 5: EXPORTAR DATOS ====================
st.header("📥 Exportar Datos")

col_export1, col_export2 = st.columns(2)

with col_export1:
    if logs:
        csv_all = pd.DataFrame(logs).to_csv(index=False)
        st.download_button(
            label="📊 Descargar todo el historial (CSV)",
            data=csv_all,
            file_name=f"historial_envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

with col_export2:
    st.write("**Próximamente:**")
    st.button("📧 Generar reporte PDF", disabled=True, use_container_width=True)

# Footer
st.markdown("---")
st.caption("Dashboard de Envíos - Actualizado automáticamente con cada operación de envío masivo")
