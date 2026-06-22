<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>会话列表</h2>
      <el-button type="primary" :icon="Plus" circle @click="$emit('create-session')" />
    </div>
    
    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="搜索会话..."
        clearable
        :prefix-icon="Search"
        size="small"
      />
    </div>
    
    <div class="session-list">
      <template v-if="filteredSessions.length > 0">
        <div
          v-for="session in filteredSessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === currentSessionId }"
          @click="$emit('select-session', session.id)"
        >
          <div class="session-info">
            <div class="session-title" v-html="highlightText(session.title || '新会话')"></div>
            <div class="session-preview" v-if="getSessionPreview(session)">
              {{ getSessionPreview(session) }}
            </div>
            <div class="session-meta">
              <span class="model-tag">{{ session.model }}</span>
              <span class="message-count">{{ session.message_count || 0 }} 条消息</span>
            </div>
          </div>
          <el-dropdown trigger="click" @command="(command) => handleCommand(command, session.id)">
            <el-button type="info" :icon="More" size="small" circle />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
      <el-empty v-else-if="searchQuery" description="未找到匹配的会话" />
      <el-empty v-else description="暂无会话" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Plus, More, Search } from '@element-plus/icons-vue'

const props = defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  currentSessionId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['select-session', 'create-session', 'delete-session'])

const searchQuery = ref('')

// 过滤后的会话列表
const filteredSessions = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.sessions
  }
  
  const query = searchQuery.value.toLowerCase().trim()
  return props.sessions.filter(session => {
    // 搜索标题
    if ((session.title || '新会话').toLowerCase().includes(query)) {
      return true
    }
    // 搜索消息内容
    if (session.messages) {
      return session.messages.some(msg => 
        msg.content && msg.content.toLowerCase().includes(query)
      )
    }
    return false
  })
})

// 获取会话预览（第一条用户消息）
function getSessionPreview(session) {
  if (!session.messages || session.messages.length === 0) {
    return ''
  }
  const firstUserMessage = session.messages.find(m => m.role === 'user')
  if (firstUserMessage && firstUserMessage.content) {
    return firstUserMessage.content.substring(0, 50) + (firstUserMessage.content.length > 50 ? '...' : '')
  }
  return ''
}

// 高亮搜索文本
function highlightText(text) {
  if (!searchQuery.value.trim()) {
    return text
  }
  const query = searchQuery.value.trim()
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

function handleCommand(command, sessionId) {
  if (command === 'delete') {
    emit('delete-session', sessionId)
  } else if (command === 'rename') {
    // 可以添加重命名逻辑
  }
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  height: 100%;
  background: var(--bg-color-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
}

.search-box {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.session-item:hover {
  background: var(--hover-bg);
}

.session-item.active {
  background: var(--hover-bg);
  border-left: 3px solid #409eff;
}

.session-info {
  flex: 1;
  overflow: hidden;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.session-preview {
  font-size: 12px;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.model-tag {
  background: var(--hover-bg);
  padding: 2px 6px;
  border-radius: 4px;
}

.message-count {
  white-space: nowrap;
}

/* 搜索高亮样式 */
.session-title :deep(mark) {
  background-color: #fef08a;
  color: #000;
  padding: 0 2px;
  border-radius: 2px;
}

:root.dark .session-title :deep(mark) {
  background-color: #854d0e;
  color: #fef08a;
}
</style>
