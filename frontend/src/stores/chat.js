/**
 * Chat Store
 * 管理聊天相关的状态，支持本地存储持久化
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'chat_sessions'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const sessions = ref([])
  const currentSessionId = ref(null)
  const isTyping = ref(false)
  const settings = ref({
    model: localStorage.getItem('chat_model') || 'deepseek',
    temperature: parseFloat(localStorage.getItem('chat_temperature')) || 0.7,
    maxTokens: parseInt(localStorage.getItem('chat_maxTokens')) || 2000,
  })

  // 计算属性
  const currentSession = computed(() => {
    return sessions.value.find(s => s.id === currentSessionId.value) || null
  })

  // 从本地存储加载会话
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        sessions.value = data.sessions || []
        currentSessionId.value = data.currentSessionId || null
      }
    } catch (e) {
      console.error('从本地存储加载会话失败:', e)
    }
  }

  // 保存到本地存储
  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        sessions: sessions.value,
        currentSessionId: currentSessionId.value,
      }))
    } catch (e) {
      console.error('保存会话到本地存储失败:', e)
    }
  }

  // 监听变化自动保存
  watch([sessions, currentSessionId], () => {
    saveToStorage()
  }, { deep: true })

  // 监听设置变化
  watch(() => settings.value, (newSettings) => {
    localStorage.setItem('chat_model', newSettings.model)
    localStorage.setItem('chat_temperature', String(newSettings.temperature))
    localStorage.setItem('chat_maxTokens', String(newSettings.maxTokens))
  }, { deep: true })

  // 方法
  function addSession(session) {
    sessions.value.unshift(session)
    currentSessionId.value = session.id
  }

  function updateSession(sessionId, updates) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      Object.assign(session, updates)
    }
  }

  function deleteSession(sessionId) {
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
  }

  function addMessage(sessionId, message) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      if (!session.messages) session.messages = []
      session.messages.push(message)
    }
  }

  function updateLastMessage(sessionId, content) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session && session.messages && session.messages.length > 0) {
      session.messages[session.messages.length - 1].content = content
    }
  }

  function updateSettings(newSettings) {
    settings.value = { ...settings.value, ...newSettings }
  }

  // 初始化时加载本地存储
  loadFromStorage()

  return {
    sessions,
    currentSessionId,
    isTyping,
    settings,
    currentSession,
    addSession,
    updateSession,
    deleteSession,
    addMessage,
    updateLastMessage,
    updateSettings,
    loadFromStorage,
    saveToStorage,
  }
})
