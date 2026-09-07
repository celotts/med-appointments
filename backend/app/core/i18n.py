"""Internationalization (i18n) module for API responses."""

# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # Appointments
        "appointment_created": "Appointment created successfully",
        "appointment_updated": "Appointment updated successfully",
        "appointment_deleted": "Appointment deleted successfully",
        "appointment_not_found": "Appointment not found",
        "appointment_already_exists": "An appointment already exists at that time",
        "appointment_rescheduled": "Appointment rescheduled successfully",
        "status_changed": "Status changed successfully",
        "invalid_status_transition": "Invalid status transition",
        # Patients
        "patient_created": "Patient created successfully",
        "patient_updated": "Patient updated successfully",
        "patient_deleted": "Patient deleted successfully",
        "patient_not_found": "Patient not found",
        "patient_already_exists": "Patient with this email already exists",
        # Doctors
        "doctor_created": "Doctor created successfully",
        "doctor_updated": "Doctor updated successfully",
        "doctor_deleted": "Doctor deleted successfully",
        "doctor_not_found": "Doctor not found",
        "doctor_already_exists": "Doctor with this license already exists",
        # Specialties
        "specialty_created": "Specialty created successfully",
        "specialty_updated": "Specialty updated successfully",
        "specialty_deleted": "Specialty deleted successfully",
        "specialty_not_found": "Specialty not found",
        "specialty_already_exists": "Specialty with this name already exists",
        # Medical Notes
        "note_created": "Medical note created successfully",
        "note_updated": "Medical note updated successfully",
        "note_deleted": "Medical note deleted successfully",
        "note_not_found": "Medical note not found",
        "note_already_exists": "This appointment already has a medical note",
        # RAG & Documents
        "document_ingested": "Document ingested successfully",
        "document_not_found": "Document not found",
        "search_error": "Search error",
        "agent_error": "Agent error",
        # Notifications
        "notification_sent": "Notification sent successfully",
        "notification_failed": "Failed to send notification",
        "invalid_notification_type": "Invalid notification type",
        "reminders_sent": "Reminders sent successfully",
        # Reports & Analytics
        "last_days": "Last {days} days",
        "total_appointments": "Total appointments",
        "appointments_by_day": "Appointments by day",
        "appointments_by_doctor": "Appointments by doctor",
        "no_show_analysis": "No-show analysis",
        "billing_summary": "Billing summary",
        "period": "Period",
        "total_billed": "Total billed",
        "total_collected": "Total collected",
        "pending_collection": "Pending collection",
        # Integrations
        "calendar_synced": "Calendar synced successfully",
        "branch_not_found": "Branch not found",
        "role_not_found": "Role not found",
        # Premium Features
        "telemedicine_session_created": "Telemedicine session created",
        "prescription_created": "Prescription created",
        "invoice_created": "Invoice created",
        # General
        "success": "Success",
        "error": "Error",
        "bad_request": "Bad request",
        "unauthorized": "Unauthorized",
        "forbidden": "Forbidden",
        "not_found": "Not found",
        "internal_error": "Internal server error",
        "total": "Total",
        "details": "Details",
        "message": "Message",
    },
    "es": {
        # Appointments
        "appointment_created": "Cita creada exitosamente",
        "appointment_updated": "Cita actualizada exitosamente",
        "appointment_deleted": "Cita eliminada exitosamente",
        "appointment_not_found": "Cita no encontrada",
        "appointment_already_exists": "Ya existe una cita en ese horario",
        "appointment_rescheduled": "Cita reagendada exitosamente",
        "status_changed": "Estado cambiado exitosamente",
        "invalid_status_transition": "Transición de estado no válida",
        # Patients
        "patient_created": "Paciente creado exitosamente",
        "patient_updated": "Paciente actualizado exitosamente",
        "patient_deleted": "Paciente eliminado exitosamente",
        "patient_not_found": "Paciente no encontrado",
        "patient_already_exists": "Ya existe un paciente con este email",
        # Doctors
        "doctor_created": "Médico creado exitosamente",
        "doctor_updated": "Médico actualizado exitosamente",
        "doctor_deleted": "Médico eliminado exitosamente",
        "doctor_not_found": "Médico no encontrado",
        "doctor_already_exists": "Ya existe un médico con esta cédula",
        # Specialties
        "specialty_created": "Especialidad creada exitosamente",
        "specialty_updated": "Especialidad actualizada exitosamente",
        "specialty_deleted": "Especialidad eliminada exitosamente",
        "specialty_not_found": "Especialidad no encontrada",
        "specialty_already_exists": "Ya existe una especialidad con este nombre",
        # Medical Notes
        "note_created": "Nota médica creada exitosamente",
        "note_updated": "Nota médica actualizada exitosamente",
        "note_deleted": "Nota médica eliminada exitosamente",
        "note_not_found": "Nota médica no encontrada",
        "note_already_exists": "Esta cita ya tiene una nota médica",
        # RAG & Documents
        "document_ingested": "Documento indexado exitosamente",
        "document_not_found": "Documento no encontrado",
        "search_error": "Error en la búsqueda",
        "agent_error": "Error del agente",
        # Notifications
        "notification_sent": "Notificación enviada exitosamente",
        "notification_failed": "Error al enviar notificación",
        "invalid_notification_type": "Tipo de notificación no válido",
        "reminders_sent": "Recordatorios enviados exitosamente",
        # Reports & Analytics
        "last_days": "Últimos {days} días",
        "total_appointments": "Total de citas",
        "appointments_by_day": "Citas por día",
        "appointments_by_doctor": "Citas por médico",
        "no_show_analysis": "Análisis de inasistencias",
        "billing_summary": "Resumen de facturación",
        "period": "Período",
        "total_billed": "Total facturado",
        "total_collected": "Total recaudado",
        "pending_collection": "Cobro pendiente",
        # Integrations
        "calendar_synced": "Calendario sincronizado exitosamente",
        "branch_not_found": "Sucursal no encontrada",
        "role_not_found": "Rol no encontrado",
        # Premium Features
        "telemedicine_session_created": "Sesión de telemedicina creada",
        "prescription_created": "Receta creada exitosamente",
        "invoice_created": "Factura creada exitosamente",
        # General
        "success": "Éxito",
        "error": "Error",
        "bad_request": "Solicitud incorrecta",
        "unauthorized": "No autorizado",
        "forbidden": "Prohibido",
        "not_found": "No encontrado",
        "internal_error": "Error interno del servidor",
        "total": "Total",
        "details": "Detalles",
        "message": "Mensaje",
    },
    "pt": {
        # Appointments
        "appointment_created": "Consulta criada com sucesso",
        "appointment_updated": "Consulta atualizada com sucesso",
        "appointment_deleted": "Consulta excluída com sucesso",
        "appointment_not_found": "Consulta não encontrada",
        "appointment_already_exists": "Já existe uma consulta nesse horário",
        "appointment_rescheduled": "Consulta reagendada com sucesso",
        "status_changed": "Status alterado com sucesso",
        "invalid_status_transition": "Transição de status inválida",
        # Patients
        "patient_created": "Paciente criado com sucesso",
        "patient_updated": "Paciente atualizado com sucesso",
        "patient_deleted": "Paciente excluído com sucesso",
        "patient_not_found": "Paciente não encontrado",
        "patient_already_exists": "Já existe um paciente com este email",
        # Doctors
        "doctor_created": "Médico criado com sucesso",
        "doctor_updated": "Médico atualizado com sucesso",
        "doctor_deleted": "Médico excluído com sucesso",
        "doctor_not_found": "Médico não encontrado",
        "doctor_already_exists": "Já existe um médico com esta licença",
        # Specialties
        "specialty_created": "Especialidade criada com sucesso",
        "specialty_updated": "Especialidade atualizada com sucesso",
        "specialty_deleted": "Especialidade excluída com sucesso",
        "specialty_not_found": "Especialidade não encontrada",
        "specialty_already_exists": "Já existe uma especialidade com este nome",
        # Medical Notes
        "note_created": "Nota médica criada com sucesso",
        "note_updated": "Nota médica atualizada com sucesso",
        "note_deleted": "Nota médica excluída com sucesso",
        "note_not_found": "Nota médica não encontrada",
        "note_already_exists": "Esta consulta já possui uma nota médica",
        # RAG & Documents
        "document_ingested": "Documento indexado com sucesso",
        "document_not_found": "Documento não encontrado",
        "search_error": "Erro na busca",
        "agent_error": "Erro do agente",
        # Notifications
        "notification_sent": "Notificação enviada com sucesso",
        "notification_failed": "Falha ao enviar notificação",
        "invalid_notification_type": "Tipo de notificação inválido",
        "reminders_sent": "Lembretes enviados com sucesso",
        # Reports & Analytics
        "last_days": "Últimos {days} dias",
        "total_appointments": "Total de consultas",
        "appointments_by_day": "Consultas por dia",
        "appointments_by_doctor": "Consultas por médico",
        "no_show_analysis": "Análise de faltas",
        "billing_summary": "Resumo de faturamento",
        "period": "Período",
        "total_billed": "Total faturado",
        "total_collected": "Total arrecadado",
        "pending_collection": "Cobrança pendente",
        # Integrations
        "calendar_synced": "Calendário sincronizado com sucesso",
        "branch_not_found": "Filial não encontrada",
        "role_not_found": "Função não encontrada",
        # Premium Features
        "telemedicine_session_created": "Sessão de telemedicina criada",
        "prescription_created": "Receita criada com sucesso",
        "invoice_created": "Fatura criada com sucesso",
        # General
        "success": "Sucesso",
        "error": "Erro",
        "bad_request": "Requisição inválida",
        "unauthorized": "Não autorizado",
        "forbidden": "Proibido",
        "not_found": "Não encontrado",
        "internal_error": "Erro interno do servidor",
        "total": "Total",
        "details": "Detalhes",
        "message": "Mensagem",
    },
}


def get_translation(key: str, lang: str = "en", **kwargs) -> str:
    """Get a translation by key and language with optional format kwargs."""
    if lang in TRANSLATIONS and key in TRANSLATIONS[lang]:
        translation = TRANSLATIONS[lang][key]
    # Fallback to English
    elif key in TRANSLATIONS["en"]:
        translation = TRANSLATIONS["en"][key]
    else:
        # Return key if not found
        translation = key

    # Apply format kwargs if provided
    if kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError:
            return translation
    return translation


def get_supported_languages() -> list[str]:
    """Get list of supported languages."""
    return list(TRANSLATIONS.keys())
