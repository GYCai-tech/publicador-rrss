from src import db_config
import streamlit as st
import pandas as pd
import re
from typing import List, Tuple

# --- Configuración e Inicialización ---
st.set_page_config(layout="wide", page_title="Gestión de Contactos", page_icon="👥")

if 'editing_contact_id' not in st.session_state:
    st.session_state.editing_contact_id = None
if 'import_step' not in st.session_state:
    st.session_state.import_step = 0 # 0: Oculto, 1: Subir, 2: Mapear, 3: Validar
if 'selected_contact_ids' not in st.session_state:
    st.session_state.selected_contact_ids = set()


# --- Función de Validación ---
def _validate_contact_data(name: str, emails: List[str], phones: List[str]) -> Tuple[bool, str]:
    """Valida los datos de un contacto, aceptando listas de emails y teléfonos."""
    if not name or not name.strip():
        return False, "El nombre es obligatorio."

    # Limpiar listas de elementos vacíos antes de validar
    clean_emails = [e.strip() for e in emails if e and e.strip()]
    clean_phones = [p.strip() for p in phones if p and p.strip()]

    if not clean_emails and not clean_phones:
        return False, "Se requiere al menos un teléfono o un email."

    if clean_emails:
        pattern = r'^[a-zA-Z0-9ñÑ._%+-]+@[a-zA-Z0-9ñÑ.-]+\.[a-zA-Z]{2,}$'
        for email in clean_emails:
            if not re.match(pattern, email):
                return False, f"Formato de email inválido para '{email}'."

    has_sendable_phone = False
    if clean_phones:
        for phone in clean_phones:
            phone_digits = re.sub(r'[\s()-]', '', str(phone))
            pattern = r'^((\+|00)\d{7,15}|[67]\d{8})$'
            fijo = r'^[89]\d{8}$'

            is_mobile = re.match(pattern, phone_digits)
            is_landline = re.match(fijo, phone_digits)
            if is_mobile:
                has_sendable_phone = True

            # Si no es ni un móvil válido ni un fijo español, es un error de formato
            if not is_mobile and not is_landline:
                return False, f"Teléfono '{phone}' no es un número válido (ni móvil ni fijo español)."

    # Un contacto solo es válido si tiene al menos un email o un teléfono móvil (no solo fijos)
    if not clean_emails and not has_sendable_phone:
        return False, "El contacto debe tener al menos un email o un teléfono móvil válido para el envío."

    return True, ""


# --- Función para manejar el cambio en el checkbox ---
def toggle_contact_selection(contact_id):
    if contact_id in st.session_state.selected_contact_ids:
        st.session_state.selected_contact_ids.remove(contact_id)
    else:
        st.session_state.selected_contact_ids.add(contact_id)


# --- Función para procesar texto de text_area a lista ---
def parse_textarea_input(text: str) -> List[str]:
    # Divide por comas o saltos de línea, elimina espacios y filtra vacíos
    items = re.split(r'[,\n]', text)
    return [item.strip() for item in items if item.strip()]


