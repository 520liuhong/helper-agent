<template>
  <div class="app-container">
    <Sidebar 
      :sessions="sessions"
      :currentSessionId="currentSessionId"
      @select-session="handleSelectSession"
      @create-session="handleCreateSession"
      @delete-session="handleDeleteSession"
    />
    <div class="main-area">
      <div class="chat-toolbar">
        <div class="toolbar-left">
          <ModelSelector v-model="settings.model" @change="handleModelChange" />
        </div>
        <div class="toolbar-right">
          <el-button 
            :icon="isDark ? Sunny : Moon" 
            circle 
            @click="toggleTheme"
            :title="isDark ? '切换到亮色主题' : '切换到暗色主题'"
          />
          <el-button :icon="Setting" circle @click="settingsVisible = true" />
        </div>
      </div>
      <ChatArea
        :session="currentSession"
        :isTyping="isTyping"
        @send-message="handleSendMessage"
        @retry-message="handleRetryMessage"
      />
    </div>
    <Settings 
      :visible="settingsVisible"
      :settings="settings"
      @update:visible="settingsVisible = $event"
      @update:settings="handleUpdateSettings"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Setting, Sunny, Moon } from '@element-plus/icons-vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import Settings from './components/Settings.vue'
import ModelSelector from './components/ModelSelector.vue'
import { chatApi, sessionsApi } from './api'
import { useChatStore } from './stores/chat'
import { ElMessage } from 'element-plus'

const chatStore = useChatStore()

const sessions = ref([])
const currentSessionId = ref(null)
const settingsVisible = ref(false)
const isTyping = ref(false)
const isDark = ref(localStorage.getItem('theme_dark') === 'true')
const settings = ref({
  model: localStorage.getItem('chat_model') || 'deepseek',
  temperature: parseFloat(localStorage.getItem('chat_temperature')) || 0.7,
  maxTokens: parseInt(localStorage.getItem('chat_maxTokens')) || 2000,
})

// 应用主题
function applyTheme() {
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  localStorage.setItem('theme_dark', String(isDark.value))
}

// 切换主题
function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
}

// 初始化主题
onMounted(() => {
  applyTheme()
})

const currentSession = computed(() => {
  return sessions.value.find(s => s.id === currentSessionId.value) || null
})

// 监听设置变化，自动保存到本地存储
watch(() => settings.value, (newSettings) => {
  localStorage.setItem('chat_model', newSettings.model)
  localStorage.setItem('chat_temperature', String(newSettings.temperature))
  localStorage.setItem('chat_maxTokens', String(newSettings.maxTokens))
}, { deep: true })

onMounted(async () => {
  await loadSessions()
})

async function loadSessions() {
  try {
    const response = await sessionsApi.list()
    sessions.value = response.sessions
    if (sessions.value.length > 0 && !currentSessionId.value) {
      currentSessionId.value = sessions.value[0].id
      await loadSessionMessages(sessions.value[0].id)
    }
  } catch (error) {
    console.error('加载会话列表失败:', error)
  }
}

async function loadSessionMessages(sessionId) {
  try {
    const response = await sessionsApi.get(sessionId)
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      session.messages = response.messages || []
    }
  } catch (error) {
    console.error('加载会话消息失败:', error)
  }
}

async function handleSelectSession(sessionId) {
  currentSessionId.value = sessionId
  await loadSessionMessages(sessionId)
}

async function handleCreateSession() {
  try {
    const response = await sessionsApi.create({ model: settings.value.model })
    const newSession = {
      id: response.id,
      title: response.title,
      model: response.model || settings.value.model,
      messages: [],
    }
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
  } catch (error) {
    console.error('创建会话失败:', error)
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await sessionsApi.delete(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
  } catch (error) {
    console.error('删除会话失败:', error)
  }
}

function handleModelChange(model) {
  localStorage.setItem('chat_model', model)
}

async function handleSendMessage(payload, options = {}) {
  if (!currentSessionId.value) {
    await handleCreateSession()
  }

  const content = typeof payload === 'string' ? payload : payload.content
  const attachments = typeof payload === 'object' ? (payload.attachments || []) : []
  const userMessage = { role: 'user', content, ...(attachments.length && { attachments }) }
  
  const session = sessions.value.find(s => s.id === currentSessionId.value)
  if (!session.messages) session.messages = []

  if (!options.skipUserMessage) {
    session.messages.push(userMessage)
    try {
      const response = await sessionsApi.addMessage(currentSessionId.value, userMessage)
      if (response.title) {
        session.title = response.title
      }
    } catch (error) {
      console.error('保存消息失败:', error)
    }
  }

  isTyping.value = true

  try {
    await chatApi.send({
      messages: session.messages.map(m => ({
        role: m.role,
        content: m.content,
        ...(m.attachments?.length && { attachments: m.attachments }),
      })),
      model: settings.value.model,
      stream: true,
      temperature: settings.value.temperature,
      max_tokens: settings.value.maxTokens,
    }, (chunk) => {
      if (chunk.choices?.[0]?.delta?.content) {
        const delta = chunk.choices[0].delta.content
        const last = session.messages[session.messages.length - 1]
        if (last.role === 'user') {
          session.messages.push({ role: 'assistant', content: delta })
        } else {
          last.content += delta
        }
      }
    })

    const assistantMessage = session.messages[session.messages.length - 1]
    if (assistantMessage?.role === 'assistant' && assistantMessage.content) {
      try {
        await sessionsApi.addMessage(currentSessionId.value, assistantMessage)
      } catch (error) {
        console.error('保存回复失败:', error)
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error(error.message || '发送消息失败，请重试')
    // 移除失败的用户消息
    session.messages.pop()
  } finally {
    isTyping.value = false
  }
}

async function handleRetryMessage(index) {
  if (index > 0) {
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    session.messages = session.messages.slice(0, index)
    try {
      await sessionsApi.update(currentSessionId.value, {
        ...session,
        model: session.model || settings.value.model,
      })
    } catch (error) {
      console.error('同步会话消息失败:', error)
    }
    const lastUserMessage = session.messages[session.messages.length - 1]
    if (lastUserMessage.role === 'user') {
      await handleSendMessage({
        content: lastUserMessage.content,
        attachments: lastUserMessage.attachments || [],
      }, { skipUserMessage: true })
    }
  }
}

function handleUpdateSettings(newSettings) {
  settings.value = newSettings
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

#app {
  width: 100%;
  height: 100%;
}

/* 亮色主题变量 */
:root {
  --bg-color: #f5f7fa;
  --bg-color-secondary: #ffffff;
  --text-color: #303133;
  --text-color-secondary: #606266;
  --border-color: #e4e7ed;
  --hover-bg: #ecf5ff;
}

/* 暗色主题变量 */
:root.dark {
  --bg-color: #1a1a1a;
  --bg-color-secondary: #2d2d2d;
  --text-color: #e0e0e0;
  --text-color-secondary: #a0a0a0;
  --border-color: #404040;
  --hover-bg: #3a3a3a;
}

.app-container {
  display: flex;
  width: 100%;
  height: 100%;
  background: var(--bg-color);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
