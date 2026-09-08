import axiosInstance from './axiosInstance';

export interface RescheduleRequest {
  appointment_id: number;
  preferred_date: string;
  preferred_time?: string;
}

export interface RescheduleSuggestion {
  start: string;
  end: string;
  score: number;
}

export interface RescheduleResponse {
  appointment_id: number;
  current_start: string;
  current_end: string;
  suggestions: RescheduleSuggestion[];
  message: string;
}

export interface AvailabilityRequest {
  doctor_id: number;
  date: string;
  duration_minutes?: number;
}

export interface AvailabilitySlot {
  start: string;
  end: string;
}

export interface ConflictCheckRequest {
  doctor_id: number;
  start_datetime: string;
  end_datetime: string;
  exclude_appointment_id?: number;
}

export interface ConflictCheckResponse {
  has_conflict: boolean;
  conflict_details?: string;
  suggested_fix?: string;
}

export interface FollowUpRequest {
  patient_id: number;
  doctor_id: number;
  last_appointment_date: string;
  visit_type: 'control' | 'urgent' | 'routine' | 'surgery_followup';
}

export interface FollowUpResponse {
  recommended_days: number;
  recommended_date: string;
  reason: string;
}

export const medasistApi = {
  async reschedule(data: RescheduleRequest): Promise<RescheduleResponse> {
    const response = await axiosInstance.post('/medasist/reschedule', data);
    return response.data;
  },

  async checkConflict(data: ConflictCheckRequest): Promise<ConflictCheckResponse> {
    const response = await axiosInstance.post('/medasist/check-conflict', data);
    return response.data;
  },

  async getAvailableSlots(data: AvailabilityRequest): Promise<AvailabilitySlot[]> {
    const response = await axiosInstance.post('/medasist/available-slots', data);
    return response.data;
  },

  async suggestFollowUp(data: FollowUpRequest): Promise<FollowUpResponse> {
    const response = await axiosInstance.post('/medasist/suggest-followup', data);
    return response.data;
  },
};