# --- Lógica de la Interfaz de Importación ---
@st.dialog("⬆️ Importar Contactos desde Archivo")
def import_contacts_dialog():
    """Muestra el diálogo para importar contactos en varios pasos."""
    # --- PASO 1: Subir archivo ---
    if st.session_state.import_step == 1:
        st.info("Sube un archivo CSV o Excel con tus contactos. Puede contener varias columnas para email y/o teléfono.")
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo de contactos",
            type=['csv', 'xlsx', 'xls'],
            label_visibility="collapsed"
        )
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=None, engine='python', dtype=str, keep_default_na=False)
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding='latin1', sep=None, engine='python', dtype=str, keep_default_na=False)
                else:
                    df = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)

                st.session_state.import_df = df
                st.session_state.import_step = 2
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
        if st.button("Cancelar", key="cancel_step1"):
            st.session_state.import_step = 0
            st.rerun()

    # --- PASO 2: Mapear columnas ---
    elif st.session_state.import_step == 2:
        st.subheader("2. Asigna las columnas")
        st.write("Indica qué columnas de tu archivo corresponden a cada campo.")
        df = st.session_state.import_df
        st.dataframe(df.head(), width='stretch')

        columns = ["-- No usar --"] + list(df.columns)

        col_map = {}
        col1, col2, col3 = st.columns(3)
        with col1:
            col_map['name'] = st.selectbox("Nombre Completo*", options=columns)
        with col2:
            col_map['emails'] = st.multiselect("Columnas de Email", options=df.columns)
        with col3:
            col_map['phones'] = st.multiselect("Columnas de Teléfono", options=df.columns)

        all_lists = db_config.get_all_contact_lists()
        list_options = {lst['id']: lst['name'] for lst in all_lists}
        selected_list_ids = st.multiselect(
            "Asignar todos los contactos importados a estas listas (opcional)",
            options=list_options.keys(),
            format_func=lambda x: list_options[x]
        )

        if st.button("Analizar y Validar Datos", type="primary"):
            if col_map['name'] == "-- No usar --":
                st.error("Debes asignar una columna para el 'Nombre'.")
            elif not col_map['emails'] and not col_map['phones']:
                st.error("Debes asignar una columna para 'Email' o 'Teléfono'.")
            else:
                st.session_state.col_map = col_map
                st.session_state.selected_list_ids = selected_list_ids
                st.session_state.import_step = 3
                st.rerun()
        if st.button("Volver", key="back_step2"):
            st.session_state.import_step = 1
            del st.session_state.import_df
            st.rerun()

    # --- PASO 3: Validar y Confirmar ---
    elif st.session_state.import_step == 3:
        st.subheader("3. Revisa y Confirma")
        df = st.session_state.import_df
        col_map = st.session_state.col_map
        valid_contacts, invalid_contacts = [], []

        for index, row in df.iterrows():
            name = str(row[col_map['name']]) if col_map['name'] != '-- No usar --' and col_map['name'] in row else ""
            emails = [str(row[col]) for col in col_map.get('emails', []) if col in row and pd.notna(row[col]) and str(row[col]).strip()]
            phones = [str(row[col]) for col in col_map.get('phones', []) if col in row and pd.notna(row[col]) and str(row[col]).strip()]

            is_valid, error_msg = _validate_contact_data(name, emails, phones)

            contact_data = {'name': name, 'emails': emails, 'phones': phones}
            if is_valid:
                valid_contacts.append(contact_data)
            else:
                contact_data['error'] = error_msg
                invalid_contacts.append(contact_data)

        st.session_state.valid_contacts_to_import = valid_contacts
        st.success(f"✅ **{len(valid_contacts)} contactos válidos** listos para importar.")
        if invalid_contacts:
            st.warning(f"⚠️ **{len(invalid_contacts)} contactos con errores** que no se importarán.")
            with st.expander("Ver detalles de los errores"):
                df_errors = pd.DataFrame(invalid_contacts)
                if 'emails' in df_errors.columns:
                    df_errors['emails'] = df_errors['emails'].apply(lambda x: ', '.join(x) if x else '-')
                if 'phones' in df_errors.columns:
                    df_errors['phones'] = df_errors['phones'].apply(lambda x: ', '.join(x) if x else '-')
                st.dataframe(df_errors, width='stretch')

        if 'import_result' in st.session_state:
            result = st.session_state.import_result

            # Mostrar un resumen claro y persistente
            if result['added'] > 0:
                st.success(f"🎉 ¡Éxito! Se han añadido {result['added']} nuevos contactos.")

            if result['errors']:
                st.warning(f"⚠️ Se omitieron {len(result['errors'])} filas por los siguientes motivos:")
                # Mostrar los errores en un recuadro para que sea fácil de leer
                st.code('\n'.join(result['errors']), language='text')

            if st.button("Cerrar"):
                del st.session_state.import_result
                st.session_state.import_step = 0
                st.rerun()

        else:  # Si no hay resultado, mostrar el botón de confirmación
            if valid_contacts:
                if st.button(f"Añadir {len(valid_contacts)} contactos a la base de datos", type="primary"):
                    contacts_to_add = [{**c, 'list_ids': st.session_state.selected_list_ids} for c in valid_contacts]
                    result = db_config.create_contacts_bulk(contacts_to_add)

                    # Guardar el resultado en el session_state y recargamos
                    st.session_state.import_result = result
                    db_config.get_all_contacts.clear()
                    st.rerun()

            if st.button("Volver a mapear", key="back_step3"):
                st.session_state.import_step = 2
                st.rerun()
            if st.button("Cancelar importación", key="cancel_step3"):
                st.session_state.import_step = 0
                st.rerun()


