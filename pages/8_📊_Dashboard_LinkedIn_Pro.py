import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.linkedin import LinkedInClient
from src.ui_components import render_header
from src.auth import check_password

# --- Page config ---
st.set_page_config(
    page_title="LinkedIn Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_header()

if not check_password():
    st.stop()

# --- Clean SaaS CSS ---
st.markdown("""
<style>
    /* Base reset */
    .block-container { padding-top: 2rem; }

    /* KPI metric cards */
    .metric-card {
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 24px 20px;
        text-align: left;
        transition: box-shadow 0.2s ease;
    }
    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        background: rgba(255,255,255,0.10);
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #d1d5db;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #f9fafb;
        line-height: 1.2;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #9ca3af;
        font-weight: 400;
    }

    /* Accent dot indicators */
    .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .dot-blue { background: #3b82f6; }
    .dot-green { background: #10b981; }
    .dot-amber { background: #f59e0b; }
    .dot-rose { background: #f43f5e; }

    /* Section titles */
    .section-title {
        font-size: 1rem;
        font-weight: 600;
        color: #e5e7eb;
        padding: 12px 0 8px 0;
        margin-top: 24px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 16px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 0;
        padding: 12px 24px;
        font-weight: 500;
        font-size: 0.9rem;
        color: #9ca3af;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: #f9fafb !important;
        border-bottom: 2px solid #3b82f6 !important;
    }

    /* Page title */
    h1 {
        font-weight: 700;
        color: #f9fafb;
        font-size: 1.75rem !important;
        margin-bottom: 4px;
    }

    /* Subtitle text */
    .page-subtitle {
        color: #9ca3af;
        font-size: 0.9rem;
        margin-bottom: 24px;
    }

    /* Clean divider */
    hr { border: none; border-top: 1px solid #f3f4f6; margin: 24px 0; }

    /* Dataframe styling */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Footer */
    .dashboard-footer {
        text-align: center;
        color: #6b7280;
        font-size: 0.75rem;
        padding: 32px 0 16px 0;
    }

    /* Force high contrast on Streamlit native elements */
    .stMarkdown p, .stMarkdown li { color: #d1d5db; }
    .stMarkdown strong { color: #f3f4f6; }
</style>
""", unsafe_allow_html=True)

# --- Plotly theme ---
CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#06b6d4"]
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#d1d5db", size=12),
    margin=dict(l=16, r=16, t=24, b=16),
    xaxis=dict(showgrid=False, zeroline=False, color="#9ca3af"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, color="#9ca3af"),
)


def metric_card(label, value, sub="", dot_color="blue"):
    return f"""
    <div class="metric-card">
        <div class="metric-label"><span class="dot dot-{dot_color}"></span>{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """


# --- LinkedIn client ---
@st.cache_resource
def get_linkedin_client():
    return LinkedInClient()

try:
    api = get_linkedin_client()
except Exception as e:
    st.error(f"Error al conectar con LinkedIn: {e}")
    st.stop()

# --- Header ---
st.title("LinkedIn Analytics")
st.markdown('<p class="page-subtitle">Rendimiento de publicaciones y audiencia</p>', unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### Filtros")

    date_preset = st.selectbox(
        "Periodo",
        ["7 dias", "30 dias", "90 dias", "Personalizado"],
        index=1
    )

    if date_preset == "Personalizado":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Desde", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Hasta", datetime.now())
    else:
        days_map = {"7 dias": 7, "30 dias": 30, "90 dias": 90}
        days = days_map[date_preset]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

    st.divider()

    num_posts = st.slider("Posts a analizar", 5, 50, 20, 5)

    content_filter = st.multiselect(
        "Tipo de contenido",
        ["Texto", "Imagen/Video", "Carrusel", "Articulo", "Encuesta"],
        default=["Texto", "Imagen/Video", "Carrusel"]
    )

    st.divider()

    show_demographics = st.checkbox("Demograficos", value=True)

    st.divider()

    if st.button("Actualizar datos", type="primary", use_container_width=True):
        st.session_state['refresh_data'] = True
        st.cache_data.clear()
        st.rerun()

