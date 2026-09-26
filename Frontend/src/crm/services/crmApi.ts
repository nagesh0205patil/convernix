const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

async function request(path: string, options: RequestInit = {}, token?: string) {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (response.status === 204) return null

  if (!response.ok) {
    let errMessage = `Request failed (${response.status})`
    try {
      const data = await response.json()
      errMessage = data.detail || (typeof data === 'object' ? JSON.stringify(data) : errMessage)
    } catch {
      // ignore json parse error
    }
    const err = new Error(errMessage) as any
    err.status = response.status
    throw err
  }

  return response.json()
}

export const crmApi = {
  // Leads
  async getLeads(token: string, params: Record<string, any> = {}) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        searchParams.append(k, String(v))
      }
    })
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return request(`/v1/leads${qs}`, { method: 'GET' }, token)
  },

  async getLead(token: string, leadId: string) {
    return request(`/v1/leads/${leadId}/`, { method: 'GET' }, token)
  },

  async createLead(token: string, data: any) {
    return request('/v1/leads/', { method: 'POST', body: JSON.stringify(data) }, token)
  },

  async updateLead(token: string, leadId: string, data: any) {
    return request(`/v1/leads/${leadId}/`, { method: 'PATCH', body: JSON.stringify(data) }, token)
  },

  async transitionLeadStage(token: string, leadId: string, payload: { stage_id: string; expected_version: number; reason?: string }) {
    return request(`/v1/leads/${leadId}/stage/`, { method: 'PUT', body: JSON.stringify(payload) }, token)
  },

  async assignLead(token: string, leadId: string, payload: { owner_user_id?: string; department_id?: string; reason?: string }) {
    return request(`/v1/leads/${leadId}/assign/`, { method: 'POST', body: JSON.stringify(payload) }, token)
  },

  async updateLeadTags(token: string, leadId: string, tags: string[]) {
    return request(`/v1/leads/${leadId}/tags/`, { method: 'POST', body: JSON.stringify({ tags }) }, token)
  },

  // Customers
  async getCustomers(token: string, params: Record<string, any> = {}) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        searchParams.append(k, String(v))
      }
    })
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return request(`/v1/customers${qs}`, { method: 'GET' }, token)
  },

  async getCustomer(token: string, customerId: string) {
    return request(`/v1/customers/${customerId}/`, { method: 'GET' }, token)
  },

  async createCustomer(token: string, data: any) {
    return request('/v1/customers/', { method: 'POST', body: JSON.stringify(data) }, token)
  },

  async getCustomer360(token: string, customerId: string) {
    return request(`/v1/customers/${customerId}/360/`, { method: 'GET' }, token)
  },

  async getCustomerConversations(token: string, customerId: string) {
    return request(`/v1/customers/${customerId}/conversations/`, { method: 'GET' }, token)
  },

  async getCustomerActivities(token: string, customerId: string) {
    return request(`/v1/customers/${customerId}/activities/`, { method: 'GET' }, token)
  },

  async getCustomerNotes(token: string, customerId: string) {
    return request(`/v1/customers/${customerId}/notes/`, { method: 'GET' }, token)
  },

  async addCustomerNote(token: string, customerId: string, note: string) {
    return request(`/v1/customers/${customerId}/notes/`, { method: 'POST', body: JSON.stringify({ note }) }, token)
  },

  async mergeCustomers(token: string, payload: { primary_customer_id: string; duplicate_customer_id: string; reason?: string }) {
    return request('/v1/customers/merge/', { method: 'POST', body: JSON.stringify(payload) }, token)
  },

  // Global Search
  async search(token: string, query: string, entity_type = 'all') {
    return request(`/v1/crm/search/?q=${encodeURIComponent(query)}&type=${entity_type}`, { method: 'GET' }, token)
  },

  // Pipelines
  async getPipelines(token: string) {
    return request('/v1/crm/pipelines/', { method: 'GET' }, token)
  },

  async createPipeline(token: string, data: any) {
    return request('/v1/crm/pipelines/', { method: 'POST', body: JSON.stringify(data) }, token)
  },

  async createPipelineStage(token: string, pipelineId: string, data: any) {
    return request(`/v1/crm/pipelines/${pipelineId}/stages/`, { method: 'POST', body: JSON.stringify(data) }, token)
  },

  // Tags
  async getTags(token: string) {
    return request('/v1/crm/tags/', { method: 'GET' }, token)
  },

  async createTag(token: string, data: { name: string; color?: string; description?: string }) {
    return request('/v1/crm/tags/', { method: 'POST', body: JSON.stringify(data) }, token)
  },

  async deleteTag(token: string, tagId: string) {
    return request(`/v1/crm/tags/${tagId}/`, { method: 'DELETE' }, token)
  },

  // Custom Fields
  async getCustomFields(token: string) {
    return request('/v1/crm/custom-fields/', { method: 'GET' }, token)
  },

  async createCustomField(token: string, data: any) {
    return request('/v1/crm/custom-fields/', { method: 'POST', body: JSON.stringify(data) }, token)
  },

  async deleteCustomField(token: string, fieldId: string) {
    return request(`/v1/crm/custom-fields/${fieldId}/`, { method: 'DELETE' }, token)
  },
}