# --- Diálogos para acciones en masa ---
@st.dialog("🗑️ Eliminar Contactos")
def delete_confirmation_dialog():
    count = len(st.session_state.selected_contact_ids)
    st.warning(f"¿Quieres eliminar los {count} contacto(s) seleccionados?")
    if st.button("Confirmar Eliminación", type="primary"):
        for contact_id in st.session_state.selected_contact_ids:
            db_config.delete_contact(contact_id)
        st.session_state.selected_contact_ids.clear()
        db_config.get_all_contacts.clear()
        st.toast(f"{count} contactos eliminados.", icon="✅")
        st.rerun()
    if st.button("Cancelar"):
        st.rerun()


@st.dialog("➕ Asignar a Lista")
def add_to_list_dialog():
    count = len(st.session_state.selected_contact_ids)
    st.info(f"Vas a modificar las listas de {count} contacto(s).")
    list_options = {lst['id']: lst['name'] for lst in all_lists}
    lists_to_add = st.multiselect(
        "Selecciona las listas a las que quieres añadir los contactos",
        options=list_options.keys(),
        format_func=lambda x: list_options[x]
    )
    if st.button("Confirmar y Añadir", type="primary"):
        if not lists_to_add:
            st.warning("Debes seleccionar al menos una lista.")
            return

        updated_count = 0
        for contact_id in st.session_state.selected_contact_ids:
            # Lógica para no duplicar listas
            contact = db_config.get_contact_by_id(contact_id)
            if contact:
                db_config.update_contact(
                    contact_id=contact_id,
                    name=contact['name'],
                    phones=contact.get('phones', []),
                    emails=contact.get('emails', []),
                    list_ids=lists_to_add
                )
                updated_count += 1
        st.session_state.selected_contact_ids.clear()
        db_config.get_all_contacts.clear()
        st.toast(f"{updated_count} contactos actualizados.", icon="✅")
        st.rerun()
    if st.button("Cancelar"):
        st.rerun()


# --- Título y botón de importación ---
header_cols = st.columns([0.8, 0.2])
with header_cols[0]:
    st.title("👥 Gestión de Contactos")
    st.markdown("Crea, organiza e importa tus contactos y listas.")
with header_cols[1]:
    st.write("")
    st.write("")
    if st.button("⬆️ Importar Contactos", width='stretch'):
        st.session_state.import_step = 1
if st.session_state.import_step > 0:
    import_contacts_dialog()

# --- Layout Principal ---
col_lists, col_contacts = st.columns([1, 3])
all_lists = db_config.get_all_contact_lists()

# --- Columna de Listas de Contactos ---
with col_lists:
    st.header("📂 Listas")

    with st.expander("➕ Añadir Nueva Lista", expanded=True):
        with st.form("new_list_form", clear_on_submit=True):
            list_name = st.text_input("Nombre de la nueva lista")
            submitted = st.form_submit_button("Crear Lista")
            if submitted and list_name:
                result = db_config.create_contact_list(list_name)
                if result["success"]:
                    st.toast(result["message"], icon="🎉")
                    db_config.get_all_contact_lists.clear()  # Limpiar caché
                    st.rerun()
                else:
                    st.error(result["message"])

    st.divider()
    if not all_lists:
        st.info("Aún no has creado ninguna lista.")
    else:
        for lst in all_lists:
            with st.container(border=True):
                c1, c2 = st.columns([0.85, 0.15])
                c1.write(f"**{lst['name']}**")
                if c2.button("🗑️", key=f"delete_list_{lst['id']}", help="Eliminar lista"):
                    db_config.delete_contact_list(lst['id'])
                    db_config.get_all_contact_lists.clear()
                    db_config.get_all_contacts.clear()
                    st.toast(f"Lista '{lst['name']}' eliminada.", icon="🗑️")
                    st.rerun()