# ==============================================================================
# TABS
# ==============================================================================
tab_overview, tab_content, tab_audience, tab_comparison = st.tabs([
    "Overview",
    "Contenido",
    "Audiencia",
    "Comparativa"
])

# ==============================================================================
# TAB 1: OVERVIEW
# ==============================================================================
with tab_overview:

    # Load data
    if 'linkedin_data_pro' not in st.session_state or st.session_state.get('refresh_data', False):
        with st.spinner("Cargando datos de LinkedIn..."):
            try:
                posts_data = api.get_recent_posts_details(count=num_posts)

                if posts_data:
                    post_ids = [p['post_id'] for p in posts_data]
                    df_metrics = api.get_post_metrics(post_ids)

                    if df_metrics is not None and not df_metrics.empty:
                        df_posts = pd.DataFrame(posts_data)
                        df_final = pd.merge(df_posts, df_metrics, on='post_id', how='left')

                        if content_filter:
                            df_final = df_final[df_final['tipo'].isin(content_filter)]

                        if not df_final.empty:
                            st.session_state['linkedin_data_pro'] = df_final
                            st.session_state['refresh_data'] = False
                        else:
                            st.warning("No hay posts que coincidan con los filtros seleccionados.")
                            st.stop()
                    else:
                        st.error("No se pudieron obtener metricas de la API de LinkedIn.")
                        with st.expander("Debug"):
                            st.write(f"Posts encontrados: {len(posts_data)}")
                            for i, pid in enumerate(post_ids[:3]):
                                st.code(pid)
                            st.write(f"Tipo respuesta: {type(df_metrics)}")
                            if df_metrics is not None:
                                st.write(f"Shape: {df_metrics.shape}")
                        st.stop()
                else:
                    st.warning("No se encontraron publicaciones en tu cuenta de LinkedIn.")
                    st.stop()

            except Exception as e:
                st.error(f"Error al cargar datos: {e}")
                with st.expander("Detalles"):
                    import traceback
                    st.code(traceback.format_exc())
                st.stop()

    df = st.session_state.get('linkedin_data_pro')

    if df is not None and not df.empty:

        # --- KPI Cards ---
        total_impressions = df['impresiones'].sum() if 'impresiones' in df.columns else df.get('impression', pd.Series([0])).sum()
        total_clicks = df.get('clics', pd.Series([0])).sum()
        total_likes = df.get('likes', pd.Series([0])).sum()
        total_comments = df.get('comentarios', pd.Series([0])).sum()
        total_shares = df.get('compartidos', pd.Series([0])).sum()
        total_engagement = total_likes + total_comments + total_shares + total_clicks
        avg_er = df['ER%'].mean()

        kpi_cols = st.columns(4, gap="medium")

        with kpi_cols[0]:
            st.markdown(metric_card("Impresiones", f"{total_impressions:,.0f}", "Alcance total", "blue"), unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(metric_card("Engagement", f"{total_engagement:,.0f}", f"{total_likes:,.0f} likes  {total_comments:,.0f} comentarios", "green"), unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(metric_card("Clics", f"{total_clicks:,.0f}", "Clicks en enlaces", "amber"), unsafe_allow_html=True)
        with kpi_cols[3]:
            er_dot = "green" if avg_er > 5 else "amber" if avg_er > 2 else "rose"
            st.markdown(metric_card("Engagement Rate", f"{avg_er:.2f}%", "Tasa promedio", er_dot), unsafe_allow_html=True)

        st.markdown("")

        # --- Charts ---
        st.markdown('<div class="section-title">Rendimiento de publicaciones</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2, gap="medium")

        with col1:
            if 'fecha' in df.columns and not df['fecha'].isna().all():
                df_temp = df.copy()
                df_temp['fecha_dt'] = pd.to_datetime(df_temp['fecha'], errors='coerce')
                df_sorted = df_temp.dropna(subset=['fecha_dt']).sort_values('fecha_dt')

                if not df_sorted.empty:
                    imp_col = 'impresiones' if 'impresiones' in df_sorted.columns else 'impression'
                    fig_bars = go.Figure(go.Bar(
                        x=df_sorted['fecha'],
                        y=df_sorted[imp_col],
                        marker_color="#3b82f6",
                                            ))
                    fig_bars.update_layout(
                        **CHART_LAYOUT,
                        height=320,
                        title=dict(text="Impresiones por post", font=dict(size=14, color="#e5e7eb")),
                        yaxis_title="",
                        xaxis_title="",
                    )
                    st.plotly_chart(fig_bars, use_container_width=True)
            else:
                st.info("No hay datos de fecha disponibles")

        with col2:
            engagement_data = pd.DataFrame({
                'Tipo': ['Likes', 'Comentarios', 'Compartidos', 'Clics'],
                'Cantidad': [
                    df.get('likes', df.get('reaction', pd.Series([0]))).sum(),
                    df.get('comentarios', df.get('comment', pd.Series([0]))).sum(),
                    df.get('compartidos', df.get('reshare', pd.Series([0]))).sum(),
                    df.get('clics', df.get('click_count', pd.Series([0]))).sum()
                ]
            })

            fig_engagement = go.Figure(go.Bar(
                x=engagement_data['Tipo'],
                y=engagement_data['Cantidad'],
                marker_color=CHART_COLORS[:4],
                                text=engagement_data['Cantidad'],
                textposition='outside',
                texttemplate='%{text:,.0f}',
            ))
            fig_engagement.update_layout(
                **CHART_LAYOUT,
                height=320,
                title=dict(text="Distribucion de engagement", font=dict(size=14, color="#e5e7eb")),
                yaxis_title="",
                xaxis_title="",
                showlegend=False,
            )
            st.plotly_chart(fig_engagement, use_container_width=True)

        # --- Top Posts ---
        st.markdown('<div class="section-title">Top 5 publicaciones por engagement</div>', unsafe_allow_html=True)

        top_posts = df.nlargest(5, 'ER%')[['texto_corto', 'impresiones', 'likes', 'comentarios', 'ER%']].copy()
        top_posts.columns = ['Contenido', 'Impresiones', 'Likes', 'Comentarios', 'ER%']

        st.dataframe(
            top_posts,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Contenido": st.column_config.TextColumn("Contenido", width="large"),
                "Impresiones": st.column_config.NumberColumn("Impresiones", format="%d"),
                "Likes": st.column_config.NumberColumn("Likes", format="%d"),
                "Comentarios": st.column_config.NumberColumn("Comentarios", format="%d"),
                "ER%": st.column_config.ProgressColumn(
                    "Engagement %",
                    format="%.2f%%",
                    min_value=0,
                    max_value=float(df['ER%'].max()) if df['ER%'].max() > 0 else 10
                )
            },
            height=250
        )

        # --- Secondary metrics ---
        st.markdown('<div class="section-title">Resumen de metricas</div>', unsafe_allow_html=True)

        sec_cols = st.columns(4, gap="medium")
        avg_impressions = df.get('impresiones', df.get('impression', pd.Series([0]))).mean()

        with sec_cols[0]:
            st.metric("Reacciones totales", f"{total_likes:,.0f}")
        with sec_cols[1]:
            st.metric("Comentarios totales", f"{total_comments:,.0f}")
        with sec_cols[2]:
            st.metric("Compartidos totales", f"{total_shares:,.0f}")
        with sec_cols[3]:
            st.metric("Impresiones promedio", f"{avg_impressions:,.0f}")

# ==============================================================================
# TAB 2: CONTENT ANALYSIS
# ==============================================================================
with tab_content:
    st.markdown('<div class="section-title">Analisis de contenido</div>', unsafe_allow_html=True)

    if df is not None and not df.empty:
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            available_metrics = [m for m in ["ER%", "impresiones", "likes", "comentarios", "compartidos", "clics"] if m in df.columns]
            sort_metric = st.selectbox("Ordenar por", available_metrics, index=0 if "ER%" in available_metrics else 0)

        with col_f2:
            sort_order = st.radio("Orden", ["Descendente", "Ascendente"], horizontal=True)

        with col_f3:
            show_details = st.checkbox("Mostrar detalles completos", value=False)

        # Performance by content type
        st.markdown('<div class="section-title">Rendimiento por tipo</div>', unsafe_allow_html=True)

        if 'tipo' in df.columns:
            content_analysis = df.groupby('tipo').agg({
                'impresiones': 'sum' if 'impresiones' in df.columns else lambda x: df.get('impression', 0).sum(),
                'ER%': 'mean',
                'post_id': 'count'
            }).reset_index()

            content_analysis.columns = ['Tipo', 'Impresiones Totales', 'ER% Promedio', 'Cantidad']
            content_analysis = content_analysis.sort_values('ER% Promedio', ascending=False)

            st.dataframe(
                content_analysis,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tipo": st.column_config.TextColumn("Tipo de Contenido", width="medium"),
                    "Cantidad": st.column_config.NumberColumn("Posts", format="%d"),
                    "Impresiones Totales": st.column_config.NumberColumn("Impresiones", format="%d"),
                    "ER% Promedio": st.column_config.ProgressColumn(
                        "Engagement %",
                        format="%.2f%%",
                        min_value=0,
                        max_value=float(content_analysis['ER% Promedio'].max()) if not content_analysis.empty else 10
                    )
                }
            )

        # Detailed table
        st.markdown('<div class="section-title">Detalle de publicaciones</div>', unsafe_allow_html=True)

        df_sorted = df.sort_values(by=sort_metric, ascending=(sort_order == "Ascendente"))

        if show_details:
            cols_display = ['fecha', 'texto_completo', 'tipo', 'impresiones', 'ER%', 'likes', 'comentarios', 'compartidos', 'clics']
        else:
            cols_display = ['fecha', 'texto_corto', 'tipo', 'impresiones', 'ER%', 'likes', 'comentarios']

        cols_display = [col for col in cols_display if col in df_sorted.columns]

        st.dataframe(
            df_sorted[cols_display],
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
                "texto_corto": st.column_config.TextColumn("Contenido", width="medium"),
                "texto_completo": st.column_config.TextColumn("Contenido Completo", width="large"),
                "impresiones": st.column_config.NumberColumn("Impresiones", format="%d"),
                "ER%": st.column_config.ProgressColumn(
                    "Engagement %",
                    format="%.2f%%",
                    min_value=0,
                    max_value=float(df['ER%'].max()) if df['ER%'].max() > 0 else 10
                ),
                "likes": st.column_config.NumberColumn("Likes", format="%d"),
                "comentarios": st.column_config.NumberColumn("Comentarios", format="%d")
            },
            height=400
        )

        csv = df_sorted[cols_display].to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv,
            file_name=f"linkedin_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ==============================================================================
