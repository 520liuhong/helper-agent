/**
 * API调用模块
 */
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const chatApi = {
  /**
   * 发送聊天消息
   * @param {Object} params - 请求参数
   * @param {Array} params.messages - 消息列表
   * @param {string} params.model - AI模型 (deepseek/qwen)
   * @param {boolean} params.stream - 是否流式响应
   * @param {number} params.temperature - 温度参数
   * @param {number} params.max_tokens - 最大token数
   * @param {Function} onChunk - 流式数据回调
   */
  async send(params, onChunk) {
    if (params.stream && onChunk) {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '请求失败')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              return
            }
            try {
              const parsed = JSON.parse(data)
              if (parsed.error) {
                throw new Error(parsed.error)
              }
              onChunk(parsed)
            } catch (e) {
              if (e instanceof Error && e.message && !e.message.includes('JSON')) {
                throw e
              }
              console.error('解析SSE数据失败:', e)
            }
          }
        }
      }
      return
    } else {
      const response = await apiClient.post('/chat', params)
      return response.data
    }
  },

  /**
   * 获取支持的模型列表
   */
  async listModels() {
    const response = await apiClient.get('/models')
    return response.data
  },
}

export const sessionsApi = {
  /**
   * 获取会话列表
   */
  async list() {
    const response = await apiClient.get('/sessions')
    return response.data
  },

  /**
   * 创建会话
   */
  async create(data = {}) {
    const response = await apiClient.post('/sessions', data)
    return response.data
  },

  /**
   * 获取会话详情
   */
  async get(sessionId) {
    const response = await apiClient.get(`/sessions/${sessionId}`)
    return response.data
  },

  /**
   * 更新会话
   */
  async update(sessionId, data) {
    const response = await apiClient.put(`/sessions/${sessionId}`, data)
    return response.data
  },

  /**
   * 删除会话
   */
  async delete(sessionId) {
    const response = await apiClient.delete(`/sessions/${sessionId}`)
    return response.data
  },

  /**
   * 添加消息到会话
   */
  async addMessage(sessionId, message) {
    const response = await apiClient.post(`/sessions/${sessionId}/messages`, message)
    return response.data
  },
}

export const uploadApi = {
  /**
   * 上传文件
   */
  async upload(file) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}