# --- Columna de Contactos ---
with col_contacts:
    st.header("👤 Contactos")

    if st.session_state.editing_contact_id is not None:
        # --- Formulario de Edición ---
        contact_to_edit = db_config.get_contact_by_id(st.session_state.editing_contact_id)
        if contact_to_edit:
            with st.container(border=True):
                st.markdown("#### ✏️ Modificar Contacto")
                with st.form("edit_contact_form"):
                    name = st.text_input("Nombre Completo*", value=contact_to_edit.get('name', ''))

                    # Usar text_area y unir listas para mostrar
                    emails_str = "\n".join(contact_to_edit.get('emails', []))
                    phones_str = "\n".join(contact_to_edit.get('phones', []))

                    c1, c2 = st.columns(2)
                    emails_input = c1.text_area("Emails", value=emails_str, height=120, help="Uno por línea o separados por coma.")
                    phones_input = c2.text_area("Teléfonos", value=phones_str, height=120, help="Uno por línea o separados por coma.")

                    list_options = {lst['id']: lst['name'] for lst in all_lists}
                    current_list_ids = [l['id'] for l in contact_to_edit.get('lists', [])]
                    selected_list_ids = st.multiselect(
                        "Asignar a listas",
                        options=list_options.keys(),
                        default=current_list_ids,
                        format_func=lambda x: list_options.get(x, x)
                    )

                    submitted_edit, cancelled_edit = st.columns(2)
                    if submitted_edit.form_submit_button("Guardar Cambios", width='stretch', type="primary"):
                        emails_list = parse_textarea_input(emails_input)
                        phones_list = parse_textarea_input(phones_input)

                        is_valid, error_msg = _validate_contact_data(name, emails_list, phones_list)
                        if is_valid:
                            result = db_config.update_contact(
                                contact_id=st.session_state.editing_contact_id,
                                name=name,
                                phones=phones_list,
                                emails=emails_list,
                                list_ids=selected_list_ids
                            )
                            st.toast(result["message"], icon="👍" if result["success"] else "🚨")
                            if result["success"]:
                                db_config.get_all_contacts.clear()
                                st.session_state.editing_contact_id = None
                                st.rerun()
                        else:
                            st.error(error_msg)

                    if cancelled_edit.form_submit_button("Cancelar", width='stretch'):
                        st.session_state.editing_contact_id = None
                        st.rerun()
    else:
        # --- Formulario de Creación ---
        with st.expander("➕ Añadir Nuevo Contacto", expanded=True):
            with st.form("new_contact_form", clear_on_submit=True):
                st.markdown("##### Datos del Contacto")
                name = st.text_input("Nombre Completo*", help="El nombre es obligatorio.")

                c1, c2 = st.columns(2)
                emails_input = c1.text_area("Emails", height=120, help="Añade varios emails separados por comas o saltos de línea.")
                phones_input = c2.text_area("Teléfonos", height=120, help="Añade varios teléfonos separados por comas o saltos de línea.")

                # Crear diccionario solo con datos de la BD
                list_options = {lst['id']: lst['name'] for lst in all_lists}
                selected_list_ids = st.multiselect(
                    "Asignar a listas (opcional)",
                    options=list_options.keys(),
                    format_func=lambda x: list_options[x]
                )

                if st.form_submit_button("Guardar Contacto", width='stretch'):
                    emails_list = parse_textarea_input(emails_input)
                    phones_list = parse_textarea_input(phones_input)

                    is_valid, error_msg = _validate_contact_data(name, emails_list, phones_list)
                    if is_valid:
                        result = db_config.create_contact(
                            name=name,
                            phones=phones_list,
                            emails=emails_list,
                            list_ids=selected_list_ids
                        )
                        st.toast(result["message"], icon="👍" if result["success"] else "🚨")
                        if result["success"]:
                            db_config.get_all_contacts.clear()  # Limpiar caché
                            st.rerun()
                        else:
                            st.error(result["message"])
                    else:
                        st.error(error_msg)

    # --- Filtros y Visualización de Contactos ---
    st.divider()
    st.markdown("##### Listado de Contactos")
    all_contacts_data = db_config.get_all_contacts()

    if not all_contacts_data:
        st.info("No hay contactos guardados.")
    else:
        # Convertir a DataFrame para facilitar el filtrado
        df = pd.DataFrame(all_contacts_data)

        # Filtros
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            search_term = st.text_input("Buscar por nombre, email o teléfono...", key="contact_search")

        with filter_col2:
            list_filter_options = {"all": "Todas las listas", "none": "Sin lista asignada"}
            list_filter_options.update({lst['id']: lst['name'] for lst in all_lists})
            selected_list_filter = st.selectbox(
                "Filtrar por lista",
                options=["all", "none"] + [lst['id'] for lst in all_lists],
                format_func=lambda x: list_filter_options.get(x, x),
            )

        # Aplicar filtros
        if search_term:
            term = search_term.lower()
            df = df[df.apply(lambda row: term in str(row['name']).lower() or
                                         any(term in email.lower() for email in row.get('emails', [])) or
                                         any(term in phone for phone in row.get('phones', [])), axis=1)]

        if selected_list_filter != "all":
            if selected_list_filter == "none":
                df = df[df['lists'].apply(lambda x: not x)]
            else:
                df = df[df['lists'].apply(lambda lists: any(l['id'] == selected_list_filter for l in lists))]

        # Botones para acciones en masa
        st.markdown("---")
        action_col1, action_col2, _ = st.columns([1, 1, 4])

        # El botón se desactiva si no hay contactos seleccionados
        is_disabled = not st.session_state.selected_contact_ids
        with action_col1:
            if st.button("🗑️ Eliminar Seleccionados", disabled=is_disabled, width='stretch'):
                delete_confirmation_dialog()
        with action_col2:
            if st.button("➕ Añadir a Lista", disabled=is_disabled, width='stretch'):
                add_to_list_dialog()

        # --- Mostrar Tabla de Contactos ---
        if df.empty:
            st.warning("No se encontraron contactos con los filtros aplicados.")
        else:
            # Encabezados
            header_cols = st.columns([0.5, 4, 4, 3, 3, 1.5])
            header_cols[1].markdown("**Nombre**")
            header_cols[2].markdown("**Email**")
            header_cols[3].markdown("**Teléfono**")
            header_cols[4].markdown("**Listas**")
            header_cols[5].markdown("<div style='text-align: center;'>Editar</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin-top:0; margin-bottom:1rem; border-color: #444;'>", unsafe_allow_html=True)

            for index, row in df.iterrows():
                contact_id = row['id']
                cols = st.columns([0.5, 4, 4, 3, 3, 1.5])
                cols[0].checkbox(
                    " ",
                    key=f"select_{contact_id}",
                    value=(contact_id in st.session_state.selected_contact_ids),
                    on_change=toggle_contact_selection,
                    args=(contact_id,)
                )
                cols[1].text(row['name'])

                emails_display = ", ".join(row.get('emails', []))
                phones_display = ", ".join(row.get('phones', []))
                cols[2].text(emails_display if emails_display else "-")
                cols[3].text(phones_display if phones_display else "-")

                with cols[4]:
                    contact_lists = row.get('lists', [])
                    if contact_lists:
                        # Limitar el número de badges mostrados para no saturar
                        display_lists = contact_lists[:2]
                        for l in display_lists:
                           st.markdown(f"<span style='background-color:#333; color:white; padding: 3px 8px; border-radius: 10px; margin-right: 4px; font-size: 0.8em;'>{l['name']}</span>", unsafe_allow_html=True)
                        if len(contact_lists) > 2:
                            st.markdown(f"<span style='font-size: 0.8em;'>+{len(contact_lists) - 2} más</span>", unsafe_allow_html=True)
                    else:
                        st.text("-")

                with cols[5]:
                    st.markdown('<div style="display: flex; justify-content: center;">', unsafe_allow_html=True)
                    if st.button("✏️", key=f"edit_{contact_id}", help="Editar"):
                        st.session_state.editing_contact_id = contact_id
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                st.markdown("<hr style='margin:0.5rem 0; border-color: #222;'>", unsafe_allow_html=True)