# TAB 3: AUDIENCE
# ==============================================================================
with tab_audience:
    st.markdown('<div class="section-title">Audiencia</div>', unsafe_allow_html=True)

    col_aud1, col_aud2 = st.columns([3, 1])

    with col_aud2:
        if st.button("Cargar datos de audiencia", use_container_width=True):
            st.session_state['audience_loaded'] = True

    if st.session_state.get('audience_loaded', False):
        with st.spinner("Analizando audiencia..."):

            st.markdown('<div class="section-title">Segmentacion demografica</div>', unsafe_allow_html=True)

            seg_col1, seg_col2 = st.columns(2, gap="medium")

            with seg_col1:
                st.markdown("**Ubicacion geografica (Top 10)**")
                df_geo = api.get_follower_segmentation("GEOGRAPHIC_AREA")

                if df_geo is not None and not df_geo.empty:
                    df_geo_top = df_geo.head(10).sort_values('seguidores', ascending=True)

                    fig_geo = go.Figure(go.Bar(
                        y=df_geo_top['segmento'],
                        x=df_geo_top['seguidores'],
                        orientation='h',
                        marker_color="#3b82f6",
                                                text=df_geo_top['seguidores'],
                        texttemplate='%{text:,.0f}',
                        textposition='outside',
                    ))
                    fig_geo.update_layout(
                        **CHART_LAYOUT,
                        height=400,
                        yaxis_title="",
                        xaxis_title="Seguidores",
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                else:
                    st.info("No hay datos geograficos disponibles")

            with seg_col2:
                st.markdown("**Nivel de experiencia**")
                df_seniority = api.get_follower_segmentation("SENIORITY")

                if df_seniority is not None and not df_seniority.empty:
                    fig_sen = go.Figure(go.Pie(
                        values=df_seniority['seguidores'],
                        labels=df_seniority['segmento'],
                        hole=0.5,
                        marker=dict(colors=CHART_COLORS),
                        textposition='inside',
                        textinfo='percent+label',
                    ))
                    fig_sen.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter, system-ui, sans-serif", color="#d1d5db", size=12),
                        height=400,
                        showlegend=False,
                        margin=dict(l=16, r=16, t=24, b=16),
                    )
                    st.plotly_chart(fig_sen, use_container_width=True)
                else:
                    st.info("No hay datos de seniority disponibles")

            st.markdown("")

            ind_col1, ind_col2 = st.columns(2, gap="medium")

            with ind_col1:
                st.markdown("**Top 10 sectores industriales**")
                df_ind = api.get_follower_segmentation("INDUSTRY")

                if df_ind is not None and not df_ind.empty:
                    df_ind_top = df_ind.head(10)

                    fig_ind = go.Figure(go.Bar(
                        y=df_ind_top['segmento'],
                        x=df_ind_top['seguidores'],
                        orientation='h',
                        marker_color="#10b981",
                                            ))
                    fig_ind.update_layout(
                        **CHART_LAYOUT,
                        height=400,
                        yaxis_title="",
                        xaxis_title="Seguidores",
                    )
                    st.plotly_chart(fig_ind, use_container_width=True)
                else:
                    st.info("No hay datos de industria")

            with ind_col2:
                st.markdown("**Tamano de empresa**")
                df_size = api.get_follower_segmentation("COMPANY_SIZE")

                if df_size is not None and not df_size.empty:
                    fig_size = go.Figure(go.Bar(
                        x=df_size['segmento'],
                        y=df_size['seguidores'],
                        marker_color="#f59e0b",
                                            ))
                    fig_size.update_layout(
                        **CHART_LAYOUT,
                        height=400,
                        xaxis_title="",
                        yaxis_title="Seguidores",
                    )
                    st.plotly_chart(fig_size, use_container_width=True)
                else:
                    st.info("No hay datos de tamano de empresa")

            # Follower growth
            st.markdown('<div class="section-title">Crecimiento de seguidores</div>', unsafe_allow_html=True)

            df_growth = api.get_follower_growth(days=int((end_date - start_date).days))

            if df_growth is not None and not df_growth.empty:
                fig_growth = go.Figure(go.Bar(
                    x=df_growth['fecha'],
                    y=df_growth['ganancia_total'],
                    marker_color="#3b82f6",
                                    ))
                fig_growth.update_layout(
                    **CHART_LAYOUT,
                    height=320,
                    title=dict(text="Nuevos seguidores por dia", font=dict(size=14, color="#e5e7eb")),
                    yaxis_title="",
                    xaxis_title="",
                )
                st.plotly_chart(fig_growth, use_container_width=True)

                growth_cols = st.columns(3, gap="medium")
                total_growth = df_growth['ganancia_total'].sum()
                avg_daily = df_growth['ganancia_total'].mean()
                organic_pct = (df_growth['ganancia_organica'].sum() / total_growth * 100) if total_growth > 0 else 0

                with growth_cols[0]:
                    st.metric("Nuevos seguidores", f"+{total_growth:,.0f}")
                with growth_cols[1]:
                    st.metric("Promedio diario", f"+{avg_daily:.1f}")
                with growth_cols[2]:
                    st.metric("Organico", f"{organic_pct:.1f}%")
            else:
                st.info("No hay datos de crecimiento disponibles")

