<template>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1 class="sidebar-title">金融助手</h1>
            <div class="user-info">
                <span><span id="usernameDisplay">{{ getUserDisplayName() }}</span></span>
                <button id="backBtn" @click="$emit('back')" title="返回主界面">
                    <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
                        <path d="M10 12L6 8L10 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        </div>

        <div class="chat-buttons-container">
            <button class="new-chat-btn" @click="$emit('new-chat')">新对话</button>
            <button class="new-chat-btn" @click="$emit('open-api-manager')">API管理</button>
            <button class="new-chat-btn account-btn" title="设置快期账户" @click="$emit('open-account-settings')">账户设置</button>
        </div>

        <div class="model-selector">
            <label for="financeModelSelect">选择模型</label>
            <select id="financeModelSelect">
                <option v-if="models.length === 0" value="qwen">暂无模型</option>
                <option v-for="model in models" :key="model.id" :value="model.name">
                    {{ model.name }}{{ model.isGlobal ? ' [系统]' : '' }}
                </option>
            </select>
        </div>

        <div class="chat-history" id="financeChatHistory">
            <div 
                v-for="chat in chatHistory" 
                :key="chat.id"
                class="chat-item"
                :class="{ active: chat.id === activeChatId, loading: loadingChatId === chat.id }"
                :style="{ cursor: chat.id === activeChatId ? 'default' : 'pointer' }"
                @click="chat.id !== activeChatId && selectChat(chat.id)"
            >
                <div class="title-container" @click.stop>
                    <input 
                        v-if="editingChatId === chat.id"
                        ref="editInput"
                        v-model="editingTitle"
                        class="chat-item-title-input"
                        title="编辑对话标题"
                        @keydown.enter="saveTitle(chat)"
                        @keydown.escape="cancelEdit"
                        @blur="saveTitle(chat)"
                        autofocus
                    />
                    <span 
                        v-else 
                        class="chat-item-title"
                        :class="{ 'editable': chat.id === activeChatId }"
                        @click.stop="chat.id === activeChatId ? startEdit(chat) : selectChat(chat.id)"
                    >{{ chat.title }}</span>
                </div>
                <button 
                    class="chat-item-delete" 
                    :class="{ editing: editingChatId === chat.id }"
                    @click.stop="$emit('delete-chat', chat.id)" 
                    title="删除对话"
                >
                    <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
                        <rect x="3" y="5" width="10" height="8.5" stroke="currentColor" stroke-width="1.5" fill="none" rx="1" />
                        <rect x="4" y="3" width="8" height="2" stroke="currentColor" stroke-width="1.5" fill="none" rx="0.8" />
                    </svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue';

const props = defineProps({
    user: {
        type: Object,
        default: null
    },
    chatHistory: {
        type: Array,
        default: () => []
    },
    activeChatId: {
        type: [String, Number],
        default: null
    },
    models: {
        type: Array,
        default: () => []
    },
    loadingChatId: {
        type: [String, Number],
        default: null
    },
    defaultModelName: {
        type: String,
        default: null
    }
});

const emit = defineEmits(['new-chat', 'switch-chat', 'delete-chat', 'back', 'update-chat-title', 'open-api-manager', 'open-account-settings']);

const editingChatId = ref(null);
const editingTitle = ref('');
const editInput = ref(null);
const isSaving = ref(false);

const setDefaultModel = () => {
    const select = document.getElementById('financeModelSelect');
    if (select && props.defaultModelName) {
        select.value = props.defaultModelName;
    }
};

watch(() => props.defaultModelName, () => {
    nextTick(() => {
        setDefaultModel();
    });
});

watch(() => props.models, () => {
    nextTick(() => {
        setDefaultModel();
    });
}, { deep: true });

onMounted(() => {
    nextTick(() => {
        setDefaultModel();
    });
});

const getUserDisplayName = () => {
    if (!props.user) return '访客';
    
    const user = props.user && props.user.user ? props.user.user : props.user;
    return user && user.username ? user.username : '访客';
};

const selectChat = async (chatId) => {
    if (editingChatId.value !== null) {
        const editingChat = props.chatHistory.find(c => c.id === editingChatId.value);
        if (editingChat && editingTitle.value.trim() !== '') {
            await saveTitle(editingChat);
        } else {
            cancelEdit();
        }
    }
    emit('switch-chat', chatId);
};

const startEdit = (chat) => {
    editingChatId.value = chat.id;
    editingTitle.value = chat.title;
    setTimeout(() => {
        if (editInput.value) {
            editInput.value.focus();
            editInput.value.select();
        }
    }, 0);
};

const cancelEdit = () => {
    editingChatId.value = null;
    editingTitle.value = '';
};

const saveTitle = async (chat) => {
    if (editingTitle.value.trim() === '') {
        cancelEdit();
        return;
    }
    
    if (editingTitle.value === chat.title) {
        cancelEdit();
        return;
    }
    
    if (isSaving.value) {
        return;
    }
    
    isSaving.value = true;
    
    try {
        const user = props.user && props.user.user ? props.user.user : props.user;
        const user_id = user && user.user_id ? user.user_id : localStorage.getItem('agent_user_id');
        
        const response = await fetch(`http://localhost:8888/api/chats/${chat.id}?user_id=${encodeURIComponent(user_id)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json; charset=utf-8'
            },
            body: JSON.stringify({
                title: editingTitle.value.trim()
            })
        });
        
        if (response.ok) {
            const updatedChat = await response.json();
            emit('update-chat-title', updatedChat);
            cancelEdit();
        }
    } catch (error) {
        console.error('保存标题失败:', error);
    } finally {
        isSaving.value = false;
    }
};
</script>