# ==============================================================================
# TAB 4: COMPARISON
# ==============================================================================
with tab_comparison:
    st.markdown('<div class="section-title">Resumen general</div>', unsafe_allow_html=True)

    if df is not None and not df.empty:
        summary_data = {
            'Metrica': [
                'Total de Posts',
                'Impresiones Totales',
                'Clics Totales',
                'Reacciones Totales',
                'Comentarios Totales',
                'Compartidos Totales',
                'Engagement Rate Promedio'
            ],
            'Valor': [
                len(df),
                f"{df.get('impresiones', df.get('impression', pd.Series([0]))).sum():,.0f}",
                f"{df.get('clics', pd.Series([0])).sum():,.0f}",
                f"{df.get('likes', pd.Series([0])).sum():,.0f}",
                f"{df.get('comentarios', pd.Series([0])).sum():,.0f}",
                f"{df.get('compartidos', pd.Series([0])).sum():,.0f}",
                f"{df['ER%'].mean():.2f}%"
            ]
        }

        summary_df = pd.DataFrame(summary_data)

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Metrica": st.column_config.TextColumn("Metrica", width="large"),
                "Valor": st.column_config.TextColumn("Valor", width="medium")
            }
        )

        st.markdown('<div class="section-title">Rendimiento por tipo de contenido</div>', unsafe_allow_html=True)

        if 'tipo' in df.columns:
            tipo_summary = df.groupby('tipo').agg({
                'post_id': 'count',
                'impresiones': 'mean',
                'ER%': 'mean'
            }).round(2)

            tipo_summary.columns = ['Cantidad', 'Impresiones Promedio', 'ER% Promedio']
            tipo_summary = tipo_summary.sort_values('ER% Promedio', ascending=False)

            st.dataframe(
                tipo_summary,
                use_container_width=True,
                column_config={
                    "Cantidad": st.column_config.NumberColumn("Posts", format="%d"),
                    "Impresiones Promedio": st.column_config.NumberColumn("Impresiones Avg", format="%.0f"),
                    "ER% Promedio": st.column_config.NumberColumn("Engagement Avg", format="%.2f%%")
                }
            )

            fig_tipo = go.Figure(go.Bar(
                x=tipo_summary.reset_index()['tipo'],
                y=tipo_summary['ER% Promedio'],
                marker_color=CHART_COLORS[:len(tipo_summary)],
                                text=tipo_summary['ER% Promedio'],
                texttemplate='%{text:.2f}%',
                textposition='outside',
            ))
            fig_tipo.update_layout(
                **CHART_LAYOUT,
                height=380,
                title=dict(text="Engagement rate por tipo de contenido", font=dict(size=14, color="#e5e7eb")),
                yaxis_title="",
                xaxis_title="",
                showlegend=False,
            )
            st.plotly_chart(fig_tipo, use_container_width=True)

    else:
        st.info("No hay datos disponibles para mostrar el resumen")

# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown(f"""
<div class="dashboard-footer">
    LinkedIn Analytics &middot; {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
""", unsafe_allow_html=True)
